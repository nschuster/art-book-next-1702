"""Durability/concurrency tests use real CLI processes and a loopback HTTP API."""
import fcntl
import json
import subprocess
import sys
import threading
import time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/retroachievements/sync.py'

@pytest.fixture
def queue_rig(tmp_path):
    class Rig:
        requests = []
        status = 200
        block = False
        entered = threading.Event()
        release = threading.Event()
        processes = []
        def start(self, *args):
            p = subprocess.Popen(self.command + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.processes.append(p)
            return p
        def run(self, *args):
            return subprocess.run(self.command + list(args), capture_output=True, text=True, timeout=10)
        def pending(self):
            return json.loads((self.state/'pending.json').read_text())
    r = Rig()
    r.state = tmp_path/'system/retroachievements'; r.state.mkdir(parents=True)
    config = r.state/'config.json'
    mapping = tmp_path/'mapping.json'
    mapping.write_text(json.dumps([{'system':'snes','rom':f'Game{i}.sfc','game_id':i} for i in (1,2,3)]))
    config.write_text(json.dumps({'username':'private-user','api_key':'private-key','mapping_file':str(mapping),'retries':0,'min_interval':0,'backoff':0,'queue_backoff':0.2}))
    config.chmod(0o600)
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            gid = int(parse_qs(urlsplit(self.path).query)['g'][0])
            r.requests.append(gid)
            if r.block:
                r.block = False; r.entered.set(); r.release.wait(8)
            self.send_response(r.status); self.end_headers()
            try:
                self.wfile.write(json.dumps({'ID':gid,'NumAchievements':10,'NumAwardedToUser':4,'NumAwardedToUserHardcore':2}).encode())
            except BrokenPipeError:
                pass  # Intentional killed-worker recovery test.
        def log_message(self, *args): pass
    server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread = threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    r.command = [sys.executable,str(SCRIPT),'--config',str(config),'--data-root',str(tmp_path),'--test-api-base',f'http://127.0.0.1:{server.server_port}/']
    yield r
    r.release.set()
    for p in r.processes:
        if p.poll() is None: p.kill()
        p.communicate(timeout=10)
    server.shutdown(); server.server_close(); thread.join()

def test_enqueue_is_durable_before_worker_lock(queue_rig):
    r=queue_rig
    with (r.state/'sync.lock').open('w') as held:
        fcntl.flock(held,fcntl.LOCK_EX)
        result=r.run('--system','snes','--rom','Game3.sfc','--force')
        assert result.returncode == 0
        assert (r.state/'pending.json').exists(), 'lock contention must enqueue, not drop the event'
        assert r.pending()['3']['force'] is True
    assert r.requests == []
    assert r.run('--drain').returncode == 0
    assert r.requests == [3] and r.pending() == {}

def test_priority_and_generation_safe_ack(queue_rig):
    r=queue_rig; r.block=True
    worker=r.start()
    assert r.entered.wait(5)
    assert r.run('--system','snes','--rom','Game1.sfc','--force').returncode == 0
    assert r.run('--system','snes','--rom','Game3.sfc','--force').returncode == 0
    r.release.set()
    out,err=worker.communicate(timeout=10)
    assert worker.returncode == 0, (out,err)
    assert r.requests == [1,1,3,2], 'in-flight forced event must survive old ack and precede startup backlog'
    assert r.pending() == {}

def test_failure_survives_restart_without_fabricating_progress(queue_rig):
    r=queue_rig
    assert r.run().returncode == 0
    before=(r.state/'extras/snes/Game1.xml').read_bytes()
    r.status=503
    assert r.run('--system','snes','--rom','Game1.sfc','--force').returncode == 1
    assert (r.state/'pending.json').exists(), 'network failure must retain pending work'
    assert r.pending()['1']['attempts'] == 1
    assert (r.state/'extras/snes/Game1.xml').read_bytes() == before
    r.status=200
    time.sleep(.25)
    assert r.run('--drain').returncode == 0
    assert r.pending() == {}

def test_watch_retries_without_another_event_and_log_is_private_bounded(queue_rig):
    r=queue_rig; r.status=503
    worker=r.start('--watch','--system','snes','--rom','Game1.sfc','--force')
    deadline=time.monotonic()+5
    while not r.requests and worker.poll() is None and time.monotonic()<deadline: time.sleep(.02)
    assert r.requests, worker.communicate(timeout=2)
    r.status=200
    worker.communicate(timeout=10)
    assert worker.returncode == 0
    assert len(r.requests)>=2 and r.pending()=={}
    log=r.state/'status.log'
    assert log.exists()
    assert not any(secret in log.read_text() for secret in ('private-user','private-key','Game1','http'))
    # Pre-existing long status history is trimmed on the next status event.
    log.write_text('old status\n'*1000)
    assert r.run().returncode == 0
    assert len(log.read_bytes()) <= 16384

def test_watch_obligation_survives_collision_with_manual_worker(queue_rig):
    r=queue_rig; r.block=True; r.status=503
    worker=r.start('--system','snes','--rom','Game1.sfc','--force')
    assert r.entered.wait(5)
    assert r.run('--watch','--system','snes','--rom','Game1.sfc','--force').returncode == 0
    r.release.set()
    deadline=time.monotonic()+5
    while len(r.requests)<2 and worker.poll() is None and time.monotonic()<deadline: time.sleep(.02)
    r.status=200
    worker.communicate(timeout=10)
    assert worker.returncode == 0, 'watch request must transfer retry responsibility to active worker'
    assert r.pending()=={}


def test_account_change_during_inflight_request_reconciles_before_publish(queue_rig):
    r=queue_rig; r.block=True
    worker=r.start('--system','snes','--rom','Game1.sfc','--force')
    assert r.entered.wait(5)
    config=r.state/'config.json'
    cfg=json.loads(config.read_text());cfg['username']='different-user';config.write_text(json.dumps(cfg))
    r.release.set()
    worker.communicate(timeout=10)
    assert worker.returncode == 0
    assert r.requests == [1,1], 'old account in-flight response must not publish as current progress'


def test_stop_waits_for_worker_and_retains_pending(queue_rig):
    r=queue_rig; r.status=503
    worker=r.start('--watch','--system','snes','--rom','Game1.sfc','--force')
    deadline=time.monotonic()+5
    while not r.requests and worker.poll() is None and time.monotonic()<deadline: time.sleep(.02)
    assert r.requests
    assert r.run('--stop').returncode == 0
    worker.communicate(timeout=5)
    assert worker.returncode == 1 and '1' in r.pending()
    r.status=200
    assert r.run('--watch','--drain').returncode == 0
    assert r.pending()=={}


def test_rejected_setup_is_recorded_without_credentials(queue_rig):
    r=queue_rig
    (r.state/'config.json').chmod(0o644)
    assert r.run().returncode == 2
    log=r.state/'status.log'
    assert log.exists(), 'hook configuration failures need a persistent diagnostic'
    assert 'rejected' in log.read_text() and 'private-key' not in log.read_text()


def test_killed_inflight_worker_retains_work(queue_rig):
    r=queue_rig; r.block=True
    worker=r.start('--system','snes','--rom','Game1.sfc','--force')
    assert r.entered.wait(5)
    worker.kill();worker.communicate(timeout=5)
    assert (r.state/'pending.json').exists(), 'claiming work must not remove it'
    assert '1' in r.pending()
    r.release.set()
    assert r.run('--drain').returncode == 0
    assert r.requests == [1,1] and r.pending()=={}

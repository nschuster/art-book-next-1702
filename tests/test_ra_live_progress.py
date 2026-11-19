"""Worker-owned snapshots, exercised with the existing real loopback fixture."""
import fcntl
import json
import time
import uuid
from test_ra_queue import queue_rig


def snapshot(r):
    path = r.state / 'progress.json'
    assert path.exists(), 'worker must publish live progress.json'
    data = json.loads(path.read_text())
    assert data['schema'] == 1
    uuid.UUID(data['run_id'])
    assert data['pid'] > 0 and data['updated_at'] > 0
    assert data['completed'] == data['updated'] + data['cached']
    assert data['completed'] <= data['total']
    assert all(x not in path.read_text() for x in ('private-key', 'private-user', 'http://'))
    return data


def configure(r, **values):
    path = r.state / 'config.json'
    cfg = json.loads(path.read_text()); cfg.update(values)
    path.write_text(json.dumps(cfg))


def wait_state(r, state):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        path = r.state / 'progress.json'
        if path.exists() and json.loads(path.read_text())['state'] == state:
            return snapshot(r)
        time.sleep(.01)
    assert False, 'missing state: ' + state


def test_removed_queued_ids_do_not_inflate_live_total(queue_rig):
    r = queue_rig
    with (r.state/'sync.lock').open('a') as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        assert r.run('--system','snes','--rom','Game1.sfc').returncode == 0
    job = r.pending()['1']
    (r.state/'pending.json').write_text(json.dumps({'999':job}))
    assert r.run('--watch').returncode == 0
    status = snapshot(r)
    assert status['state'] == 'complete'
    assert status['total'] == status['completed'] == 3
    assert status['pending'] == status['failed'] == 0


def test_names_visible_before_http_finishes_and_contender_cannot_overwrite(queue_rig):
    r = queue_rig
    root = r.state.parents[1]
    directory = root / 'roms/snes'; directory.mkdir(parents=True)
    (directory / 'gamelist.xml').write_text('<gameList><game><path>Game1.sfc</path><name>  Super\n  Mario\tWorld\u202e </name><cheevosId>1</cheevosId></game></gameList>')
    configure(r, systems=['snes'])
    systems = root / 'system/configs/emulationstation/es_systems.cfg'
    systems.parent.mkdir(parents=True)
    systems.write_text('<systemList><system><name>snes</name><fullname>Super Nintendo</fullname></system></systemList>')
    r.block = True
    worker = r.start('--system', 'snes', '--rom', 'Game1.sfc')
    assert r.entered.wait(5)
    live = snapshot(r)
    assert live['state'] == 'syncing'
    assert live['system'] == 'Super Nintendo' and live['game'] == 'Super Mario World'
    assert live['game_id'] == 1 and live['attempt'] == 1
    assert live['total'] == live['pending'] == 1 and live['completed'] == 0
    before = (r.state / 'progress.json').read_bytes()
    assert r.run('--system', 'snes', '--rom', 'Game3.sfc', '--force').returncode == 0
    assert (r.state / 'progress.json').read_bytes() == before
    r.release.set(); worker.communicate(timeout=10)
    final = snapshot(r)
    assert final['run_id'] == live['run_id'] and final['state'] == 'complete'
    assert final['total'] == final['completed'] == final['updated'] == 2
    assert final['pending'] == final['failed'] == final['cached'] == 0


def test_cached_unique_jobs_new_run_and_initial_pending(queue_rig):
    r = queue_rig
    with (r.state / 'sync.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        assert r.run('--system', 'snes', '--rom', 'Game3.sfc').returncode == 0
    assert not (r.state / 'progress.json').exists()
    assert r.run('--system', 'snes', '--rom', 'Game1.sfc').returncode == 0
    first = snapshot(r)
    assert first['total'] == first['updated'] == 2
    assert r.run('--system', 'snes', '--rom', 'Game1.sfc').returncode == 0
    cached = snapshot(r)
    assert cached['run_id'] != first['run_id']
    assert cached['state'] == 'complete' and cached['cached'] == cached['completed'] == cached['total'] == 1
    assert cached['updated'] == 0 and r.requests == [3, 1]
    assert cached['game'] == 'Game1'


def test_queue_retries_count_only_terminal_unique_failures(queue_rig):
    r = queue_rig; r.status = 503
    configure(r, queue_attempts=2, queue_backoff=.1)
    assert r.run('--watch').returncode == 1
    final = snapshot(r)
    assert final['state'] == 'failed'
    assert final['failed'] == final['pending'] == final['total'] == 3
    assert final['completed'] == 0 and len(r.requests) == 6


def test_retry_recovers_without_inflating_counts(queue_rig):
    r = queue_rig; r.status = 503
    configure(r, queue_backoff=1)
    worker = r.start('--watch', '--system', 'snes', '--rom', 'Game1.sfc')
    live = wait_state(r, 'retrying')
    assert live['failed'] == live['completed'] == 0 and live['pending'] == 1
    r.status = 200
    worker.communicate(timeout=10)
    final = snapshot(r)
    assert final['state'] == 'complete' and final['completed'] == final['updated'] == final['total'] == 1
    assert final['failed'] == 0


def test_transport_retry_backoff_can_be_stopped(queue_rig):
    r = queue_rig; r.status = 503
    configure(r, retries=3, backoff=3)
    worker = r.start('--watch', '--system', 'snes', '--rom', 'Game1.sfc')
    live = wait_state(r, 'retrying')
    assert live['failed'] == 0
    assert r.run('--stop').returncode == 0
    worker.communicate(timeout=5)
    final = snapshot(r)
    assert final['state'] == 'stopped' and final['pending'] == 1
    assert final['run_id'] == live['run_id'] and final['completed'] == 0


def test_nonwatch_pending_is_failed_not_complete(queue_rig):
    r = queue_rig; r.status = 503
    assert r.run('--system', 'snes', '--rom', 'Game1.sfc').returncode == 1
    final = snapshot(r)
    assert final['state'] == 'failed' and final['failed'] == final['pending'] == 1


def test_owner_fatal_error_is_terminal_without_raw_details(queue_rig):
    r = queue_rig
    (r.state / 'extras-manifest.json').write_text('{private-key')
    assert r.run().returncode == 2
    final = snapshot(r)
    assert final['state'] == 'failed' and final['pending'] == 3


def test_identity_restart_gets_new_run_without_counting_discarded_response(queue_rig):
    r = queue_rig; r.block = True
    worker = r.start('--system', 'snes', '--rom', 'Game1.sfc', '--force')
    assert r.entered.wait(5)
    first = snapshot(r)
    configure(r, username='new-private-user')
    r.release.set(); worker.communicate(timeout=10)
    final = snapshot(r)
    assert final['run_id'] != first['run_id']
    assert final['completed'] == final['updated'] == final['total'] == 1
    assert r.requests == [1, 1]


def test_same_id_new_generation_never_inflates_counts(queue_rig):
    r = queue_rig; r.block = True
    worker = r.start('--system', 'snes', '--rom', 'Game1.sfc')
    assert r.entered.wait(5)
    assert r.run('--system', 'snes', '--rom', 'Game1.sfc', '--force').returncode == 0
    r.release.set(); worker.communicate(timeout=10)
    final = snapshot(r)
    assert r.requests == [1, 1]
    assert final['updated'] == final['completed'] == final['total'] == 1


def test_label_bounds_secrets_and_blank_fallback(queue_rig):
    r = queue_rig
    root = r.state.parents[1]
    directory = root / 'roms/snes'; directory.mkdir(parents=True)
    (directory / 'gamelist.xml').write_text('<gameList><game><path>Game1.sfc</path><name> \t\u202e </name></game><game><path>Game2.sfc</path><name>private-key private-user ' + 'Ａ' * 300 + '</name></game></gameList>')
    configure(r, systems=['snes'])
    assert r.run('--system', 'snes', '--rom', 'Game1.sfc').returncode == 0
    assert snapshot(r)['game'] == 'Game1'
    assert r.run('--system', 'snes', '--rom', 'Game2.sfc').returncode == 0
    name = snapshot(r)['game']
    assert len(name) <= 160 and name.isprintable() and 'Ａ' not in name


def test_gamelists_are_parsed_once_not_per_job(queue_rig, monkeypatch):
    import importlib.util
    from argparse import Namespace
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / 'scripts/retroachievements/sync.py'
    spec = importlib.util.spec_from_file_location('live_sync', path)
    sync = importlib.util.module_from_spec(spec); spec.loader.exec_module(sync)
    r = queue_rig
    root = r.state.parents[1]
    directory = root / 'roms/snes'; directory.mkdir(parents=True)
    gamelist = directory / 'gamelist.xml'
    gamelist.write_text('<gameList/>'); configure(r, systems=['snes'])
    original = sync.ET.parse
    reads = []
    def parse(path, *args, **kwargs):
        if Path(path) == gamelist: reads.append(path)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(sync.ET, 'parse', parse)
    args = Namespace(config=str(r.state / 'config.json'), data_root=str(root),
                     test_api_base=r.command[-1], system=None, rom=None,
                     force=False, watch=False, drain=False, stop=False)
    assert sync.run(args) == 0
    assert len(reads) == 1 and len(r.requests) == 3


def test_unexpected_main_exception_is_sanitized_owner_terminal(queue_rig, monkeypatch, capsys):
    import importlib.util
    import sys
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / 'scripts/retroachievements/sync.py'
    spec = importlib.util.spec_from_file_location('fatal_live_sync', path)
    sync = importlib.util.module_from_spec(spec); spec.loader.exec_module(sync)
    def broken(*args, **kwargs):
        raise RuntimeError('private-key http://private-user/')
    monkeypatch.setattr(sync, 'render', broken)
    monkeypatch.setattr(sys, 'argv', queue_rig.command[1:])
    assert sync.main() == 2
    assert snapshot(queue_rig)['state'] == 'failed'
    output = capsys.readouterr()
    assert 'private-key' not in output.err and 'http://' not in output.err


def test_disabled_owner_publishes_disabled(queue_rig):
    r = queue_rig
    configure(r, backend='batocera')
    (r.state.parent / 'batocera.conf').write_text('global.retroachievements=0\n')
    assert r.run().returncode == 0
    assert snapshot(r)['state'] == 'disabled'

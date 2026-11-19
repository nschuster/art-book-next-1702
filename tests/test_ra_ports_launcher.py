"""Ports launcher lifecycle: no real account/network; real locks and subprocesses."""
import fcntl
import importlib.util
import json
import os
import time
import subprocess
import sys
from pathlib import Path

import pytest
from test_ra_queue import queue_rig

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts/retroachievements'
PORT = 'roms/ports/Refresh RetroAchievements Progress.sh'


def load_launcher():
    path = SCRIPTS / 'launcher.py'
    assert path.exists(), 'controller launcher is not implemented'
    sys.path.insert(0, str(SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location('ra_launcher', path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def install(root, *args):
    return subprocess.run([sys.executable, str(SCRIPTS/'install.py'), '--data-root', str(root), *args], capture_output=True, text=True)


def test_ports_menu_opt_in_and_upgrade_preservation(tmp_path):
    assert install(tmp_path).returncode == 0
    assert not (tmp_path/PORT).exists()
    result = install(tmp_path, '--ports-menu')
    assert result.returncode == 0, result.stderr
    launcher = tmp_path/PORT
    assert launcher.exists() and launcher.stat().st_mode & 0o111
    assert 'launcher.py' in launcher.read_text()
    assert install(tmp_path).returncode == 0
    assert launcher.exists(), 'ordinary upgrades must retain an opted-in menu'
    assert install(tmp_path, '--uninstall').returncode == 0
    assert not launcher.exists()


def test_ports_menu_refuses_unmanaged_launcher_without_partial_upgrade(tmp_path):
    assert install(tmp_path).returncode == 0
    before = (tmp_path/'system/retroachievements/install-manifest.json').read_bytes()
    path = tmp_path/PORT
    path.parent.mkdir(parents=True)
    path.write_text('user launcher\n')
    result = install(tmp_path, '--ports-menu')
    assert result.returncode != 0
    assert path.read_text() == 'user launcher\n'
    assert (tmp_path/'system/retroachievements/install-manifest.json').read_bytes() == before


def test_attaching_does_not_enqueue_or_replace_active_progress(tmp_path):
    launcher = load_launcher()
    state = tmp_path/'system/retroachievements'; state.mkdir(parents=True)
    (state/'progress.json').write_text('{"run_id":"active"}')
    (state/'launcher-process.json').write_text(json.dumps({'pid':0, 'start_ticks':None, 'owner_run_id':'active'}))
    with (state/'sync.lock').open('a') as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        assert launcher.start_or_attach(tmp_path) is None
        assert json.loads((state/'progress.json').read_text())['run_id'] == 'active'
    assert not (state/'pending.json').exists()


def test_worker_detached_no_inherited_pipes_and_stale_status_cleared(tmp_path):
    launcher = load_launcher()
    state = tmp_path/'system/retroachievements'; state.mkdir(parents=True)
    (state/'progress.json').write_text('{"state":"complete"}')
    # A synthetic worker records argv/session, without touching a real service.
    (state/'sync.py').write_text('import os,sys,json; from pathlib import Path; Path(__file__).with_name("invocation.json").write_text(json.dumps({"args":sys.argv[1:],"pid":os.getpid(),"sid":os.getsid(0)}))')
    process = launcher.start_or_attach(tmp_path)
    assert process is not None
    assert process.wait(timeout=5) == 0
    result = json.loads((state/'invocation.json').read_text())
    assert result['pid'] == result['sid'], 'worker must survive closing the Ports UI'
    assert '--force' in result['args'] and '--watch' in result['args']
    assert '--config' in result['args'] and '--data-root' in result['args']
    assert not (state/'progress.json').exists(), 'old completion must not appear for a new run'
    assert process.stdout is None and process.stderr is None


def test_install_refuses_a_worker_still_scanning_before_sync_lock(tmp_path):
    launcher = load_launcher()
    state = tmp_path/'system/retroachievements'; state.mkdir(parents=True)
    worker = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
    try:
        (state/'launcher-process.json').write_text(json.dumps({'pid': worker.pid, 'start_ticks': launcher.process_identity(worker.pid)}))
        result = install(tmp_path)
        assert result.returncode != 0, 'must not replace helper while launched worker loads/scans'
        assert not (state/'install-manifest.json').exists()
    finally:
        worker.terminate(); worker.wait(timeout=5)


def test_reopen_during_initial_scan_does_not_start_second_worker(tmp_path):
    launcher = load_launcher()
    state = tmp_path/'system/retroachievements'; state.mkdir(parents=True)
    (state/'sync.py').write_text('import time; time.sleep(30)')
    worker = launcher.start_or_attach(tmp_path)
    try:
        assert launcher.start_or_attach(tmp_path) is None
    finally:
        worker.terminate(); worker.wait(timeout=5)


def test_early_worker_failure_is_visible_instead_of_waiting_forever(tmp_path):
    launcher = load_launcher()
    state = tmp_path/'system/retroachievements'; state.mkdir(parents=True)
    (state/'sync.py').write_text('raise SystemExit(2)')
    session = launcher.SyncSession(tmp_path)
    session.start()
    session.child.wait(timeout=5)
    status = session.read_status()
    assert status['state'] == 'failed'
    assert status['reason'] == 'worker_ended_without_result'
    assert status['completed'] == 0
    assert not (state/'progress.json').exists(), 'UI must not write worker-owned progress'


def test_session_reports_initial_discovery_and_detects_abrupt_exit(tmp_path):
    launcher = load_launcher()
    state = tmp_path/'system/retroachievements'; state.mkdir(parents=True)
    (state/'sync.py').write_text('import time; time.sleep(30)')
    session = launcher.SyncSession(tmp_path)
    session.start()
    try:
        assert session.read_status()['state'] == 'scanning'
        (state/'progress.json').write_text(json.dumps({'schema':1,'state':'syncing','total':3,'completed':1,'pid':session.child.pid,'run_id':'fixture'}))
        session.child.kill(); session.child.wait(timeout=5)
        assert session.read_status()['state'] == 'failed'
        assert session.read_status()['completed'] == 1
    finally:
        if session.child.poll() is None:
            session.child.terminate(); session.child.wait(timeout=5)


def test_ui_polling_never_takes_worker_lock(tmp_path, monkeypatch):
    launcher = load_launcher()
    state = tmp_path/'system/retroachievements'; state.mkdir(parents=True)
    def forbidden(*args):
        raise AssertionError('read-only UI must not look like a competing worker')
    monkeypatch.setattr(launcher.fcntl, 'flock', forbidden)
    assert launcher.SyncSession(tmp_path).read_status()['state'] == 'failed'


def test_child_is_spawned_after_releasing_probe_lock(tmp_path, monkeypatch):
    launcher = load_launcher()
    state = tmp_path/'system/retroachievements'; state.mkdir(parents=True)
    real_popen = launcher.subprocess.Popen
    def checked(*args, **kwargs):
        with (state/'sync.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return real_popen(*args, **kwargs)
    monkeypatch.setattr(launcher.subprocess, 'Popen', checked)
    (state/'sync.py').write_text('raise SystemExit(0)')
    worker = launcher.start_or_attach(tmp_path)
    worker.wait(timeout=5)


def test_first_ports_launch_enqueues_full_library_behind_game_exit_worker(queue_rig):
    r = queue_rig; root = r.state.parents[1]
    assert install(root, '--ports-menu').returncode == 0
    r.block = True
    active = r.start('--system', 'snes', '--rom', './Game1.sfc', '--force', '--watch')
    contender = None
    try:
        assert r.entered.wait(5)
        launcher = load_launcher()
        contender = launcher.start_or_attach(root, r.command[-1])
        assert contender is not None, 'full-library intent must not attach silently to a one-game hook'
        contender.wait(timeout=5)
        queued = r.pending()
        assert set(queued) == {'1','2','3'}
        assert launcher.start_or_attach(root, r.command[-1]) is None
        assert r.pending() == queued, 'reopening must not reset generations or attempts'
        r.release.set()
        active.communicate(timeout=8)
        assert active.returncode == 0
        assert set(r.requests) == {1,2,3}
    finally:
        r.release.set()
        if contender is not None and contender.poll() is None:
            contender.terminate(); contender.wait(timeout=5)


def test_installed_ui_closes_while_real_worker_continues(queue_rig):
    r = queue_rig
    root = r.state.parents[1]
    result = install(root, '--ports-menu')
    assert result.returncode == 0, result.stderr
    r.block = True
    capture = root/'live-progress.bmp'
    cmd = [sys.executable, str(r.state/'launcher.py'), '--data-root', str(root),
           '--test-api-base', r.command[-1], '--frames', '20', '--windowed', '--screenshot', str(capture)]
    ui = subprocess.Popen(cmd, env={**os.environ, 'SDL_VIDEODRIVER':'dummy'}, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert r.entered.wait(5), 'installed UI must launch real fixture-backed worker'
        out, err = ui.communicate(timeout=5)
        assert ui.returncode == 0, (out, err)
        assert capture.read_bytes().startswith(b'BM')
        status = json.loads((r.state/'progress.json').read_text())
        assert status['state'] == 'syncing' and status['game'] == 'Game1'
        assert status['system'] and status['total'] == 3
        with (r.state/'sync.lock').open('a') as lock:
            with pytest.raises(BlockingIOError):
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        r.release.set()
        deadline = time.monotonic()+8
        while time.monotonic() < deadline:
            status = json.loads((r.state/'progress.json').read_text())
            if status['state'] == 'complete':
                break
            time.sleep(.03)
        assert status['state'] == 'complete' and status['completed'] == 3
        assert r.requests == [1,2,3]
        assert 'private-key' not in (r.state/'progress.json').read_text()
    finally:
        r.release.set()
        if ui.poll() is None:
            ui.terminate(); ui.communicate(timeout=5)
        r.run('--stop')


def test_display_failure_does_not_start_network_worker(queue_rig):
    r = queue_rig
    root = r.state.parents[1]
    assert install(root, '--ports-menu').returncode == 0
    result = subprocess.run([sys.executable, str(r.state/'launcher.py'), '--data-root', str(root), '--test-api-base', r.command[-1], '--frames', '1'], env={**os.environ, 'SDL_VIDEODRIVER':'nonexistent-test-driver'}, capture_output=True, text=True, timeout=5)
    assert result.returncode != 0
    assert r.requests == [] and not (r.state/'launcher-process.json').exists()


def test_launcher_refuses_symlinked_progress_without_starting(tmp_path):
    launcher = load_launcher()
    state = tmp_path/'system/retroachievements'; state.mkdir(parents=True)
    outside = tmp_path/'unrelated'; outside.write_text('unchanged')
    (state/'progress.json').symlink_to(outside)
    with pytest.raises(Exception):
        launcher.start_or_attach(tmp_path)
    assert outside.read_text() == 'unchanged'

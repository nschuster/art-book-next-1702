"""Managed hook upgrades keep retry/error visibility and refuse active mutations."""
import fcntl
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

INSTALL = Path(__file__).resolve().parents[1]/'scripts/retroachievements/install.py'


def test_hooks_retry_and_stop(tmp_path):
    def install(*args):
        return subprocess.run([sys.executable,str(INSTALL),'--data-root',str(tmp_path),*args],capture_output=True,text=True)
    assert install().returncode == 0
    hook=(tmp_path/'system/scripts/ra-progress-sync.sh').read_text()
    service=(tmp_path/'system/services/ra_progress_sync').read_text()
    assert '--watch' in hook and '--watch' in service
    assert '--stop' in service
    assert install().returncode == 0
    assert install('--uninstall').returncode == 0
    assert not (tmp_path/'system/scripts/ra-progress-sync.sh').exists()


@pytest.mark.parametrize('hook,args', [
    ('system/scripts/ra-progress-sync.sh',
     ['gameStop', 'snes', 'libretro', 'snes9x', './Game with spaces.sfc']),
    ('system/services/ra_progress_sync', ['start']),
])
def test_installed_background_hook_releases_capture_pipes(tmp_path, hook, args):
    # Install the real shell scripts, substituting only the worker. No RA calls.
    root = tmp_path / 'data root'
    result = subprocess.run(
        [sys.executable, str(INSTALL), '--data-root', str(root)],
        capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    state = root / 'system/retroachievements'
    ready = state / 'worker-ready.json'
    (state / 'sync.py').write_text(
        'import json, os, sys, time\n'
        'from pathlib import Path\n'
        'print("worker stdout", flush=True)\n'
        'print("worker stderr", file=sys.stderr, flush=True)\n'
        'ready = Path(__file__).with_name("worker-ready.json")\n'
        'temporary = ready.with_suffix(".tmp")\n'
        'temporary.write_text(\n'
        '    json.dumps({"pid": os.getpid(), "args": sys.argv[1:],\n'
        '                "stdin": sys.stdin.read()}))\n'
        'temporary.replace(ready)\n'
        'time.sleep(30)\n')
    process = subprocess.Popen(
        ['sh', str(root / hook), *args], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        start_new_session=True)
    try:
        try:
            stdout, stderr = process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            pytest.fail('background worker retained caller capture pipes')
        assert process.returncode == 0
        assert stdout == stderr == ''
        deadline = time.monotonic() + 2
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(.01)
        assert ready.exists(), 'hook must actually launch the worker'
        worker = json.loads(ready.read_text())
        os.kill(worker['pid'], 0)  # Capture returned while worker is still alive.
        expected = ['--config', str(state / 'config.json'), '--data-root',
                    str(root), '--watch']
        if args[0] == 'gameStop':
            expected += ['--system', 'snes', '--rom', args[4], '--force']
        assert worker['args'] == expected
        assert worker['stdin'] == ''
    finally:
        # Own isolated group only: reap the caller and stop the fake worker on
        # both RED and GREEN, without waiting for its long-lived sleep.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.communicate(timeout=5)


def test_install_and_uninstall_refuse_active_worker(tmp_path):
    command=[sys.executable,str(INSTALL),'--data-root',str(tmp_path)]
    assert subprocess.run(command,capture_output=True).returncode == 0
    state=tmp_path/'system/retroachievements'
    before=(state/'sync.py').read_bytes()
    with (state/'sync.lock').open('a') as held:
        fcntl.flock(held,fcntl.LOCK_EX)
        for args in ([],['--uninstall']):
            result=subprocess.run(command+args,capture_output=True,text=True)
            assert result.returncode == 2, 'active worker must be stopped before replacing/removing managed code'
            assert (state/'sync.py').read_bytes() == before

"""Managed hook upgrades keep retry/error visibility and refuse active mutations."""
import fcntl
import subprocess
import sys
from pathlib import Path

INSTALL = Path(__file__).resolve().parents[1]/'scripts/retroachievements/install.py'


def test_hooks_retry_and_expose_failures_and_stop(tmp_path):
    def install(*args):
        return subprocess.run([sys.executable,str(INSTALL),'--data-root',str(tmp_path),*args],capture_output=True,text=True)
    assert install().returncode == 0
    hook=(tmp_path/'system/scripts/ra-progress-sync.sh').read_text()
    service=(tmp_path/'system/services/ra-progress-sync').read_text()
    assert '--watch' in hook and '--watch' in service
    assert '>/dev/null 2>&1' not in hook+service
    assert '--stop' in service
    assert install().returncode == 0
    assert install('--uninstall').returncode == 0
    assert not (tmp_path/'system/scripts/ra-progress-sync.sh').exists()


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

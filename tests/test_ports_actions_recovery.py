"""Actual process interruption of the outer Ports publication transaction."""
from pathlib import Path
import os
import subprocess
import sys

import pytest
from test_ports_actions import module, SOURCE


@pytest.mark.parametrize('upgrade', [False, True])
@pytest.mark.parametrize('boundary', [1, 4, 7, 8])
def test_ports_install_recovers_sigkill(tmp_path, upgrade, boundary):
    m = module()
    if upgrade:
        m.install_features(tmp_path)
    program = '''import sys,os,signal
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import ports_actions as m
root=Path(sys.argv[2]); boundary=int(sys.argv[3])
join=m.shlex.join
m.shlex.join=lambda args: join(args)+' # simulated next release'
write=m.atomic_write
count=0
def interrupted(path,data):
 global count
 write(path,data)
 if (path.parent==root/'roms/ports' and path.suffix=='.sh') or path==root/'system/art-book-next-ports/manifest.json':
  count+=1
  if count==boundary: os.kill(os.getpid(),signal.SIGKILL)
m.atomic_write=interrupted
m.install_features(root)
'''
    killed = subprocess.run([sys.executable, '-c', program, str(SOURCE), str(tmp_path), str(boundary)], capture_output=True, text=True, timeout=20)
    assert killed.returncode == -9, killed.stdout + killed.stderr
    if boundary == 1:
        killed_again = subprocess.run([sys.executable, '-c', program.replace('next release', 'third release'), str(SOURCE), str(tmp_path), str(boundary)], capture_output=True, text=True, timeout=20)
        assert killed_again.returncode == -9, killed_again.stderr
    m.install_features(tmp_path)
    assert not (tmp_path / 'system/art-book-next-ports/pending-install.json').exists()
    assert len(list((tmp_path / 'roms/ports').glob('Art Book Next - *.sh'))) == 7
    for script in (tmp_path / 'roms/ports').glob('Art Book Next - *.sh'):
        assert 'simulated next release' not in script.read_text()


def test_interrupted_ports_install_preserves_modified_output(tmp_path, monkeypatch):
    m = module()
    original = m.atomic_write
    def interrupt(path, data):
        original(path, data)
        if path.name == 'Art Book Next - Install Features.sh':
            raise KeyboardInterrupt()
    monkeypatch.setattr(m, 'atomic_write', interrupt)
    with pytest.raises(KeyboardInterrupt):
        m.install_features(tmp_path)
    script = tmp_path / 'roms/ports/Art Book Next - Install Features.sh'
    script.write_text('my locally edited script')
    monkeypatch.setattr(m, 'atomic_write', original)
    with pytest.raises(Exception):
        m.install_features(tmp_path)
    assert script.read_text() == 'my locally edited script'

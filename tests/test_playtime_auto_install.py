"""Independent installer ownership, transactions and actual detached shell hook."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

import pytest

SOURCE = Path(__file__).resolve().parents[1] / 'scripts/system-playtime'


def installer():
    spec = importlib.util.spec_from_file_location('playtime_install', SOURCE / 'install.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def snapshot(root):
    return {str(p.relative_to(root)): (p.read_bytes(), p.stat().st_mode) for p in root.rglob('*') if p.is_file()}


def test_install_repeat_uninstall_retains_totals_and_ra(tmp_path):
    m = installer()
    keep = tmp_path / 'system/configs/art-book-next-system-playtime/snes.xml'
    keep.parent.mkdir(parents=True)
    keep.write_text('custom totals')
    ra = tmp_path / 'system/retroachievements/install-manifest.json'
    ra.parent.mkdir(parents=True)
    ra.write_text('private')
    m.install(tmp_path)
    hook = tmp_path / 'system/scripts/art-book-playtime.sh'
    assert hook.stat().st_mode & 0o111
    before = snapshot(tmp_path)
    m.install(tmp_path)
    assert snapshot(tmp_path) == before
    m.install(tmp_path, uninstall=True)
    assert not hook.exists()
    assert keep.read_text() == 'custom totals'
    assert ra.read_text() == 'private'


@pytest.mark.parametrize('uninstall', [False, True])
def test_modified_file_refuses_whole_transaction(tmp_path, uninstall):
    m = installer()
    m.install(tmp_path)
    (tmp_path / 'system/art-book-next-playtime/refresh.py').write_text('custom')
    before = snapshot(tmp_path)
    with pytest.raises((ValueError, OSError)):
        m.install(tmp_path, uninstall=uninstall)
    assert snapshot(tmp_path) == before


def test_symlink_parent_refused(tmp_path):
    m = installer()
    outside = tmp_path / 'outside'
    outside.mkdir()
    (tmp_path / 'system').symlink_to(outside, target_is_directory=True)
    with pytest.raises((ValueError, OSError)):
        m.install(tmp_path)
    assert not list(outside.iterdir())


def test_write_failure_rolls_back(tmp_path, monkeypatch):
    m = installer()
    m.install(tmp_path)
    before = snapshot(tmp_path)
    real = m.atomic_write
    calls = 0
    def fail_once(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError('disk write failure')
        return real(*args, **kwargs)
    monkeypatch.setattr(m, 'atomic_write', fail_once)
    with pytest.raises(OSError):
        m.install(tmp_path)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('operation', ['fresh', 'update', 'uninstall'])
@pytest.mark.parametrize('boundary', range(1, 7))
def test_abrupt_interruption_recovers(tmp_path, monkeypatch, operation, boundary):
    import shutil
    m = installer()
    source = tmp_path / 'source'
    shutil.copytree(SOURCE, source)
    shutil.copyfile(SOURCE.parent / 'playtime_discovery.py', source / 'playtime_discovery.py')
    monkeypatch.setattr(m, '__file__', str(source / 'install.py'))
    root = tmp_path / 'data'
    if operation != 'fresh':
        m.install(root)
    (source / 'auto_refresh.py').write_text('# new version\n')
    real_write, real_unlink = m.atomic_write, Path.unlink
    calls = 0
    def interrupted(path):
        nonlocal calls
        if str(path.relative_to(root)) in (*m.FILES, m.STATE + '/install-manifest.json'):
            calls += 1
            if calls == boundary:
                raise KeyboardInterrupt()
    def write(path, *args, **kwargs):
        real_write(path, *args, **kwargs)
        interrupted(path)
    def unlink(path, *args, **kwargs):
        real_unlink(path, *args, **kwargs)
        interrupted(path)
    with monkeypatch.context() as patch:
        patch.setattr(m, 'atomic_write', write)
        patch.setattr(Path, 'unlink', unlink)
        with pytest.raises(KeyboardInterrupt):
            m.install(root, uninstall=operation == 'uninstall')
    m.install(root, uninstall=operation == 'uninstall')
    if operation == 'uninstall':
        assert not (root / m.HOOK).exists()
    else:
        assert (root / m.FILES[0]).read_text() == '# new version\n'
    assert not (root / m.STATE / 'install-pending.json').exists()


@pytest.mark.parametrize('operation', ['fresh', 'update', 'uninstall'])
@pytest.mark.parametrize('boundary', range(1, 7))
def test_sigkill_restart_in_new_process(tmp_path, operation, boundary):
    import shutil
    import signal
    source = tmp_path / 'source'
    shutil.copytree(SOURCE, source)
    shutil.copyfile(SOURCE.parent / 'playtime_discovery.py', source / 'playtime_discovery.py')
    root = tmp_path / 'data'
    command = [sys.executable, str(source / 'install.py'), '--data-root', str(root)]
    if operation != 'fresh':
        subprocess.run(command, check=True, capture_output=True)
    (source / 'auto_refresh.py').write_text('# changed release\n')
    script = f'''
import importlib.util, os, signal
from pathlib import Path
spec = importlib.util.spec_from_file_location('installer', {str(source / 'install.py')!r})
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
root = Path({str(root)!r})
write, unlink = m.atomic_write, Path.unlink
calls = 0
def stop(path):
    global calls
    if str(path.relative_to(root)) in (*m.FILES, m.STATE + '/install-manifest.json'):
        calls += 1
        if calls == {boundary}:
            os.kill(os.getpid(), signal.SIGKILL)
def wrapped_write(path, *args, **kwargs):
    write(path, *args, **kwargs)
    stop(path)
def wrapped_unlink(path, *args, **kwargs):
    unlink(path, *args, **kwargs)
    stop(path)
m.atomic_write = wrapped_write
Path.unlink = wrapped_unlink
m.install(root, uninstall={operation == 'uninstall'!r})
'''
    result = subprocess.run([sys.executable, '-c', script], capture_output=True)
    assert result.returncode == -signal.SIGKILL, result.stderr
    if operation == 'uninstall':
        command.append('--uninstall')
    result = subprocess.run(command, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (root / 'system/art-book-next-playtime/install-pending.json').exists()
    if operation != 'uninstall':
        assert (root / 'system/art-book-next-playtime/auto_refresh.py').read_text() == '# changed release\n'


def test_interrupted_recovery_preserves_modified_content(tmp_path, monkeypatch):
    m = installer()
    real = m.atomic_write
    def interrupt(path, *args, **kwargs):
        real(path, *args, **kwargs)
        if path == tmp_path / m.FILES[0]:
            raise KeyboardInterrupt()
    with monkeypatch.context() as patch:
        patch.setattr(m, 'atomic_write', interrupt)
        with pytest.raises(KeyboardInterrupt):
            m.install(tmp_path)
    (tmp_path / m.FILES[0]).write_text('genuine user modification')
    before = snapshot(tmp_path)
    with pytest.raises(ValueError):
        m.install(tmp_path)
    assert snapshot(tmp_path) == before
    assert (tmp_path / m.STATE / 'install-pending.json').exists()


def test_real_hook_does_not_hold_parent_pipes_and_uses_native_args(tmp_path):
    m = installer()
    root = tmp_path / "user data's"
    m.install(root)
    worker = root / 'system/art-book-next-playtime/auto_refresh.py'
    marker = tmp_path / 'args.json'
    worker.write_text('import sys,time,json\nfrom pathlib import Path\nPath(' + repr(str(marker)) + ').write_text(json.dumps(sys.argv[1:]))\ntime.sleep(3)\n')
    hook = root / 'system/scripts/art-book-playtime.sh'
    start = time.time()
    result = subprocess.run(['sh', str(hook), 'gameStop', 'snes', 'libretro', 'core', '/rom/Game name.sfc'], capture_output=True, timeout=1)
    assert result.returncode == 0
    assert time.time() - start < 1
    deadline = time.monotonic() + 1
    while not marker.exists() and time.monotonic() < deadline:
        time.sleep(.01)
    args = json.loads(marker.read_text())
    assert args[:6] == ['--data-root', str(root), '--system', 'snes', '--rom', '/rom/Game name.sfc']
    assert args[6] == '--since'
    assert start <= float(args[7]) <= time.time()

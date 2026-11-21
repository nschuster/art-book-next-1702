"""Saved metadata, never wall-clock session estimates."""
import importlib.util
import os
from pathlib import Path
import sys
import threading
import time
import xml.etree.ElementTree as ET

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts/system-playtime'
sys.path.insert(0, str(SCRIPTS))


def worker():
    path = SCRIPTS / 'auto_refresh.py'
    assert path.exists(), 'automatic recovery-aware worker is missing'
    spec = importlib.util.spec_from_file_location('auto_playtime_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def game(path, seconds):
    return f'<game><path>{path}</path><gametime>{seconds}</gametime></game>'


@pytest.fixture
def library(tmp_path):
    rom = tmp_path / 'roms/nes'
    rom.mkdir(parents=True)
    base = tmp_path / 'system/configs/emulationstation/gamelists/nes/gamelist.xml'
    base.parent.mkdir(parents=True)
    base.write_text('<gameList>' + game('./sub/a.zip', 3600) + '</gameList>')
    os.utime(base, (1, 1))
    recovery = tmp_path / 'system/configs/emulationstation/recovery/nes'
    recovery.mkdir(parents=True)
    details = {'nes': {'gamelist': base, 'rom_root': rom}}
    return tmp_path, rom, base, recovery, details


def save(base, recovery, name='a.xml', path='./sub/a.zip', seconds=7200, parent=None):
    file = recovery / name
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(f'<gameList parentHash="{base.stat().st_size if parent is None else parent}">' + game(path, seconds) + '</gameList>')
    return file


def text(root, name='nes'):
    return ET.parse(root / f'system/configs/art-book-next-system-playtime/{name}.xml').findtext('.//text/text')


def run(w, lib, **kwargs):
    root, rom, base, recovery, details = lib
    return w.run(root, details=details, **kwargs)


def test_saved_overlay_replaces_and_new_game_adds_with_fallback_root(library):
    w = worker()
    root, rom, base, recovery, _ = library
    save(base, recovery, path=str(rom / 'sub/../sub/a.zip'))
    save(base, recovery, 'nested/b.xml', './nested/b.zip', 1800)
    assert run(w, library, refresh_all=True) == 1
    assert text(root) == '2h 30m'
    assert run(w, library, refresh_all=True) == 1
    assert text(root) == '2h 30m'


def test_stale_hash_ignored(library):
    w = worker()
    save(library[2], library[3], parent=999999)
    run(w, library, refresh_all=True)
    assert text(library[0]) == '1h 0m'


@pytest.mark.parametrize('bad', ['<gameList', '<gameList parentHash="bad"/>', '<gameList parentHash="{size}">' + game('./sub/a.zip', '-1') + '</gameList>'])
def test_malformed_preserves_output(library, bad):
    w = worker()
    run(w, library, refresh_all=True)
    (library[3] / 'bad.xml').write_text(bad.replace('{size}', str(library[2].stat().st_size)))
    with pytest.raises((ValueError, ET.ParseError)):
        run(w, library, refresh_all=True)
    assert text(library[0]) == '1h 0m'


def test_missing_or_wrong_rom_or_stale_recovery_times_out(library):
    w = worker()
    file = save(library[2], library[3], path='./other.zip')
    with pytest.raises(TimeoutError):
        run(w, library, system='nes', rom=library[1] / 'sub/a.zip', since=time.time()-2, timeout=.03, poll_interval=.005)
    file = save(library[2], library[3])
    os.utime(file, (1, 1))
    with pytest.raises(TimeoutError):
        run(w, library, system='nes', rom=library[1] / 'sub/a.zip', since=time.time()-2, timeout=.03, poll_interval=.005)
    assert not (library[0] / 'system/configs/art-book-next-system-playtime/nes.xml').exists()


def test_waits_for_actual_fresh_recovery(library):
    w = worker()
    def later():
        time.sleep(.04)
        save(library[2], library[3])
    thread = threading.Thread(target=later)
    thread.start()
    try:
        run(w, library, system='nes', rom=library[1] / 'sub/a.zip', since=time.time()-2, timeout=.5, poll_interval=.005)
    finally:
        thread.join()
    assert text(library[0]) == '2h 0m'


def test_fresh_main_gamelist_and_only_affected_system(library):
    w = worker()
    library[4]['other'] = library[4]['nes']
    os.utime(library[2], None)
    run(w, library, system='nes', rom=library[1] / 'sub/a.zip', since=time.time()-2, timeout=.1, poll_interval=.005)
    assert text(library[0]) == '1h 0m'
    assert not (library[0] / 'system/configs/art-book-next-system-playtime/other.xml').exists()


def test_duplicate_normalized_identity_refused(library):
    w = worker()
    save(library[2], library[3])
    save(library[2], library[3], 'duplicate.xml', './sub/../sub/a.zip')
    with pytest.raises(ValueError):
        run(w, library, refresh_all=True)


def test_lock_contention_retried(library):
    import fcntl
    w = worker()
    out = library[0] / 'system/configs/art-book-next-system-playtime'
    out.mkdir()
    with (out / '.refresh.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        thread = threading.Thread(target=lambda: (time.sleep(.05), fcntl.flock(lock, fcntl.LOCK_UN)))
        thread.start()
        try:
            run(w, library, refresh_all=True, timeout=.5, poll_interval=.005)
        finally:
            thread.join()
    assert text(library[0]) == '1h 0m'


def test_unmanaged_and_symlink_outputs_refused(library):
    w = worker()
    out = library[0] / 'system/configs/art-book-next-system-playtime'
    out.mkdir()
    (out / 'nes.xml').write_text('mine')
    with pytest.raises(ValueError):
        run(w, library, refresh_all=True)
    assert (out / 'nes.xml').read_text() == 'mine'
    (out / 'nes.xml').unlink()
    target = library[0] / 'user.xml'
    target.write_text('user')
    (out / 'nes.xml').symlink_to(target)
    with pytest.raises(ValueError):
        run(w, library, refresh_all=True)
    assert target.read_text() == 'user'


def test_same_second_preexisting_save_is_ambiguous(library):
    w = worker()
    since = int(time.time())
    file = save(library[2], library[3])
    os.utime(file, ns=(since * 10**9 + 123, since * 10**9 + 123))
    with pytest.raises(TimeoutError):
        run(w, library, system='nes', rom=library[1] / 'sub/a.zip', since=since, timeout=.03, poll_interval=.005)


def test_same_second_observed_save_change_is_accepted(library):
    w = worker()
    since = int(time.time())
    def later():
        time.sleep(.04)
        file = save(library[2], library[3])
        os.utime(file, ns=(since * 10**9 + 123, since * 10**9 + 123))
    thread = threading.Thread(target=later)
    thread.start()
    try:
        run(w, library, system='nes', rom=library[1] / 'sub/a.zip', since=since, timeout=.5, poll_interval=.005)
    finally:
        thread.join()
    assert text(library[0]) == '2h 0m'


def test_outside_rom_root_refused(library):
    w = worker()
    save(library[2], library[3], path='../elsewhere/a.zip')
    with pytest.raises(ValueError):
        run(w, library, refresh_all=True)


def test_observed_stale_file_is_not_fresh(library):
    w = worker()
    def later():
        time.sleep(.02)
        file = save(library[2], library[3])
        os.utime(file, (1, 1))
    thread = threading.Thread(target=later)
    thread.start()
    try:
        with pytest.raises(TimeoutError):
            run(w, library, system='nes', rom=library[1] / 'sub/a.zip', since=time.time()-2, timeout=.1, poll_interval=.005)
    finally:
        thread.join()


def test_cli_discovery_and_installed_layout(library, tmp_path):
    import shutil
    import subprocess
    root, rom, base, recovery, details = library
    config = root / 'system/configs/emulationstation/es_systems.cfg'
    config.write_text(f'<systemList><system><name>nes</name><path>{rom}</path></system></systemList>')
    save(base, recovery)
    bundle = tmp_path / 'installed'
    bundle.mkdir()
    for name in ('auto_refresh.py', 'refresh.py'):
        shutil.copy2(SCRIPTS / name, bundle / name)
    shutil.copy2(SCRIPTS.parent / 'playtime_discovery.py', bundle / 'playtime_discovery.py')
    for script in (SCRIPTS / 'auto_refresh.py', bundle / 'auto_refresh.py'):
        result = subprocess.run([sys.executable, str(script), '--data-root', str(root), '--refresh-all'], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        assert text(root) == '2h 0m'

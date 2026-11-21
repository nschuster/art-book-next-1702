"""Exercise the actual installed exit hook with native-shaped saved metadata."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def test_subsecond_hook_timestamp_accepts_save_before_worker_starts(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location('auto_delivery_timing', ROOT / 'scripts/system-playtime/auto_refresh.py')
    assert spec and spec.loader
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    rom_root = tmp_path / 'roms/nes'
    rom_root.mkdir(parents=True)
    base = rom_root / 'gamelist.xml'
    base.write_text('<gameList><game><path>./a.nes</path><gametime>0</gametime></game></gameList>')
    os.utime(base, (1, 1))
    recovery = tmp_path / 'system/configs/emulationstation/recovery/nes/a.xml'
    recovery.parent.mkdir(parents=True)
    recovery.write_text(f'<gameList parentHash="{base.stat().st_size}"><game>'
                        '<path>./a.nes</path><gametime>3600</gametime></game></gameList>')
    os.utime(recovery, ns=(100500000000, 100500000000))
    assert worker.run(tmp_path, system='nes', rom=rom_root / 'a.nes', since=100.25,
                      timeout=0, details={'nes': {'gamelist': base, 'rom_root': rom_root}}) == 1


def test_installed_hook_returns_before_save_and_publishes_recovery_total(tmp_path):
    data = tmp_path / 'userdata'
    roms = data / 'roms/nes'
    (roms / 'nested').mkdir(parents=True)
    rom = roms / 'nested/game.nes'
    rom.write_bytes(b'fixture')
    base = roms / 'gamelist.xml'
    base.write_text('<gameList><game><path>./nested/game.nes</path>'
                    '<gametime>36000</gametime></game><game><path>./other.nes</path>'
                    '<gametime>7200</gametime></game></gameList>')
    original = base.read_bytes()
    config = data / 'system/configs/emulationstation'
    config.mkdir(parents=True)
    (config / 'es_systems.cfg').write_text('<systemList><system><name>nes</name>'
                                         '<path>/userdata/roms/nes</path></system></systemList>')
    installer = ROOT / 'scripts/system-playtime/install.py'
    subprocess.run([sys.executable, str(installer), '--data-root', str(data)],
                   check=True, capture_output=True, timeout=10)
    worker = data / 'system/art-book-next-playtime/auto_refresh.py'
    subprocess.run([sys.executable, str(worker), '--data-root', str(data), '--refresh-all'],
                   check=True, capture_output=True, timeout=10)
    output = data / 'system/configs/art-book-next-system-playtime/nes.xml'
    def value():
        return ET.parse(output).findtext('.//text/text')
    assert value() == '12h 0m'
    hook = data / 'system/scripts/art-book-playtime.sh'
    child = subprocess.Popen([str(hook), 'gameStop', 'nes', 'libretro', 'fceumm', str(rom)],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        # A synchronous hook would deadlock: ES saves only AFTER the launcher returns.
        stdout, stderr = child.communicate(timeout=2)
        assert child.returncode == 0, stderr
        assert not stdout and not stderr
        assert value() == '12h 0m'
        recovery = config / 'recovery/nes/nested/game.xml'
        recovery.parent.mkdir(parents=True)
        recovery.write_text(f'<gameList parentHash="{len(original)}"><game>'
                            '<path>./nested/game.nes</path><gametime>37800</gametime>'
                            '<lastplayed>20261121T160000</lastplayed></game></gameList>')
        deadline = time.monotonic() + 10
        while value() != '12h 30m' and time.monotonic() < deadline:
            time.sleep(.05)
        assert value() == '12h 30m'
        assert base.read_bytes() == original
        assert not (data / 'system/retroachievements').exists()
    finally:
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

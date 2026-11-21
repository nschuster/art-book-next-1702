"""Exercise Ports hours refresh without any RA credentials or library network."""
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def fixture(tmp_path):
    scripts = tmp_path / 'themes/art-book-next-1702-master/scripts'
    shutil.copytree(ROOT / 'scripts', scripts, ignore=shutil.ignore_patterns('__pycache__'))
    rom = tmp_path / 'roms/snes'
    rom.mkdir(parents=True)
    (rom / 'gamelist.xml').write_text(f'<gameList><game><gametime>{51*3600+4*60+59}</gametime></game></gameList>')
    return scripts


def test_ports_refresh_hours_without_ra_login(tmp_path):
    scripts = fixture(tmp_path)
    run = subprocess.run([sys.executable, str(scripts / 'retroachievements/ports_setup.py'), '--data-root', str(tmp_path), '--playtime'], text=True, capture_output=True)
    assert run.returncode == 0, run.stdout + run.stderr
    output = tmp_path / 'system/configs/art-book-next-system-playtime/snes.xml'
    assert ET.parse(output).findtext('.//text/text') == '51h 4m'
    assert not (tmp_path / 'system/retroachievements/config.json').exists()
    before = output.read_bytes()
    again = subprocess.run([sys.executable, str(scripts / 'retroachievements/ports_setup.py'), '--data-root', str(tmp_path), '--playtime'], capture_output=True)
    assert again.returncode == 0
    assert output.read_bytes() == before


def test_ports_refresh_preserves_modified_output(tmp_path):
    scripts = fixture(tmp_path)
    directory = tmp_path / 'system/configs/art-book-next-system-playtime'
    directory.mkdir(parents=True)
    (directory / 'snes.xml').write_text('USER CONTENT')
    run = subprocess.run([sys.executable, str(scripts / 'retroachievements/ports_setup.py'), '--data-root', str(tmp_path), '--playtime'], text=True, capture_output=True)
    assert run.returncode == 15, run.stdout + run.stderr
    assert (directory / 'snes.xml').read_text() == 'USER CONTENT'

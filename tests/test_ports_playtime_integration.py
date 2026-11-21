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
    (rom / 'gamelist.xml').write_text(f'<gameList><game><path>./Game.sfc</path><gametime>{51*3600+4*60+59}</gametime></game></gameList>')
    return scripts


def test_ports_refresh_hours_without_ra_login(tmp_path):
    scripts = fixture(tmp_path)
    run = subprocess.run([sys.executable, str(scripts / 'retroachievements/ports_setup.py'), '--data-root', str(tmp_path), '--playtime'], text=True, capture_output=True)
    assert run.returncode == 0, run.stdout + run.stderr
    output = tmp_path / 'system/configs/art-book-next-system-playtime/snes.xml'
    assert ET.parse(output).findtext('.//text/text') == '51h 4m'
    assert not (tmp_path / 'system/retroachievements/config.json').exists()
    assert (tmp_path / 'system/scripts/art-book-playtime.sh').is_file()
    assert (tmp_path / 'system/art-book-next-playtime/auto_refresh.py').is_file()
    before = output.read_bytes()
    again = subprocess.run([sys.executable, str(scripts / 'retroachievements/ports_setup.py'), '--data-root', str(tmp_path), '--playtime'], capture_output=True)
    assert again.returncode == 0
    assert output.read_bytes() == before


def test_bootstrap_playtime_is_independent_without_theme_or_ra(tmp_path):
    roms = tmp_path / 'roms/snes'
    roms.mkdir(parents=True)
    (roms / 'gamelist.xml').write_text('<gameList><game><path>./Game.sfc</path><gametime>3600</gametime></game></gameList>')
    boot = ROOT / 'scripts/retroachievements/Install Art Book Next Features.sh'
    result = subprocess.run(['sh', str(boot), '--data-root', str(tmp_path), '--playtime'], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / 'system/scripts/art-book-playtime.sh').is_file()
    assert not (tmp_path / 'system/retroachievements').exists()


def test_playtime_success_explains_background_and_theme_reload():
    import importlib.util
    sys.path.insert(0, str(ROOT / 'scripts/retroachievements'))
    spec = importlib.util.spec_from_file_location('playtime_ports', ROOT / 'scripts/retroachievements/ports_setup.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    screen = module.SetupScreen(Path('/nonexistent'))
    screen.playtime_result = 0
    text = '\n'.join(row[2] for row in screen.layout())
    assert 'Saved totals refreshed: hours / minutes' in text
    assert 'Background' in text
    assert 'Reload the theme' in text
    screen.playtime_result = 16
    text = '\n'.join(row[2] for row in screen.layout())
    assert 'Background updates enabled' in text
    assert 'initial refresh failed' in text


def test_ports_refresh_preserves_modified_output(tmp_path):
    scripts = fixture(tmp_path)
    directory = tmp_path / 'system/configs/art-book-next-system-playtime'
    directory.mkdir(parents=True)
    (directory / 'snes.xml').write_text('USER CONTENT')
    run = subprocess.run([sys.executable, str(scripts / 'retroachievements/ports_setup.py'), '--data-root', str(tmp_path), '--playtime'], text=True, capture_output=True)
    assert run.returncode == 16, run.stdout + run.stderr
    assert 'Background updates enabled; initial refresh failed' in run.stdout
    assert (directory / 'snes.xml').read_text() == 'USER CONTENT'
    again = subprocess.run([sys.executable, str(scripts / 'retroachievements/ports_setup.py'), '--data-root', str(tmp_path), '--playtime'], text=True, capture_output=True)
    assert again.returncode == 16
    assert 'Background updates enabled; initial refresh failed' in again.stdout
    assert (directory / 'snes.xml').read_text() == 'USER CONTENT'

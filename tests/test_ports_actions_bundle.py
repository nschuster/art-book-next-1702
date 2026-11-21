"""Exercise the shipped standalone installer and generated individual Ports entries."""
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def test_installed_install_action_uses_updated_local_theme(tmp_path):
    import shutil
    root = tmp_path / "source update's root"
    theme = root / 'themes/art-book-next-1702'
    shutil.copytree(ROOT / 'scripts', theme / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
    bootstrap = ROOT / 'scripts/retroachievements/Install Art Book Next Features.sh'
    first = subprocess.run(['sh', str(bootstrap), '--data-root', str(root), '--apply'], capture_output=True, text=True, timeout=30)
    assert first.returncode == 0, first.stderr
    source = theme / 'scripts/retroachievements/ports_actions.py'
    source.write_text(source.read_text().replace('Independent, controller-friendly', 'Locally updated, controller-friendly'))
    action = root / 'roms/ports/Art Book Next - Install Features.sh'
    again = subprocess.run(['sh', str(action), '--apply'], capture_output=True, text=True, timeout=30)
    assert again.returncode == 0, again.stderr
    assert (root / 'system/retroachievements/ports_actions.py').read_bytes() == source.read_bytes()
BOOT = ROOT / 'scripts/retroachievements/Install Art Book Next Features.sh'


def test_standalone_bundle_installs_separate_actions_and_manual_refresh(tmp_path):
    root = tmp_path / 'data with spaces'
    ports = root / 'roms/ports'
    ports.mkdir(parents=True)
    (ports / 'gamelist.xml').write_text('<gameList><!--keep me--><game><path>./Other.sh</path><name>My own port</name><favorite>true</favorite></game></gameList>')
    roms = root / 'roms/nes'
    roms.mkdir()
    base = roms / 'gamelist.xml'
    base.write_text('<gameList><game><path>./test.nes</path><gametime>5400</gametime></game></gameList>')
    settings = root / 'system/configs/emulationstation'
    settings.mkdir(parents=True)
    (settings / 'es_systems.cfg').write_text('<systemList><system><name>nes</name><path>/userdata/roms/nes</path></system></systemList>')
    result = subprocess.run(['sh', str(BOOT), '--action', 'install', '--apply', '--data-root', str(root)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    entries = sorted(ports.glob('Art Book Next - *.sh'))
    assert len(entries) == 7
    metadata = ET.parse(ports / 'gamelist.xml').getroot()
    assert len(metadata.findall('game')) == 8
    assert metadata.find('game/favorite').text == 'true'
    assert '<!--keep me-->' in (ports / 'gamelist.xml').read_text()
    assert (root / 'system/retroachievements/auto-disabled').is_file()
    disabled = root / 'system/art-book-next-playtime/auto-disabled'
    assert disabled.is_file()
    assert not (root / 'system/retroachievements/config.json').exists()
    enabled = subprocess.run(['sh', str(ports / 'Art Book Next - Enable Achievements Sync.sh'), '--apply'], capture_output=True, text=True, timeout=20)
    assert enabled.returncode == 0, enabled.stdout + enabled.stderr
    # First-time enable must prepare the saved-login backend, not leave a hook
    # which silently fails forever for lack of a config file.
    assert (root / 'system/retroachievements/config.json').is_file()
    for title, should_be_disabled in [('Enable Playtime Sync', False), ('Disable Playtime Sync', True), ('Refresh Saved Playtime', True)]:
        run = subprocess.run(['sh', str(ports / ('Art Book Next - ' + title + '.sh')), '--apply'], capture_output=True, text=True, timeout=20)
        assert run.returncode == 0, run.stdout + run.stderr
        assert disabled.exists() == should_be_disabled
    assert '1h 30m' in (root / 'system/configs/art-book-next-system-playtime/nes.xml').read_text()
    assert '5400' in base.read_text()

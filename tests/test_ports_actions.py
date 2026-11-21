import importlib.util
import subprocess
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

SOURCE = Path(__file__).resolve().parents[1] / 'scripts/retroachievements'
sys.path.insert(0, str(SOURCE))

def module():
    path = SOURCE / 'ports_actions.py'
    assert path.exists(), 'independent Ports actions manager is missing'
    spec = importlib.util.spec_from_file_location('ports_actions', path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def test_install_separate_actions_without_enabling_or_sync(tmp_path):
    m = module()
    m.install_features(tmp_path)
    games = ET.parse(tmp_path/'roms/ports/gamelist.xml').getroot().findall('game')
    assert len(games) == 7
    assert all(g.findtext('desc') for g in games)
    for state in ('retroachievements', 'art-book-next-playtime'):
        assert (tmp_path/'system'/state/'auto-disabled').exists()
    assert not (tmp_path/'system/retroachievements/pending.json').exists()
    assert not (tmp_path/'system/configs/art-book-next-system-playtime').exists()
    m.install_features(tmp_path)
    assert len(ET.parse(tmp_path/'roms/ports/gamelist.xml').getroot().findall('game')) == 7

def test_metadata_preserves_unrelated_and_user_edits(tmp_path):
    m = module()
    ports = tmp_path/'roms/ports'; ports.mkdir(parents=True)
    (ports/'gamelist.xml').write_text('<gameList><!--keep--><game><path>./mine.sh</path><name>Mine</name><custom x="y">keep</custom></game></gameList>')
    m.install_features(tmp_path)
    tree = ET.parse(ports/'gamelist.xml'); tree.getroot().findall('game')[1].find('name').text = 'My custom label'
    tree.write(ports/'gamelist.xml')
    m.install_features(tmp_path)
    root = ET.parse(ports/'gamelist.xml').getroot()
    assert root.findall('game')[0].findtext('custom') == 'keep'
    assert root.findall('game')[1].findtext('name') == 'My custom label'

def test_installed_action_quoting_and_toggle_preservation(tmp_path):
    m = module(); root = tmp_path/"a 'quoted root"
    m.install_features(root)
    for feature, state in [('achievements','retroachievements'), ('playtime','art-book-next-playtime')]:
        marker = root/'system'/state/'auto-disabled'
        m.apply(root, 'enable-'+feature); assert not marker.exists()
        m.install_features(root); assert not marker.exists()
        m.apply(root, 'disable-'+feature); assert marker.exists()
    script = root/'roms/ports/Art Book Next - Enable Playtime Sync.sh'
    result = subprocess.run(['sh', str(script), '--apply'], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert not (root/'system/art-book-next-playtime/auto-disabled').exists()

def test_symlink_and_modified_script_refused(tmp_path):
    import pytest
    m = module(); m.install_features(tmp_path)
    script = tmp_path/'roms/ports/Art Book Next - Enable Playtime Sync.sh'
    script.write_text('user script')
    with pytest.raises(Exception): m.install_features(tmp_path)
    assert script.read_text() == 'user script'
    other = tmp_path/'other'; other.mkdir()
    root = tmp_path/'root'; root.mkdir(); (root/'roms').symlink_to(other)
    with pytest.raises(Exception): m.install_features(root)

def test_disabled_auto_workers_return_without_input(tmp_path):
    m = module(); m.install_features(tmp_path)
    ra = subprocess.run([sys.executable, str(tmp_path/'system/retroachievements/sync.py'), '--automatic', '--data-root', str(tmp_path), '--config', str(tmp_path/'missing')], capture_output=True)
    pt = subprocess.run([sys.executable, str(tmp_path/'system/art-book-next-playtime/auto_refresh.py'), '--data-root', str(tmp_path), '--system', 'nes', '--rom', '/missing', '--since', '1'], capture_output=True)
    assert ra.returncode == 0, ra.stderr
    assert pt.returncode == 0, pt.stderr

"""Saved-gamelist helper tests; fixtures are NOT native visible-game totals."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/system-playtime/refresh.py'

def run(tmp_path, value, *extra):
    source = tmp_path / 'gamelist.xml'
    source.write_text('<gameList><game><gametime>' + str(value) + '</gametime></game></gameList>')
    return subprocess.run([sys.executable, str(SCRIPT), '--output', str(tmp_path/'out'), '--system', 'snes='+str(source), *extra], capture_output=True, text=True)

@pytest.mark.parametrize('seconds,expected', [(0,'0h 0m'),(1,'0h 0m'),(59,'0h 0m'),(60,'0h 1m'),(3599,'0h 59m'),(3600,'1h 0m'),(86399,'23h 59m'),(86400,'24h 0m'),(172800,'48h 0m'),(183845,'51h 4m'),(8643723,'2401h 2m'),(16777259,'4660h 20m'),(2147483647,'596523h 14m')])
def test_saved_seconds_exact(tmp_path, seconds, expected):
    result = run(tmp_path, seconds)
    assert result.returncode == 0, result.stderr
    tree = ET.parse(tmp_path/'out/snes.xml')
    assert tree.findtext('./view/text/text') == expected
    assert set(tree.find('./view/text').attrib) == {'name', 'extra'}
    assert len(tree.find('./view/text')) == 1  # never override approved geometry

def test_aggregate_only_games_and_preserve_inputs(tmp_path):
    source=tmp_path/'games.xml'
    xml='<gameList><game><gametime>3600</gametime></game><game><gametime>65</gametime></game><game/><folder><gametime>9000</gametime></folder></gameList>'
    source.write_text(xml)
    result=subprocess.run([sys.executable,str(SCRIPT),'--output',str(tmp_path/'out'),'--system','snes='+str(source)],capture_output=True)
    assert result.returncode == 0, result.stderr
    assert ET.parse(tmp_path/'out/snes.xml').findtext('./view/text/text') == '1h 1m'
    assert source.read_text()==xml

@pytest.mark.parametrize('value',['-1','1.5','garbage'])
def test_invalid_duration_refuses_publish(tmp_path,value):
    result=run(tmp_path,value)
    assert result.returncode != 0
    assert not (tmp_path/'out/snes.xml').exists()

def test_owned_updates_and_modified_file_refusal(tmp_path):
    assert run(tmp_path,3600).returncode==0
    assert run(tmp_path,7200).returncode==0
    target=tmp_path/'out/snes.xml'
    target.write_text('local edit')
    assert run(tmp_path,9000).returncode!=0
    assert target.read_text()=='local edit'

def test_symlink_refusal(tmp_path):
    (tmp_path/'out').mkdir()
    victim=tmp_path/'victim'; victim.write_text('keep')
    (tmp_path/'out/snes.xml').symlink_to(victim)
    assert run(tmp_path,10).returncode != 0
    assert victim.read_text()=='keep'

def test_concurrent_refresh_refused_without_replacing_totals(tmp_path):
    import fcntl
    assert run(tmp_path, 3600).returncode == 0
    with (tmp_path / 'out/.refresh.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert run(tmp_path, 7200).returncode != 0
    assert ET.parse(tmp_path / 'out/snes.xml').findtext('./view/text/text') == '1h 0m'
    assert run(tmp_path, 7200).returncode == 0


def test_runtime_uses_saved_total_not_colon_binding():
    tree=ET.parse(ROOT/'system-playtime.xml')
    assert tree.findtext('./view/text/text')=='Playtime unavailable'
    assert tree.findtext('./include')=='/userdata/system/configs/art-book-next-system-playtime/${system.name}.xml'
    assert 'system:gameTime' not in (ROOT/'system-playtime.xml').read_text()

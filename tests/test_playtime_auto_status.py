"""Background exit errors remain observable without recording personal paths."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / 'scripts/system-playtime/auto_refresh.py'


def invoke(root):
    return subprocess.run([sys.executable, str(WORKER), '--data-root', str(root), '--refresh-all'], capture_output=True, text=True)


def test_sanitized_status_for_success_and_failure(tmp_path):
    roms = tmp_path / 'roms/nes'
    roms.mkdir(parents=True)
    base = roms / 'gamelist.xml'
    base.write_text('<gameList><game><path>./private-name.nes</path><gametime>3600</gametime></game></gameList>')
    assert invoke(tmp_path).returncode == 0
    status = tmp_path / 'system/configs/art-book-next-system-playtime/.last-result.json'
    assert json.loads(status.read_text())['result'] == 'updated'
    base.write_text('<broken secret-private-name')
    assert invoke(tmp_path).returncode == 1
    data = status.read_text()
    assert json.loads(data)['result'] == 'not-refreshed'
    assert 'private-name' not in data and str(tmp_path) not in data


def test_status_symlink_is_not_followed(tmp_path):
    totals = tmp_path / 'system/configs/art-book-next-system-playtime'
    totals.mkdir(parents=True)
    target = tmp_path / 'user-file'
    target.write_text('private')
    (totals / '.last-result.json').symlink_to(target)
    assert invoke(tmp_path).returncode == 1
    assert target.read_text() == 'private'

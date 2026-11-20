"""Batocera service-name validation and checksum-owned legacy migration."""
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / 'scripts/retroachievements'
sys.path.insert(0, str(SOURCE))
spec = importlib.util.spec_from_file_location('service_installer', SOURCE / 'install.py')
assert spec is not None and spec.loader is not None
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)
OLD = 'system/services/ra-progress-sync'
NEW = 'system/services/ra_progress_sync'
MANIFEST = 'system/retroachievements/install-manifest.json'


def snapshot(root):
    return {str(p.relative_to(root)): (p.read_bytes(), p.stat().st_mode & 0o777)
            for p in root.rglob('*') if p.is_file()}


def legacy(root):
    installer.install(root)
    manifest = root / MANIFEST
    owned = json.loads(manifest.read_text())
    current = root / NEW
    if current.exists():
        current.rename(root / OLD)
        owned[OLD] = owned.pop(NEW)
    (root / OLD).write_bytes(b'#!/bin/sh\n# old managed service\n')
    (root / OLD).chmod(0o750)
    owned[OLD] = hashlib.sha256((root / OLD).read_bytes()).hexdigest()
    manifest.write_text(json.dumps(owned, indent=4) + '\n')
    for name in ('system/batocera.conf', 'system/retroachievements/config.json',
                 'system/services/unrelated', 'system/custom.sh'):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('private unchanged\n')


def test_service_name_and_independent_hook(tmp_path, capsys):
    installer.install(tmp_path)
    services = list((tmp_path / 'system/services').iterdir())
    assert [p.name for p in services] == ['ra_progress_sync']
    assert all(re.fullmatch(r'[_a-zA-Z][_a-zA-Z0-9]*', p.name) for p in services)
    assert (tmp_path / 'system/scripts/ra-progress-sync.sh').exists()
    output = capsys.readouterr().out
    assert 'batocera-services enable ra_progress_sync' in output
    assert 'TTL' in output and 'independent' in output


def test_owned_legacy_upgrade(tmp_path):
    legacy(tmp_path)
    before = snapshot(tmp_path)
    installer.install(tmp_path)
    assert not (tmp_path / OLD).exists()
    assert (tmp_path / NEW).exists()
    owned = json.loads((tmp_path / MANIFEST).read_text())
    assert OLD not in owned and NEW in owned
    for name in before.keys() - owned.keys() - {OLD, MANIFEST}:
        assert snapshot(tmp_path)[name] == before[name]
    installer.install(tmp_path)  # repeat upgrade


@pytest.mark.parametrize('old_install', [True, False])
def test_uninstall_legacy_or_current(tmp_path, old_install):
    legacy(tmp_path) if old_install else installer.install(tmp_path)
    installer.install(tmp_path, uninstall=True)
    assert not (tmp_path / OLD).exists()
    assert not (tmp_path / NEW).exists()
    assert not (tmp_path / MANIFEST).exists()


@pytest.mark.parametrize('name', [OLD, NEW])
@pytest.mark.parametrize('uninstall', [False, True])
def test_modified_or_unmanaged_conflict_preserved(tmp_path, name, uninstall):
    legacy(tmp_path)
    (tmp_path / name).write_text('local modification or unmanaged conflict\n')
    before = snapshot(tmp_path)
    with pytest.raises(installer.SyncError):
        installer.install(tmp_path, uninstall=uninstall)
    assert snapshot(tmp_path) == before


def test_unmanaged_legacy_without_manifest_refused(tmp_path):
    target = tmp_path / OLD
    target.parent.mkdir(parents=True)
    target.write_text('unmanaged\n')
    with pytest.raises(installer.SyncError):
        installer.install(tmp_path)
    assert target.read_text() == 'unmanaged\n'
    assert not (tmp_path / NEW).exists()


@pytest.mark.parametrize('failure', ['manifest', 'legacy_unlink', 'mapping'])
def test_upgrade_rollback_restores_removed_legacy(tmp_path, monkeypatch, failure):
    legacy(tmp_path)
    if failure == 'mapping':
        (tmp_path / 'system/retroachievements/mapping.json').unlink()
    before = snapshot(tmp_path)
    write = installer.atomic_write
    unlink = Path.unlink
    failed = False

    def failing_write(path, data):
        nonlocal failed
        match = path == tmp_path / MANIFEST if failure == 'manifest' else path.name == 'mapping.json'
        if failure != 'legacy_unlink' and match and not failed:
            failed = True
            assert not (tmp_path / OLD).exists(), 'exercise failure after legacy removal'
            raise OSError('injected write failure')
        return write(path, data)

    def failing_unlink(path, *args, **kwargs):
        nonlocal failed
        if failure == 'legacy_unlink' and path == tmp_path / OLD and not failed:
            failed = True
            raise OSError('injected removal failure')
        return unlink(path, *args, **kwargs)

    monkeypatch.setattr(installer, 'atomic_write', failing_write)
    monkeypatch.setattr(Path, 'unlink', failing_unlink)
    with pytest.raises(OSError):
        installer.install(tmp_path)
    assert failed
    assert snapshot(tmp_path) == before

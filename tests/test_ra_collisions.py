"""Ambiguous ES stem outputs must not disable unrelated library progress."""
import importlib.util
import json
from pathlib import Path
import shlex
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest
from test_ra_batocera import rig, SCRIPTS

spec = importlib.util.spec_from_file_location('collision_sync', SCRIPTS / 'sync.py')
assert spec is not None and spec.loader is not None
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


def gamelist(root, entries, system='snes'):
    path = root / 'roms' / system / 'gamelist.xml'
    path.parent.mkdir(parents=True, exist_ok=True)
    tree = ET.Element('gameList')
    for rom, gid in entries:
        game = ET.SubElement(tree, 'game')
        ET.SubElement(game, 'path').text = rom
        if gid is not None:
            ET.SubElement(game, 'cheevosId').text = str(gid)
    path.write_bytes(ET.tostring(tree))
    return path


@pytest.mark.parametrize('other', ['Private.zip', 'sub/Private.sfc', 'PRIVATE.sfc', 'sub/private.ZIP'])
@pytest.mark.parametrize('ids', [(1, 2), (1, None), (None, None)])
def test_skip_entire_ambiguous_group_not_library(tmp_path, capsys, other, ids):
    path = gamelist(tmp_path, [('Private.sfc', ids[0]), (other, ids[1]), ('Safe.sfc', 3)])
    before = path.read_bytes()
    assert sync.mappings({'systems': ['snes'], 'username': 'secret-user', 'api_key': 'secret-key'}, tmp_path, tmp_path) == {('snes', 'Safe.sfc'): 3}
    warning = capsys.readouterr().err
    assert warning == ('Warning: skipped 2 games in 1 ambiguous ROM stem groups; '
                       'Batocera extras share a per-system filename stem. Unambiguous games continue; '
                       'use distinct stems only for affected games to enable their progress.\n')
    assert path.read_bytes() == before


def test_explicit_override_deduplicates_paths_but_cannot_resolve_collision(tmp_path, capsys):
    gamelist(tmp_path, [('./Private.sfc', 99), ('sub/private.zip', None), ('Safe.sfc', 99)])
    mapping = tmp_path / 'mapping.json'
    mapping.write_text(json.dumps([
        {'system': 'snes', 'rom': 'Private.sfc', 'game_id': 1},
        {'system': 'snes', 'rom': str(tmp_path / 'roms/snes/Safe.sfc'), 'game_id': 3},
        {'system': 'nes', 'rom': 'Private.nes', 'game_id': 4},
        {'system': 'SNES', 'rom': 'private.rom', 'game_id': 5},
    ]))
    assert sync.mappings({'systems': ['snes'], 'mapping_file': str(mapping)}, tmp_path, tmp_path) == {('snes', 'Safe.sfc'): 3, ('nes', 'Private.nes'): 4}
    assert 'skipped 3 games in 1 ambiguous ROM stem groups' in capsys.readouterr().err


def test_multiple_groups_count_games_not_ids_or_duplicate_records(tmp_path, capsys):
    gamelist(tmp_path, [('First.sfc', 1), ('First.zip', 1), ('sub/FIRST.rom', None),
                       ('Second.sfc', None), ('Second.zip', None),
                       ('Safe.sfc', 3), ('./Safe.sfc', 3)])
    assert sync.mappings({'systems': ['snes']}, tmp_path, tmp_path) == {('snes', 'Safe.sfc'): 3}
    warning = capsys.readouterr().err
    assert 'skipped 5 games in 2 ambiguous ROM stem groups' in warning
    assert len(warning.splitlines()) == 1


@pytest.mark.parametrize('targeted', [False, True])
def test_new_collision_prunes_owned_extras_with_full_mapping_reconciliation(rig, targeted):
    gamelist(rig.root, [('Game.sfc', 1), ('Keep.sfc', 1)])
    assert rig.sync().returncode == 0
    assert rig.output.exists()  # This must actually be previously owned, not absent all along.
    state = rig.config.parent
    manifest = state / 'extras-manifest.json'
    assert 'snes/Game.xml' in json.loads(manifest.read_text())
    keep = rig.output.with_name('Keep.xml')
    before = keep.read_bytes()
    unrelated = rig.output.with_name('Unrelated.xml'); unrelated.write_text('private unrelated XML')
    asset = state / 'assets/unrelated.svg'; asset.write_text('private unrelated asset')
    gamelist(rig.root, [('Game.sfc', 1), ('sub/GAME.zip', None), ('Keep.sfc', 1), ('New.sfc', 1)])
    p = rig.sync(*(['--system', 'snes', '--rom', 'New.sfc'] if targeted else []))
    assert p.returncode == 0, p.stderr
    assert not rig.output.exists()
    assert set(json.loads(manifest.read_text())) == {'snes/Keep.xml', 'snes/New.xml'}
    assert keep.read_bytes() == before and keep.with_name('New.xml').exists()
    assert unrelated.read_text() == 'private unrelated XML'
    assert asset.read_text() == 'private unrelated asset'
    assert 'skipped 2 games in 1 ambiguous ROM stem groups' in p.stderr
    assert all(value not in p.stderr + p.stdout for value in ['GAME', 'Game.sfc', 'fixture-user', 'fixture-token', 'NEVER-USE-PASSWORD'])


def test_new_collision_never_deletes_modified_owned_extra(rig):
    assert rig.sync().returncode == 0
    rig.output.write_text('local edit')
    gamelist(rig.root, [('Game.sfc', 1), ('sub/game.zip', None)])
    p = rig.sync()
    assert p.returncode == 2
    assert rig.output.read_text() == 'local edit'
    assert 'modified' in p.stderr


def test_all_ambiguous_prunes_owned_assets_but_keeps_changed_and_unowned(rig):
    assert rig.sync().returncode == 0
    assets = list((rig.config.parent / 'assets').glob('*.svg'))
    assert len(assets) == 3  # fill, track, exact native trophy outline
    assets[0].write_text('local asset edit')
    unrelated = assets[0].with_name('unrelated.svg'); unrelated.write_text('keep')
    gamelist(rig.root, [('Game.sfc', 1), ('Game.zip', None)])
    p = rig.sync()
    assert p.returncode == 0, p.stderr
    assert not rig.output.exists()
    assert assets[0].read_text() == 'local asset edit'
    assert all(not asset.exists() for asset in assets[1:])
    assert unrelated.read_text() == 'keep'
    assert len(rig.requests) == 3  # No API request for ambiguous games.


def test_configure_prints_executable_full_command_with_quoted_paths(tmp_path):
    root = tmp_path / "root with 'quote"
    p = subprocess.run([sys.executable, str(SCRIPTS / 'configure.py'), '--data-root', str(root)], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    command = p.stdout.splitlines()[-1]
    assert shlex.split(command) == ['python3', str(root / 'system/retroachievements/sync.py'), '--config', str(root / 'system/retroachievements/config.json'), '--data-root', str(root)]

"""Ports system-total discovery uses native system IDs, not theme aliases."""
import importlib.util
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]


def module():
    p = ROOT / 'scripts/playtime_discovery.py'
    assert p.exists(), 'Missing Ports gamelist discovery'
    spec = importlib.util.spec_from_file_location('playtime_discovery', p)
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_native_ids_and_rom_path_priority(tmp_path):
    config = tmp_path / 'system/configs/emulationstation'
    config.mkdir(parents=True)
    rom = tmp_path / 'roms/custom snes'
    rom.mkdir(parents=True)
    (rom / 'gamelist.xml').write_text('<gameList/>')
    (config / 'es_systems.cfg').write_text(f'<systemList><system><name>snes</name><path>{rom}</path><theme>sfc</theme></system></systemList>')
    result = module().discover(tmp_path, tmp_path / 'stock')
    assert result == [f'snes={rom}/gamelist.xml']


def test_user_fallback_and_additional_override(tmp_path):
    config = tmp_path / 'system/configs/emulationstation'
    config.mkdir(parents=True)
    (config / 'es_systems.cfg').write_text('<systemList><system><name>gb</name><path>/missing</path></system></systemList>')
    saved = config / 'gamelists/gb'
    saved.mkdir(parents=True)
    (saved / 'gamelist.xml').write_text('<gameList/>')
    assert module().discover(tmp_path, tmp_path / 'stock') == [f'gb={saved}/gamelist.xml']
    new = tmp_path / 'new location'
    new.mkdir()
    (new / 'gamelist.xml').write_text('<gameList/>')
    (config / 'es_systems_extra.cfg').write_text(f'<systemList><system><name>gb</name><path>{new}</path></system></systemList>')
    assert module().discover(tmp_path, tmp_path / 'stock') == [f'gb={new}/gamelist.xml']


def test_standard_directory_fallback_when_config_absent(tmp_path):
    rom = tmp_path / 'roms/c64'
    rom.mkdir(parents=True)
    (rom / 'gamelist.xml').write_text('<gameList/>')
    assert module().discover(tmp_path, tmp_path / 'stock') == [f'c64={rom}/gamelist.xml']


def test_details_preserve_configured_rom_root_with_fallback_gamelist(tmp_path):
    config = tmp_path / 'system/configs/emulationstation'
    saved = config / 'gamelists/nes/gamelist.xml'
    saved.parent.mkdir(parents=True)
    saved.write_text('<gameList/>')
    (config / 'es_systems.cfg').write_text('<systemList><system><name>nes</name>'
        '<path>/userdata/roms/custom nes</path><theme>famicom</theme></system></systemList>')
    assert module().discover_details(tmp_path, tmp_path / 'stock') == {
        'nes': {'gamelist': saved, 'rom_root': tmp_path / 'roms/custom nes'}}
    assert module().discover(tmp_path, tmp_path / 'stock') == [f'nes={saved}']


def test_invalid_config_is_not_silently_reinterpreted(tmp_path):
    config = tmp_path / 'system/configs/emulationstation'
    config.mkdir(parents=True)
    (config / 'es_systems.cfg').write_text('<broken')
    with pytest.raises(ValueError):
        module().discover(tmp_path, tmp_path / 'stock')

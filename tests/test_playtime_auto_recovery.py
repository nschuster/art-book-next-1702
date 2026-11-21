"""Repeated automatic writes must recover an interrupted ownership commit."""
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]


def helper():
    spec = importlib.util.spec_from_file_location('hours_journal_test', ROOT / 'scripts/system-playtime/refresh.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('previous', [False, True])
def test_interrupted_journal_commit_is_recoverable(tmp_path, monkeypatch, previous):
    m = helper()
    base = tmp_path / 'gamelist.xml'
    out = tmp_path / 'totals'
    base.write_text('<gameList><game><gametime>3600</gametime></game></gameList>')
    if previous:
        m.refresh([f'nes={base}'], out)
    base.write_text('<gameList><game><gametime>7200</gametime></game></gameList>')
    atomic = m.atomic
    def fail_manifest(path, data):
        if path.name == '.owned.json':
            raise OSError('simulated interruption before manifest commit')
        return atomic(path, data)
    with monkeypatch.context() as patch:
        patch.setattr(m, 'atomic', fail_manifest)
        with pytest.raises(OSError):
            m.refresh([f'nes={base}'], out)
    assert m.refresh([f'nes={base}'], out) == 1
    assert b'2h 0m' in (out / 'nes.xml').read_bytes()


def test_user_modified_output_after_interruption_is_preserved(tmp_path, monkeypatch):
    m = helper()
    base = tmp_path / 'gamelist.xml'
    out = tmp_path / 'totals'
    base.write_text('<gameList><game><gametime>3600</gametime></game></gameList>')
    atomic = m.atomic
    def fail_manifest(path, data):
        if path.name == '.owned.json':
            raise OSError('simulated interruption')
        return atomic(path, data)
    with monkeypatch.context() as patch:
        patch.setattr(m, 'atomic', fail_manifest)
        with pytest.raises(OSError):
            m.refresh([f'nes={base}'], out)
    (out / 'nes.xml').write_text('user edit')
    with pytest.raises(ValueError):
        m.refresh([f'nes={base}'], out)
    assert (out / 'nes.xml').read_text() == 'user edit'

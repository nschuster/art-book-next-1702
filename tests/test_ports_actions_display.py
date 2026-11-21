"""Ports display regression coverage using the renderer's actual font metrics."""
import sys
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / 'scripts/retroachievements'
sys.path.insert(0, str(SOURCE))
import ports_actions as ports
from progress_ui import text_width


class Child:
    def __init__(self, code):
        self.returncode = code

    def poll(self):
        return self.returncode


def rendered(screen):
    layout = screen.layout()
    for x, y, text, scale in layout:
        assert x >= 32 and y >= 32
        assert text_width(text, scale) <= 576
        assert x + text_width(text, scale) <= 608
        assert y + round(30 * scale) <= 448
        assert '...' not in text
    for before, after in zip(layout, layout[1:]):
        assert before[1] + round(30 * before[3]) <= after[1]
    return ' '.join(row[2] for row in layout)


@pytest.mark.parametrize('action', ports.ACTIONS)
@pytest.mark.parametrize('state', ['initial', 'working', 'success', 'failure'])
def test_complete_content_for_every_action_and_result(tmp_path, action, state):
    screen = ports.ActionScreen(tmp_path, action)
    if state != 'initial':
        screen.child = Child({'working': None, 'success': 0, 'failure': 2}[state])
    text = rendered(screen)
    assert ports.ACTIONS[action][0].upper() in text
    assert ports.ACTIONS[action][1] in text
    assert '[ ] Achievements sync: Not installed' in text
    assert '[ ] Playtime sync: Not installed' in text
    assert 'Automatic settings, not running status.' in text
    assert 'B / Back / Esc: Exit' in text
    if state == 'initial':
        assert 'A / Enter: Confirm' in text
    elif state == 'working':
        assert 'Working locally. Please wait.' in text
    elif state == 'failure':
        assert 'Action refused; check local files / settings.' in text
    else:
        assert 'Complete.' in text
        if action == 'install':
            assert 'Use native Update Gamelists to see entries.' in text
            assert 'No sync started. Existing settings preserved.' in text
        elif action == 'refresh-playtime':
            assert 'Reload the theme to display saved totals.' in text
        elif action.startswith('disable-'):
            assert 'Automatic workers stop at a safe boundary.' in text
            assert 'Saved data retained. Manual refresh available.' in text


@pytest.mark.parametrize('folder,label', [('retroachievements', 'Achievements'), ('art-book-next-playtime', 'Playtime')])
def test_live_read_only_status_and_child_completion(tmp_path, folder, label):
    screen = ports.ActionScreen(tmp_path, 'install')
    assert f'[ ] {label} sync: Not installed' in rendered(screen)
    state = tmp_path / 'system' / folder
    state.mkdir(parents=True)
    manifest = state / 'install-manifest.json'
    manifest.write_text('{}')
    assert f'[x] {label} sync: Enabled' in rendered(screen)
    marker = state / 'auto-disabled'
    marker.write_text('disabled')
    screen.child = Child(0)
    assert f'[ ] {label} sync: Disabled' in rendered(screen)
    assert screen.result == 0 and screen.child is None
    marker.unlink()
    assert f'[x] {label} sync: Enabled' in rendered(screen)
    manifest.unlink()
    assert f'[ ] {label} sync: Not installed' in rendered(screen)
    assert list(state.iterdir()) == []


def test_absent_root_is_not_created(tmp_path):
    root = tmp_path / 'missing'
    assert 'Not installed' in rendered(ports.ActionScreen(root, 'install'))
    assert not root.exists()


@pytest.mark.parametrize('unsafe', ['root', 'system', 'retroachievements', 'install-manifest.json', 'auto-disabled'])
def test_unsafe_paths_are_unavailable(tmp_path, unsafe):
    root = tmp_path / 'root'
    state = root / 'system/retroachievements'
    state.mkdir(parents=True)
    (state / 'install-manifest.json').write_text('{}')
    target = tmp_path / 'outside'
    target.mkdir()
    path = {'root': root, 'system': root / 'system', 'retroachievements': state}.get(unsafe, state / unsafe)
    if path.is_dir():
        import shutil
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()
    path.symlink_to(target)
    assert '[?] Achievements sync: Unavailable' in rendered(ports.ActionScreen(root, 'install'))
    assert list(target.iterdir()) == []


def test_state_io_error_is_unavailable(tmp_path, monkeypatch):
    original = Path.stat
    def denied(path, *args, **kwargs):
        if path.name == 'install-manifest.json':
            raise PermissionError('denied')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'stat', denied)
    assert '[?] Achievements sync: Unavailable' in rendered(ports.ActionScreen(tmp_path, 'install'))

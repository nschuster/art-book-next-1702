"""Real bootstrap/install fixtures; no live RA credentials or network."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

SOURCE = Path(__file__).resolve().parents[1] / 'scripts/retroachievements'
BOOT = SOURCE / 'Install Art Book Next Features.sh'


def fixture(tmp_path, auth=True):
    root = tmp_path / "user data's"
    theme = root / "themes/My theme's name"
    shutil.copytree(SOURCE, theme / 'scripts/retroachievements', ignore=shutil.ignore_patterns('__pycache__'))
    (root / 'system/configs/emulationstation').mkdir(parents=True)
    (root / 'system/configs/emulationstation/es_settings.cfg').write_text('<config><string name="ThemeSet" value="My theme\'s name" /></config>')
    (root / 'system/batocera.conf').write_text('global.retroachievements=1\nglobal.retroachievements.username=fixture\nglobal.retroachievements.token=SECRET_FIXTURE\n' if auth else '')
    (root / 'roms/snes').mkdir(parents=True)
    (root / 'roms/snes/gamelist.xml').write_text('<gameList/>')
    return root, theme


def run(root, *args, env=None):
    copied = root / 'roms/ports/Install Art Book Next Features.sh'
    copied.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(BOOT, copied)
    # Preserve explicit compatibility coverage; default/new entry semantics are
    # exercised separately in test_ports_actions_bundle.py.
    return subprocess.run(['sh', str(copied), '--legacy-setup', '--data-root', str(root), *args], input='', text=True, capture_output=True, timeout=20, env=env)


def test_bootstrap_installs_and_repeats_without_sync(tmp_path):
    root, _ = fixture(tmp_path)
    result = run(root, '--apply')
    assert result.returncode == 0, result.stderr
    state = root / 'system/retroachievements'
    cfg = state / 'config.json'
    original = cfg.read_bytes()
    assert json.loads(original)['backend'] == 'batocera'
    assert cfg.stat().st_mode & 0o777 == 0o600
    assert (root / 'roms/ports/Refresh RetroAchievements Progress.sh').exists()
    assert (root / 'system/scripts/ra-progress-sync.sh').exists()
    assert not (state / 'progress.json').exists()
    assert not (state / 'launcher-process.json').exists()
    assert not (root / 'system/scripts/art-book-playtime.sh').exists()
    assert not (root / 'system/art-book-next-playtime').exists()
    assert run(root, '--apply').returncode == 0
    assert cfg.read_bytes() == original
    assert 'SECRET_FIXTURE' not in result.stdout + result.stderr


def test_missing_login_fails_before_install(tmp_path):
    root, _ = fixture(tmp_path, False)
    assert run(root, '--apply').returncode == 10
    assert not (root / 'system/retroachievements/config.json').exists()
    assert not (root / 'system/scripts/ra-progress-sync.sh').exists()


def test_conflict_preserves_files_and_config(tmp_path):
    root, _ = fixture(tmp_path)
    assert run(root, '--apply').returncode == 0
    state = root / 'system/retroachievements'
    (state / 'sync.py').write_text('# local change\n')
    before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
    assert run(root, '--apply').returncode == 12
    assert all(p.read_bytes() == b for p, b in before.items())


def test_dummy_screen_does_not_install_without_confirm(tmp_path):
    root, _ = fixture(tmp_path)
    capture = tmp_path / 'screen.bmp'
    result = run(root, '--windowed', '--frames', '2', '--screenshot', str(capture), env=dict(os.environ, SDL_VIDEODRIVER='dummy'))
    assert result.returncode == 0, result.stderr
    assert capture.read_bytes()[:2] == b'BM'
    assert not (root / 'system/scripts/ra-progress-sync.sh').exists()


def load_setup():
    spec = importlib.util.spec_from_file_location('ports_setup', SOURCE / 'ports_setup.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_startup_is_explicit_and_never_starts_service(tmp_path):
    module = load_setup()
    root, _ = fixture(tmp_path)
    service = tmp_path / 'service tool'
    service.write_text('#!/usr/bin/env python3\nimport sys\nfrom pathlib import Path\np=Path(' + repr(str(root / 'system/batocera.conf')) + ')\np.write_text(p.read_text()+"system.services="+("ra_progress_sync other" if sys.argv[1]=="enable" else "other")+"\\n")\nassert sys.argv[1] in ("enable", "disable")\nassert sys.argv[2]=="ra_progress_sync"\n')
    service.chmod(0o755)
    assert module.startup_enabled(root) is False
    assert module.set_startup(root, True, command=str(service)) == 0
    assert module.startup_enabled(root) is True
    assert module.set_startup(root, False, command=str(service)) == 0
    assert module.startup_enabled(root) is False
    assert module.set_startup(root, True, command='/nonexistent') == 14


def test_startup_panel_requires_separate_confirmation(tmp_path):
    sys.path.insert(0, str(SOURCE))
    from progress_ui import event
    module = load_setup()
    root, _ = fixture(tmp_path)
    screen = module.SetupScreen(root)
    screen.result = 0
    screen.handle_event(event(0x651, button=2))
    assert screen.startup_menu
    assert screen.child is None
    assert any('boot' in row[2] for row in screen.layout())
    screen.handle_event(event(0x651, button=2))
    assert not screen.startup_menu
    assert not module.startup_enabled(root)


def test_real_sdl_confirm_installs_and_renders_success(tmp_path):
    root, _ = fixture(tmp_path)
    code = '''
import ctypes, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from progress_ui import run_ui, load_sdl, event
from ports_setup import SetupScreen
screen = SetupScreen(Path(sys.argv[2]))
def confirm():
    ev = event(0x651, button=0)
    load_sdl().SDL_PushEvent(ctypes.byref(ev))
assert run_ui(None, screen=screen, start_callback=confirm, fullscreen=False, frames=30) == 0
assert screen.result == 0
assert any('Installation complete' in item[2] for item in screen.layout())
assert not screen.open_refresh
'''
    result = subprocess.run([sys.executable, '-c', code, str(SOURCE), str(root)], capture_output=True, text=True, env=dict(os.environ, SDL_VIDEODRIVER='dummy'), timeout=15)
    assert result.returncode == 0, result.stderr
    assert (root / 'system/scripts/ra-progress-sync.sh').exists()
    assert not (root / 'system/retroachievements/launcher-process.json').exists()


def test_existing_manual_config_custom_files_and_startup_preserved(tmp_path):
    root, _ = fixture(tmp_path, False)
    state = root / 'system/retroachievements'
    state.mkdir(parents=True)
    config = state / 'config.json'
    config.write_text(json.dumps({'backend': 'webapi', 'username': 'fixture', 'api_key': 'PRIVATE', 'systems': [], 'template': {'font': 'custom'}}))
    config.chmod(0o600)
    (state / 'mapping.json').write_text('[ ]\n')
    (root / 'system/custom.sh').write_text('# custom\n')
    (root / 'system/batocera.conf').write_text('system.services=other ra_progress_sync\n')
    keep = [config, state / 'mapping.json', root / 'system/custom.sh', root / 'system/batocera.conf']
    before = {p: (p.read_bytes(), p.stat().st_uid, p.stat().st_gid, p.stat().st_mode) for p in keep}
    assert run(root, '--apply').returncode == 0
    assert all((p.read_bytes(), p.stat().st_uid, p.stat().st_gid, p.stat().st_mode) == data for p, data in before.items())
    # A normal non-Ports installer update retains opt-in.
    installed = subprocess.run([sys.executable, str(find_theme_helper(root) / 'install.py'), '--data-root', str(root)], capture_output=True)
    assert installed.returncode == 0
    assert (root / 'roms/ports/Refresh RetroAchievements Progress.sh').exists()


def find_theme_helper(root):
    return root / "themes/My theme's name/scripts/retroachievements"


def test_unsafe_config_is_secret_safe(tmp_path):
    root, _ = fixture(tmp_path)
    state = root / 'system/retroachievements'
    state.mkdir(parents=True)
    private = tmp_path / 'PRIVATE'
    private.write_text('do not change')
    (state / 'config.json').symlink_to(private)
    result = run(root, '--apply')
    assert result.returncode == 12
    assert 'Traceback' not in result.stderr
    assert private.read_text() == 'do not change'
    assert not (root / 'system/scripts/ra-progress-sync.sh').exists()


def test_bootstrap_payload_is_reproducible():
    spec = importlib.util.spec_from_file_location('build_ports_setup', SOURCE / 'build_ports_setup.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert BOOT.read_text() == module.build()


def test_error_screen_retry_and_invalid_sdl_are_safe(tmp_path):
    sys.path.insert(0, str(SOURCE))
    from progress_ui import event
    module = load_setup()
    screen = module.SetupScreen(tmp_path / 'absent')
    screen.handle_event(event(0x651, button=0))
    assert screen.child is not None
    screen.child.wait(timeout=10)
    screen.layout()
    assert screen.result == 11
    root, _ = fixture(tmp_path)
    result = run(root, '--frames', '1', env=dict(os.environ, SDL_VIDEODRIVER='nonexistent-driver'))
    assert result.returncode == 2
    assert not (root / 'system/scripts/ra-progress-sync.sh').exists()


def test_bootstrap_uses_updated_local_setup_without_recopy(tmp_path):
    root, theme = fixture(tmp_path)
    (theme / 'scripts/retroachievements/ports_setup.py').write_text('print("LOCAL_SETUP_REVISION")\n')
    result = run(root, '--apply')
    assert result.returncode == 0
    assert 'LOCAL_SETUP_REVISION' in result.stdout


def test_missing_theme_still_opens_error_screen(tmp_path):
    root = tmp_path / 'absent'
    assert run(root, '--apply').returncode == 11
    result = run(root, '--windowed', '--frames', '2', env=dict(os.environ, SDL_VIDEODRIVER='dummy'))
    assert result.returncode == 0, result.stderr

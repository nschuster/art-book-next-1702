#!/usr/bin/env python3
"""Local-only controller setup, also embedded in the standalone Ports bootstrap."""
import argparse
import ctypes
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

MESSAGES = {
    10: ('Saved RA login missing or disabled', 'Enable RA and log in in Game Settings.'),
    11: ('Theme helper sources not found', 'Copy the updated theme into share/themes.'),
    12: ('Install refused; files preserved', 'Stop sync; check modified files / safe paths.'),
    13: ('Private configuration needs attention', 'Existing settings were not overwritten.'),
    14: ('Startup setting could not be changed', 'Check Batocera service support.'),
    15: ('Playtime refresh refused', 'Check saved gamelists / modified totals.'),
    16: ('Background updates enabled; initial refresh failed', 'Check saved gamelists / modified totals.'),
}


def find_source(root):
    required = ('install.py', 'configure.py', 'sync.py', 'launcher.py', 'progress_ui.py', 'ui_palette.py', 'config.example.json', 'ui-assets/font.bmp')
    def valid(theme):
        helper = theme / 'scripts/retroachievements'
        return helper if all((helper / name).is_file() for name in required) else None
    settings = root / 'system/configs/emulationstation/es_settings.cfg'
    try:
        for item in ET.parse(settings).getroot().iter('string'):
            if item.get('name') == 'ThemeSet':
                name = item.get('value', '')
                if name and Path(name).name == name and name not in ('.', '..'):
                    source = valid(root / 'themes' / name)
                    if source: return source
    except (OSError, ET.ParseError):
        pass
    for name in ('art-book-next-1702-master', 'art-book-next-1702'):
        source = valid(root / 'themes' / name)
        if source: return source
    candidates = [p for theme in (root / 'themes').glob('*') if (p := valid(theme))]
    return candidates[0] if len(candidates) == 1 else None


def apply(root):
    source = find_source(root)
    if source is None: return 11
    # Imports are from the selected local theme, never downloaded or from cwd.
    sys.path.insert(0, str(source))
    try:
        import sync
        import install
        import configure
        root = sync.safe_path(root)
        config = sync.safe_path(root / 'system/retroachievements/config.json')
        try:
            cfg = sync.load_config(config) if config.exists() else {'backend': 'batocera'}
        except (OSError, ValueError, sync.SyncError, AttributeError):
            return 13
        if cfg.get('backend', 'webapi') == 'batocera':
            auth = sync.batocera_settings(root)
            if not auth['enabled'] or not auth['username'] or not auth['token']:
                return 10
        try:
            install.install(root, ports_menu=True)
        except (OSError, ValueError, sync.SyncError):
            return 12
        if not config.exists():
            try: configure.configure(root)
            except (OSError, ValueError): return 13
        return 0
    except Exception:
        # A local-source import/path failure must not expose a traceback or secrets.
        return 12


def refresh_playtime(root):
    source = find_source(root)
    candidates = ([source.parent / 'system-playtime'] if source else [])
    candidates += [Path(__file__).resolve().parent / 'system-playtime']
    candidates += sorted((root / 'themes').glob('*/scripts/system-playtime'))
    source = next((path for path in candidates if all((path / name).is_file()
                   for name in ('install.py', 'auto_refresh.py', 'refresh.py'))), None)
    if source is None:
        return 11
    def load(path, name):
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise ValueError('missing helper')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    enabled = False
    try:
        installer = load(source / 'install.py', 'playtime_installer')
        installer.install(root)
        enabled = True
        result = subprocess.run([sys.executable, str(root / 'system/art-book-next-playtime/auto_refresh.py'),
                                 '--data-root', str(root), '--refresh-all'],
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return 0 if result.returncode == 0 else 16
    except (OSError, ValueError, ET.ParseError, ImportError):
        return 16 if enabled else 15


def startup_enabled(root):
    value = ''
    try:
        for line in (root / 'system/batocera.conf').read_text().splitlines():
            key, sep, text = line.partition('=')
            if sep and key.strip() == 'system.services': value = text.strip()
    except OSError:
        return False
    return 'ra_progress_sync' in value.split()


def set_startup(root, enabled, command='/usr/bin/batocera-services'):
    # enable/disable modifies scheduling only: never invoke start/restart.
    try:
        result = subprocess.run([command, 'enable' if enabled else 'disable', 'ra_progress_sync'],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        return 0 if result.returncode == 0 and startup_enabled(root) == enabled else 14
    except (OSError, subprocess.TimeoutExpired):
        return 14


class SetupScreen:
    def __init__(self, root):
        self.root = root
        self.child = None
        self.result = None if find_source(root) else 11
        self.open_refresh = False
        self.startup_menu = False
        self.task = 'install'
        self.playtime_result = None

    def handle_event(self, ev):
        key = ctypes.c_int32.from_buffer(ev, 20).value if ev.type == 0x300 else None
        if self.child is not None: return
        if ev.type == 0x651 and ev.padding[12] == 3 or key == 121:
            self.task = 'playtime'
            self.playtime_result = None
            self.child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()),
                '--data-root', str(self.root), '--playtime'], stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        if self.playtime_result is not None:
            if ev.type == 0x651 and ev.padding[12] == 0 or key == 13:
                self.playtime_result = None
            return
        self.task = 'install'
        if (ev.type == 0x651 and ev.padding[12] == 2 or key == 120) and self.result in (0, 14):
            self.startup_menu = not self.startup_menu
            self.result = 0
            return
        accept = ev.type == 0x651 and ev.padding[12] == 0 or key == 13
        if not accept: return
        if self.startup_menu:
            self.child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()),
                '--data-root', str(self.root), '--startup',
                'disable' if startup_enabled(self.root) else 'enable'],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif self.result == 0:
            self.open_refresh = True
            # Queue a quit; run_ui releases all SDL resources before refresh opens.
            from progress_ui import load_sdl, event
            quit_event = event(0x100)
            load_sdl().SDL_PushEvent(ctypes.byref(quit_event))
        else:
            self.result = None
            self.child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()),
                '--data-root', str(self.root), '--apply'], stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def layout(self):
        from progress_ui import ellipsis
        if self.child is not None and self.child.poll() is not None:
            if self.task == 'playtime':
                self.playtime_result = self.child.returncode
            else:
                self.result = self.child.returncode
            self.child = None
        lines = ['ART BOOK NEXT SETUP']
        if self.child is not None:
            lines += ['Refreshing saved playtime...' if self.task == 'playtime' else 'Installing local helper...', 'Please wait. No library sync is started.', 'Existing private settings are preserved.']
        elif self.playtime_result is not None:
            if self.playtime_result == 0:
                lines += ['Saved totals refreshed: hours / minutes', 'Reload the theme to see the new totals.', 'Background updates enabled after games.']
            else:
                lines += list(MESSAGES.get(self.playtime_result, MESSAGES[15]))
            lines += ['A / Enter: Back', 'Y: Refresh saved playtime', 'B / Back / Esc: Exit']
        elif self.startup_menu and self.result == 0:
            enabled = startup_enabled(self.root)
            lines += ['Optional startup sync: ' + ('ON' if enabled else 'OFF'),
                      'May queue your entire library at next boot.',
                      'After-game refresh works independently.',
                      'A / Enter: ' + ('Disable startup sync' if enabled else 'Enable startup sync'),
                      'X: Back to success screen', 'B / Back / Esc: Exit']
        elif self.result == 0:
            lines += ['Installation complete', 'Refresh screen + after-game hook ready.', 'No full sync started. Startup unchanged.', 'A / Enter: Open full-library refresh', 'X: Optional startup sync', 'B / Back / Esc: Exit']
        elif self.result is not None:
            title, detail = MESSAGES.get(self.result, MESSAGES[12])
            lines += [title, detail, 'A / Enter: Retry setup', 'B / Back / Esc: Exit']
        else:
            lines += ['Install / update local features', 'Uses your saved Batocera RA login.', 'Refresh screen + after-game hook.', 'No download or automatic full sync.', 'A / Enter: Install / update', 'B / Back / Esc: Exit']
        if self.child is None and self.playtime_result is None and not self.startup_menu:
            lines.insert(-1, 'Y: Enable auto playtime + refresh')
        return [(32, y, ellipsis(text, 576), 1.0) for y, text in zip((28, 90, 138, 180, 230, 310, 366, 418), lines)]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, default=Path('/userdata'))
    parser.add_argument('--apply', action='store_true', help='noninteractive local installation; no sync')
    parser.add_argument('--startup', choices=('enable', 'disable'), help='explicit scheduling change only; never starts sync')
    parser.add_argument('--playtime', action='store_true', help='refresh saved system totals independently of RA')
    parser.add_argument('--windowed', action='store_true')
    parser.add_argument('--frames', type=int)
    parser.add_argument('--screenshot', type=Path)
    args = parser.parse_args(argv)
    if args.frames is not None and args.frames < 1: parser.error('positive frames required')
    root = args.data_root.absolute()
    source = find_source(root)
    local_setup = source / 'ports_setup.py' if source else None
    if local_setup is not None and local_setup.is_file() and local_setup.resolve() != Path(__file__).resolve():
        # Keep the one-time copied entry current when the local theme is updated.
        os.execv(sys.executable, [sys.executable, str(local_setup), *(sys.argv[1:] if argv is None else argv)])
    if args.startup:
        if root != Path('/userdata') or not (root / 'system/services/ra_progress_sync').is_file(): return 14
        return set_startup(root, args.startup == 'enable')
    if args.playtime:
        result = refresh_playtime(root)
        print('Saved playtime refreshed; reload the theme.' if result == 0 else MESSAGES.get(result, MESSAGES[15])[0])
        return result
    if args.apply:
        result = apply(root)
        print('Setup complete; no sync started.' if result == 0 else MESSAGES.get(result, MESSAGES[12])[0])
        return result
    from progress_ui import run_ui
    screen = SetupScreen(root)
    result = run_ui(None, screen=screen, data_root=args.data_root, fullscreen=not args.windowed,
                    frames=args.frames, screenshot=args.screenshot)
    # An in-progress local installation is allowed to finish if the screen closes.
    if screen.child is not None: screen.child.wait()
    if result == 0 and screen.open_refresh:
        return subprocess.call([sys.executable, str(root / 'system/retroachievements/launcher.py'), '--data-root', str(root)])
    return result


if __name__ == '__main__':
    raise SystemExit(main())

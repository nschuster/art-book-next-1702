#!/usr/bin/env python3
"""Independent, controller-friendly Ports actions; installation is not consent to sync."""
import argparse
import ctypes
import fcntl
import importlib.util
import json
import os
import re
from pathlib import Path
import shlex
import subprocess
import sys
import xml.etree.ElementTree as ET

from sync import safe_path, atomic_write, SyncError
from install import digest

ACTIONS = {
    'install': ('Install Features', 'Install or update local helpers and these Ports entries. Does not enable automatic sync or refresh your library. Existing enable settings are preserved. Use Update Gamelists after first installation.'),
    'enable-achievements': ('Enable Achievements Sync', 'Enable automatic achievement progress refresh after games. Uses your saved Batocera RA login. Does not start a full-library refresh. Existing optional startup scheduling is preserved.'),
    'disable-achievements': ('Disable Achievements Sync', 'Suppress after-game and optional startup achievement sync, and stop automatic work at a safe boundary. Credentials, cached progress and manual refresh remain available.'),
    'enable-playtime': ('Enable Playtime Sync', 'Enable background updates from saved gamelists after games. No achievements login or network needed. Display changes on a later theme reload; no refresh starts now.'),
    'disable-playtime': ('Disable Playtime Sync', 'Stop automatic saved-playtime updates. Keep existing totals. Manual Refresh Saved Playtime still works.'),
    'refresh-achievements': ('Refresh Achievement Progress', 'Manually refresh mapped achievement progress using your saved login, even when automatic sync is disabled. Opens the progress screen; closing it leaves the bounded worker running. Reselect a game to reload progress.'),
    'refresh-playtime': ('Refresh Saved Playtime', 'Recompute saved system totals in hours and minutes without enabling automatic sync. Reads local gamelists and recovery saves only. Reload the theme to display updated totals.'),
}


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, safe_path(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def durable_write(path, data):
    atomic_write(path, data)
    sync_directory(path.parent)


def owned_files(value, allowed):
    if (not isinstance(value, dict) or set(value) - set(allowed) or
            any(not isinstance(v, str) or not re.fullmatch(r'[0-9a-f]{64}', v) for v in value.values())):
        raise SyncError('invalid Ports ownership record')
    return value


def recover_ownership(root, pending, old, allowed):
    old_files = owned_files(old.get('files'), allowed) if isinstance(old, dict) else owned_files(None, allowed)
    if not pending.exists():
        return old_files
    if pending.stat().st_size > 32768:
        raise SyncError('invalid Ports pending record')
    transaction = json.loads(pending.read_bytes())
    if not isinstance(transaction, dict) or set(transaction) != {'old', 'new', 'allowed'}:
        raise SyncError('invalid Ports pending record')
    before = owned_files(transaction['old'], allowed)
    after = owned_files(transaction['new'], allowed)
    permitted = transaction['allowed']
    if (set(after) != set(allowed) or old_files not in (before, after) or
            not isinstance(permitted, dict) or set(permitted) != set(allowed)):
        raise SyncError('incoherent Ports pending ownership')
    for name, checksums in permitted.items():
        if (not isinstance(checksums, list) or not 1 <= len(checksums) <= 3 or
                any(not isinstance(v, str) or not re.fullmatch(r'[0-9a-f]{64}', v) for v in checksums) or
                after[name] not in checksums or (name in before and before[name] not in checksums)):
            raise SyncError('invalid Ports pending checksums')
    effective = {}
    for name in allowed:
        target = safe_path(root/name)
        if target.exists():
            if not target.is_file():
                raise SyncError('non-file Ports action preserved')
            checksum = digest(target.read_bytes())
            if checksum not in permitted[name]:
                raise SyncError('modified Ports action preserved during recovery')
            effective[name] = checksum
    return effective


def install_features(root):
    root = safe_path(Path(root).absolute())
    state = safe_path(root / 'system/art-book-next-ports')
    state.mkdir(parents=True, exist_ok=True)
    with safe_path(state/'install.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        manifest = safe_path(state/'manifest.json')
        old = json.loads(manifest.read_bytes()) if manifest.exists() else {'files': {}}
        files = {}
        for action, (title, _) in ACTIONS.items():
            name = 'roms/ports/Art Book Next - ' + title + '.sh'
            command = [sys.executable, str(root/'system/retroachievements/ports_actions.py'), '--data-root', str(root), '--action', action]
            files[name] = ('#!/bin/sh\n# Managed Art Book Next independent action.\nexec ' + shlex.join(command) + ' "$@"\n').encode()
        pending = safe_path(state/'pending-install.json')
        ownership = recover_ownership(root, pending, old, files)
        for name in files:
            target = safe_path(root/name)
            if target.exists() and (not target.is_file() or ownership.get(name) != digest(target.read_bytes())):
                raise SyncError('modified or unmanaged action preserved')
        gamelist = safe_path(root/'roms/ports/gamelist.xml')
        parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
        initial_gamelist = gamelist.read_bytes() if gamelist.exists() else None
        tree = ET.fromstring(initial_gamelist, parser=parser) if initial_gamelist is not None else ET.Element('gameList')
        if tree.tag != 'gameList': raise SyncError('invalid Ports gamelist')
        # Never overwrite an existing game, even a previously owned entry: native
        # scraping and manual metadata edits remain authoritative. Only append.
        paths = {g.findtext('path') for g in tree.findall('game')}
        for action, (title, description) in ACTIONS.items():
            filename = 'Art Book Next - ' + title + '.sh'
            if any(p in paths for p in ('./'+filename, filename, str(root/'roms/ports'/filename))): continue
            game = ET.SubElement(tree, 'game')
            for tag, value in [('path', './'+filename), ('name', title), ('desc', description), ('developer', 'Art Book Next'), ('genre', 'Utilities')]:
                ET.SubElement(game, tag).text = value
        installer = load(Path(__file__).resolve().parent/'install.py', '_ports_ra_install')
        installer.install(root)
        here = Path(__file__).resolve().parent
        candidates = (here.parent/'system-playtime/install.py', here/'system-playtime/install.py', root/'system/art-book-next-playtime/install.py')
        source = next((path for path in candidates if path.is_file()), candidates[-1])
        load(source, '_ports_playtime_install').install(root, enable=False)
        checksums = {n: digest(d) for n, d in files.items()}
        # Persist provenance before publishing even the first action. A retry can
        # authorize only recorded pre-install, recovered-current, or target bytes.
        permitted = {n: sorted({v for v in (old['files'].get(n), ownership.get(n), checksums[n]) if v}) for n in files}
        durable_write(pending, json.dumps({'old': old['files'], 'new': checksums, 'allowed': permitted}, sort_keys=True).encode())
        for name, data in files.items():
            durable_write(root/name, data)
            (root/name).chmod(0o755)
        if (gamelist.read_bytes() if gamelist.exists() else None) != initial_gamelist:
            raise SyncError('Ports metadata changed during installation; retry safely')
        durable_write(gamelist, ET.tostring(tree, encoding='utf-8', xml_declaration=True))
        durable_write(manifest, json.dumps({'files': checksums}, sort_keys=True).encode())
        pending.unlink()
        sync_directory(state)


def apply(root, action):
    root = safe_path(Path(root).absolute())
    if action == 'install':
        # Keep the installed entry useful after a theme update: prefer the selected
        # local source, then use this self-contained copy when no theme is present.
        from ports_setup import find_source
        source = find_source(root)
        candidate = safe_path(source/'ports_actions.py') if source else None
        if candidate is not None and candidate.is_file() and candidate != Path(__file__).absolute():
            return subprocess.run([sys.executable, str(candidate), '--data-root', str(root), '--action', 'install', '--apply'], timeout=150).returncode
        install_features(root)
        return 0
    if action.startswith(('enable-', 'disable-')):
        feature = action.split('-', 1)[1]
        folder = 'retroachievements' if feature == 'achievements' else 'art-book-next-playtime'
        state = safe_path(root/'system'/folder)
        if not safe_path(state/'install-manifest.json').is_file(): raise SyncError('install features first')
        marker = safe_path(state/'auto-disabled')
        if action == 'enable-achievements' and not safe_path(state/'config.json').exists():
            from configure import configure
            configure(root)
        if action.startswith('disable-'):
            atomic_write(marker, b'Automatic sync disabled by Ports action.\n')
        elif marker.exists():
            marker.unlink()
        return 0
    if action == 'refresh-playtime':
        return subprocess.run([sys.executable, str(root/'system/art-book-next-playtime/auto_refresh.py'), '--data-root', str(root), '--refresh-all'], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=150).returncode
    if action == 'refresh-achievements':
        # Configure only on explicit refresh, never require credentials to install.
        config = safe_path(root/'system/retroachievements/config.json')
        if not config.exists():
            from configure import configure
            configure(root)
        return subprocess.call([sys.executable, str(root/'system/retroachievements/launcher.py'), '--data-root', str(root)])
    raise ValueError('unknown action')


class ActionScreen:
    def __init__(self, root, action):
        self.root, self.action = root, action
        self.child = None
        self.result = None
        self.open_refresh = False

    def handle_event(self, ev):
        key = ctypes.c_int32.from_buffer(ev, 20).value if ev.type == 0x300 else None
        if self.child is not None or self.result is not None: return
        if not (ev.type == 0x651 and ev.padding[12] == 0 or key == 13): return
        if self.action == 'refresh-achievements':
            self.open_refresh = True
            from progress_ui import load_sdl, event
            quit_event = event(0x100)
            load_sdl().SDL_PushEvent(ctypes.byref(quit_event))
            return
        self.child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--data-root', str(self.root), '--action', self.action, '--apply'], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def automatic_status(self, folder, label):
        """Read installation/opt-out state only; never infer worker activity."""
        import stat
        try:
            state = safe_path(Path(self.root) / 'system' / folder)
            manifest = safe_path(state / 'install-manifest.json')
            marker = safe_path(state / 'auto-disabled')
            try:
                installed = stat.S_ISREG(manifest.stat().st_mode)
            except FileNotFoundError:
                installed = False
            if not installed:
                return '[ ] ' + label + ' sync: Not installed'
            try:
                marker.stat()
            except FileNotFoundError:
                return '[x] ' + label + ' sync: Enabled'
            return '[ ] ' + label + ' sync: Disabled'
        except (OSError, ValueError, SyncError):
            return '[?] ' + label + ' sync: Unavailable'

    def layout(self):
        from progress_ui import wrap, text_width
        if self.child is not None and self.child.poll() is not None:
            self.result = self.child.returncode
            self.child = None
        lines = [
            self.automatic_status('retroachievements', 'Achievements'),
            self.automatic_status('art-book-next-playtime', 'Playtime'),
            'Automatic settings, not running status.',
            ACTIONS[self.action][1],
        ]
        if self.child is not None: lines += ['Working locally. Please wait.']
        elif self.result is not None:
            lines += ['Complete.' if self.result == 0 else 'Action refused; check local files / settings.']
            if self.result == 0 and self.action == 'install': lines += ['Use native Update Gamelists to see entries.', 'No sync started. Existing settings preserved.']
            elif self.result == 0 and self.action == 'refresh-playtime': lines += ['Reload the theme to display saved totals.']
            elif self.result == 0 and self.action.startswith('disable-'): lines += ['Automatic workers stop at a safe boundary.', 'Saved data retained. Manual refresh available.']
        else:
            lines += ['A / Enter: Confirm']
        lines += ['B / Back / Esc: Exit']
        # SDL draws 30px atlas cells. At .85 scale, 28px leading leaves
        # breathing room without truncating any description or result message.
        scale = .85
        wrapped = [part for text in lines
                   for part in wrap(text, 576 / scale, lines=len(text.split()) + 1)]
        title = ACTIONS[self.action][0].upper()
        # Keep the title clear of the renderer's decorative bars at x=488.
        title_scale = min(scale, 448 / text_width(title))
        return [(32, 32, title, title_scale)] + [
            (32, 80 + i * 28, text, scale) for i, text in enumerate(wrapped)]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, default=Path('/userdata'))
    parser.add_argument('--action', choices=ACTIONS, default='install')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--frames', type=int)
    parser.add_argument('--windowed', action='store_true')
    parser.add_argument('--screenshot', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.apply: return apply(args.data_root, args.action)
        from progress_ui import run_ui
        screen = ActionScreen(args.data_root, args.action)
        result = run_ui(None, screen=screen, data_root=args.data_root, frames=args.frames, fullscreen=not args.windowed, screenshot=args.screenshot)
        if screen.child is not None: screen.child.wait(timeout=180)
        if screen.open_refresh: return apply(args.data_root, args.action)
        return result or 0
    except (OSError, ValueError, SyncError, RuntimeError, ET.ParseError, subprocess.TimeoutExpired):
        print('Action refused: check installed helpers, saved settings and modified or unsafe paths.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

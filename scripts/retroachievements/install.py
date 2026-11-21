#!/usr/bin/env python3
"""Install only RA-owned files; never edit custom.sh or unrelated services."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import shlex
import sys
from sync import SyncError, atomic_write, safe_path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def install(root, uninstall=False, ports_menu=False):
    state = safe_path(root / 'system/retroachievements')
    state.mkdir(parents=True, exist_ok=True)
    with safe_path(state / 'launcher.lock').open('a') as launching:
        fcntl.flock(launching, fcntl.LOCK_EX)
        marker = safe_path(state / 'launcher-process.json')
        if marker.exists():
            from launcher import process_identity
            previous = json.loads(marker.read_text())
            identity = process_identity(previous.get('pid', 0))
            if identity and identity == previous.get('start_ticks'):
                raise SyncError('stop launched worker before install/uninstall')
        with safe_path(state / 'sync.lock').open('a') as lock:
            try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise SyncError('stop active worker before install/uninstall') from None
            install_files(root, uninstall, ports_menu)


def install_files(root, uninstall=False, ports_menu=False):
    root = safe_path(root)
    state = safe_path(root / 'system/retroachievements')
    manifest = safe_path(state / 'install-manifest.json')
    source = Path(__file__).resolve().parent
    q = shlex.quote
    command = f"python3 {q(str(state / 'sync.py'))} --config {q(str(state / 'config.json'))} --data-root {q(str(root))}"
    # Background workers must not retain the launch caller's capture pipes.
    # sync.py writes bounded, sanitized status.log diagnostics independently.
    files = {
        'system/retroachievements/sync.py': (source / 'sync.py').read_bytes(),
        'system/retroachievements/configure.py': (source / 'configure.py').read_bytes(),
        'system/scripts/ra-progress-sync.sh': (
            '#!/bin/sh\n# Managed by RA extras installer.\n'
            'case "$1" in\n  gameStop)\n'
            f'    {command} --automatic --watch --system "$2" --rom "$5" --force </dev/null >/dev/null 2>&1 &\n'
            '    ;;\nesac\n').encode(),
        'system/services/ra_progress_sync': (
            '#!/bin/sh\n# Managed by RA extras installer; exits when durable queue drains.\n'
            'case "$1" in\n  start)\n'
            f'    {command} --automatic --watch </dev/null >/dev/null 2>&1 &\n'
            f'    ;;\n  stop) {command} --stop ;;\nesac\n').encode(),
    }
    example = safe_path(state / 'config.example.json')
    mapping = safe_path(state / 'mapping.json')
    example_content = (source / 'config.example.json').read_bytes()
    for target in (example, mapping, manifest):
        if target.exists() and not target.is_file():
            raise SyncError('expected regular installed file')
    manifest_before = manifest.read_bytes() if manifest.exists() else None
    old = json.loads(manifest_before) if manifest_before is not None else {}
    port = 'roms/ports/Refresh RetroAchievements Progress.sh'
    # Keep opt-in on normal upgrades; do not touch an unrelated Ports gamelist.
    if ports_menu or port in old:
        for filename in ('launcher.py', 'progress_ui.py', 'ui_palette.py'):
            files['system/retroachievements/' + filename] = (source / filename).read_bytes()
        assets = source / 'ui-assets'
        if assets.exists():
            for asset in sorted(assets.iterdir()):
                if asset.is_file():
                    files['system/retroachievements/ui-assets/' + asset.name] = safe_path(asset).read_bytes()
        files[port] = (
            '#!/bin/sh\n# Managed RA progress screen; closing it leaves sync running.\n'
            f'exec python3 {q(str(state / "launcher.py"))} --data-root {q(str(root))}\n'
        ).encode()
    for filename in ('install.py', 'ports_actions.py', 'ports_setup.py', 'launcher.py', 'progress_ui.py', 'ui_palette.py'):
        files['system/retroachievements/' + filename] = (source / filename).read_bytes()
    for asset in sorted((source / 'ui-assets').iterdir()):
        if asset.is_file():
            files['system/retroachievements/ui-assets/' + asset.name] = safe_path(asset).read_bytes()
    # Fresh install is inactive. Upgrades preserve the previous active state.
    disabled = safe_path(state / 'auto-disabled')
    if not old and not uninstall and not disabled.exists():
        atomic_write(disabled, b'Automatic sync not enabled.\n')
    # Preflight every target before writing anything. Exact known allowlist only.
    legacy = 'system/services/ra-progress-sync'
    targets = [*files, legacy]
    for name in targets:
        target = safe_path(root / name)
        if target.exists() and not target.is_file():
            raise SyncError('expected regular installed file')
        if target.exists() and (name not in old or digest(target.read_bytes()) != old[name]):
            raise SyncError('refusing unmanaged or locally changed installed file')
    if uninstall:
        for name in targets:
            target = root / name
            if name in old and target.exists(): target.unlink()
        if manifest.exists(): manifest.unlink()
        print('Removed owned helper/hooks; config, examples, cache and extras retained.')
        return
    before = {name: ((root / name).read_bytes(), (root / name).stat().st_mode & 0o777) if (root / name).exists() else None for name in targets}
    new_examples = [path for path in (example, mapping) if not path.exists()]
    try:
        for name, data in files.items():
            target = root / name
            atomic_write(target, data); target.chmod(0o755)
        if (root / legacy).exists(): (root / legacy).unlink()
        atomic_write(manifest, json.dumps({name: digest(data) for name, data in files.items()}, indent=2).encode())
        if not example.exists(): atomic_write(example, example_content)
        if not mapping.exists(): atomic_write(mapping, b'[]\n')
    except (OSError, SyncError):
        for path in new_examples:
            if path.exists(): path.unlink()
        for name, data in before.items():
            target = root / name
            if data is None:
                if target.exists(): target.unlink()
            else:
                atomic_write(target, data[0]); target.chmod(data[1])
        if manifest_before is not None: atomic_write(manifest, manifest_before)
        elif manifest.exists(): manifest.unlink()
        raise
    print('Installed RA helper and gameStop hook; startup service is NOT enabled.')
    if port in files:
        print('Installed Ports > Refresh RetroAchievements Progress. Update gamelists/restart ES to discover it.')
    if not (state / 'config.json').exists():
        print('First-time setup: python3', state / 'configure.py', '--data-root', root)
    else:
        print('Existing private configuration preserved; do not rerun configure.')
    print('Manual sync:', command)
    print('Optional startup service queues mapped IDs with cache TTL; gameStop is independent and does not require it for the exit fix.')
    print('No credential prompts: uses Batocera RA login. Optionally: batocera-services enable ra_progress_sync')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', default='/userdata')
    parser.add_argument('--uninstall', action='store_true')
    parser.add_argument('--ports-menu', action='store_true', help='install optional controller-friendly sync launcher under Ports')
    args = parser.parse_args()
    try:
        install(Path(args.data_root).absolute(), args.uninstall, args.ports_menu)
        return 0
    except (OSError, ValueError, SyncError):
        print('Install refused: stop any active sync worker first; otherwise check unsafe paths or unmanaged/modified files. No unrelated service is modified.', file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.exit(main())

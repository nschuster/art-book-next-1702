#!/usr/bin/env python3
"""Install only RA-owned files; never edit custom.sh or unrelated services."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import sys
from sync import SyncError, atomic_write, safe_path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def install(root, uninstall=False):
    root = safe_path(root)
    state = safe_path(root / 'system/retroachievements')
    manifest = safe_path(state / 'install-manifest.json')
    source = Path(__file__).resolve().parent
    q = shlex.quote
    command = f"python3 {q(str(state / 'sync.py'))} --config {q(str(state / 'config.json'))} --data-root {q(str(root))}"
    files = {
        'system/retroachievements/sync.py': (source / 'sync.py').read_bytes(),
        'system/retroachievements/configure.py': (source / 'configure.py').read_bytes(),
        'system/scripts/ra-progress-sync.sh': (
            '#!/bin/sh\n# Managed by RA extras installer.\n'
            'case "$1" in\n  gameStop)\n'
            f'    {command} --system "$2" --rom "$5" --force </dev/null >/dev/null 2>&1 &\n'
            '    ;;\nesac\n').encode(),
        'system/services/ra-progress-sync': (
            '#!/bin/sh\n# Managed by RA extras installer; one-shot, not a daemon.\n'
            'case "$1" in\n  start)\n'
            f'    {command} </dev/null >/dev/null 2>&1 &\n'
            '    ;;\n  stop) : ;;\nesac\n').encode(),
    }
    example = safe_path(state / 'config.example.json')
    mapping = safe_path(state / 'mapping.json')
    example_content = (source / 'config.example.json').read_bytes()
    for target in (example, mapping, manifest):
        if target.exists() and not target.is_file():
            raise SyncError('expected regular installed file')
    old = json.loads(manifest.read_text()) if manifest.exists() else {}
    # Preflight every target before writing anything. Exact known allowlist only.
    for name in files:
        target = safe_path(root / name)
        if target.exists() and (name not in old or digest(target.read_bytes()) != old[name]):
            raise SyncError('refusing unmanaged or locally changed installed file')
    if uninstall:
        for name in files:
            target = root / name
            if name in old and target.exists(): target.unlink()
        if manifest.exists(): manifest.unlink()
        print('Removed owned helper/hooks; config, examples, cache and extras retained.')
        return
    before = {name: ((root / name).read_bytes(), (root / name).stat().st_mode & 0o777) if (root / name).exists() else None for name in files}
    new_examples = [path for path in (example, mapping) if not path.exists()]
    try:
        for name, data in files.items():
            target = root / name
            atomic_write(target, data); target.chmod(0o755)
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
        if old: atomic_write(manifest, json.dumps(old).encode())
        elif manifest.exists(): manifest.unlink()
        raise
    print('Installed RA helper and gameStop hook; startup service is NOT enabled.')
    print('Run: python3', state / 'configure.py', '--data-root', root)
    print('Then run:', command)
    print('No credential prompts: uses Batocera RA login. Optionally: batocera-services enable ra-progress-sync')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', default='/userdata')
    parser.add_argument('--uninstall', action='store_true')
    args = parser.parse_args()
    try:
        install(Path(args.data_root).absolute(), args.uninstall)
        return 0
    except (OSError, ValueError, SyncError):
        print('Install refused: unsafe path or existing unmanaged/modified file. No unrelated service is modified.', file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.exit(main())

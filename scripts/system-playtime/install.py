#!/usr/bin/env python3
"""Opt-in local playtime hook installation; never changes RA or frontend settings."""
import argparse
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shlex
import tempfile

STATE = 'system/art-book-next-playtime'
HOOK = 'system/scripts/art-book-playtime.sh'
FILES = tuple(STATE + '/' + name for name in ('auto_refresh.py', 'refresh.py', 'playtime_discovery.py', 'install.py')) + (HOOK,)


def safe_path(path):
    path = Path(os.path.abspath(path))
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError('symlink path refused')
    return path


def digest(data):
    return hashlib.sha256(data).hexdigest()


MANIFEST = STATE + '/install-manifest.json'
PENDING = STATE + '/install-pending.json'
MAX_JOURNAL = 8 * 1024 * 1024


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def remove(path):
    if path.exists():
        path.unlink()
        sync_directory(path.parent)


def capture(path):
    return [base64.b64encode(path.read_bytes()).decode('ascii'), path.stat().st_mode & 0o777] if path.exists() else None


def decode(entry):
    if entry is None:
        return None
    if not isinstance(entry, list) or len(entry) != 2 or type(entry[1]) is not int or not 0 <= entry[1] <= 0o777:
        raise ValueError('invalid pending entry')
    return base64.b64decode(entry[0], validate=True)


def recover(root, pending):
    if not pending.exists():
        return
    if pending.stat().st_size > MAX_JOURNAL:
        raise ValueError('oversized pending transaction')
    txn = json.loads(pending.read_bytes())
    names = (*FILES, MANIFEST)
    if not isinstance(txn, dict) or set(txn) != {'old', 'new'}:
        raise ValueError('invalid pending transaction')
    decoded = {}
    for side in ('old', 'new'):
        entries = txn[side]
        if not isinstance(entries, dict) or set(entries) != set(names):
            raise ValueError('invalid pending paths')
        decoded[side] = {name: decode(entries[name]) for name in names}
        raw_manifest = decoded[side][MANIFEST]
        ownership = json.loads(raw_manifest) if raw_manifest is not None else {}
        if not isinstance(ownership, dict) or set(ownership) - set(FILES):
            raise ValueError('invalid pending manifest')
        for name in FILES:
            data = decoded[side][name]
            if data is not None and ownership.get(name) != digest(data):
                raise ValueError('pending content does not match manifest')
    # Validate every path before restoring any: never clobber a third-party edit.
    paths = {name: safe_path(root / name) for name in names}
    for name, path in paths.items():
        if path.exists() and not path.is_file():
            raise ValueError('expected regular file')
        data = path.read_bytes() if path.exists() else None
        if not any(data == decoded[side][name] for side in ('old', 'new')):
            raise ValueError('modified pending file; preserved')
    # Always roll back. This remains restartable even if recovery itself dies.
    for name, path in paths.items():
        data = decoded['old'][name]
        if data is None:
            remove(path)
        else:
            atomic_write(path, data, txn['old'][name][1])
    remove(pending)


def atomic_write(path, data, mode=0o644):
    path = safe_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.playtime-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), mode)
        os.replace(name, path)
        sync_directory(path.parent)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def install(root, uninstall=False, enable=True):
    root = safe_path(root)
    # Lock the root directory itself: no unmanaged lock file is created.
    root.mkdir(parents=True, exist_ok=True)
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        fresh = not safe_path(root / MANIFEST).exists()
        disabled = safe_path(root / STATE / 'auto-disabled')
        if fresh and not enable and not uninstall:
            atomic_write(disabled, b'Automatic sync not enabled.\n')
        _install(root, uninstall)
    finally:
        os.close(fd)


def _install(root, uninstall):
    pending = safe_path(root / PENDING)
    if pending.exists() and not pending.is_file():
        raise ValueError('expected regular pending file')
    recover(root, pending)
    manifest = safe_path(root / MANIFEST)
    targets = {name: safe_path(root / name) for name in FILES}
    for path in (*targets.values(), manifest):
        if path.exists() and not path.is_file():
            raise ValueError('expected regular file')
    old = json.loads(manifest.read_bytes()) if manifest.exists() else {}
    if not isinstance(old, dict) or set(old) - set(FILES):
        raise ValueError('invalid ownership manifest')
    for name, path in targets.items():
        if path.exists() and old.get(name) != digest(path.read_bytes()):
            raise ValueError('unmanaged or modified file; preserved')
    files = {}
    if not uninstall:
        source = Path(__file__).resolve().parent
        for name in FILES[:-1]:
            filename = Path(name).name
            origin = source / filename
            if filename == 'playtime_discovery.py' and not origin.exists():
                origin = source.parent / filename
            files[name] = safe_path(origin).read_bytes()
        command = 'python3 ' + shlex.quote(str(root / STATE / 'auto_refresh.py')) + ' --data-root ' + shlex.quote(str(root))
        files[HOOK] = ('#!/bin/sh\n# Independently managed optional saved-playtime hook.\n'
                       'case "$1" in\n  gameStop)\n    since=$(python3 -c "import time; print(time.time())") || exit 0\n'
                       f'    {command} --system "$2" --rom "$5" --since "$since" </dev/null >/dev/null 2>&1 &\n'
                       '    ;;\nesac\n').encode()
    paths = {**targets, MANIFEST: manifest}
    if not uninstall:
        files[MANIFEST] = (json.dumps({name: digest(data) for name, data in files.items()}, indent=2) + '\n').encode()
    txn = {
        'old': {name: capture(path) for name, path in paths.items()},
        'new': {name: [base64.b64encode(files[name]).decode('ascii'), 0o755 if name == HOOK else 0o644]
                if name in files else None for name in paths},
    }
    journal = json.dumps(txn).encode()
    if len(journal) > MAX_JOURNAL:
        raise ValueError('oversized pending transaction')
    try:
        # Persist before the first replacement, including on a fresh install.
        atomic_write(pending, journal, 0o600)
        for name, path in paths.items():
            if uninstall:
                remove(path)
            else:
                atomic_write(path, files[name], txn['new'][name][1])
        remove(pending)
    except (OSError, ValueError):
        recover(root, pending)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, default=Path('/userdata'))
    parser.add_argument('--uninstall', action='store_true')
    args = parser.parse_args(argv)
    try:
        install(args.data_root, args.uninstall)
    except (OSError, ValueError):
        print('Playtime installation refused: unsafe paths or modified files; files preserved.')
        return 2
    print('Playtime hook removed; saved totals preserved.' if args.uninstall else 'Background playtime updates enabled; reload theme to display saved totals.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Publish exact saved-gamelist totals. Independent of RetroAchievements.

Explicit mappings use native system.name, not display names or theme aliases.
Outputs reload with the theme; they do not track live ES visibility filters.
"""
import argparse
import hashlib
import fcntl
import json
import os
from pathlib import Path
import re
import tempfile
import xml.etree.ElementTree as ET

DEFAULT_OUTPUT = '/userdata/system/configs/art-book-next-system-playtime'

def digest(data):
    return hashlib.sha256(data).hexdigest()

def atomic(path, data):
    fd, temp = tempfile.mkstemp(prefix='.hours-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

def total(path):
    root = ET.parse(path).getroot()
    if root.tag != 'gameList':
        raise ValueError('invalid gamelist root')
    seconds = 0
    for game in root.findall('game'):
        value = (game.findtext('gametime') or '0').strip()
        if not re.fullmatch(r'[0-9]+', value):
            raise ValueError('invalid gametime; output not refreshed')
        seconds += int(value)
    return f'{seconds // 3600}h {(seconds // 60) % 60}m'

def refresh(mappings, output, *, total_provider=None):
    """Publish under the ownership lock; optional provider reads saved overlays.

    The provider runs inside the lock, so concurrent workers cannot publish an
    older snapshot calculated before waiting for another writer.
    """
    output = Path(output).absolute()
    if output.resolve() != output:
        raise ValueError('symlinked output path refused')
    output.mkdir(parents=True, exist_ok=True)
    fd = os.open(output / '.refresh.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _refresh(mappings, output, total_provider)


def recover_commit(output, journal, owned):
    """Accept only old/new hashes from a write-ahead record after interruption."""
    transaction = output / '.pending.json'
    if transaction.is_symlink():
        raise ValueError('symlink transaction refused')
    if not transaction.exists():
        return owned
    record = json.loads(transaction.read_text())
    if not isinstance(record, dict) or set(record) != {'before', 'after'}:
        raise ValueError('invalid pending transaction')
    before, after = record['before'], record['after']
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise ValueError('ownership transaction mismatch')
    if set(owned) - set(after) or any(owned.get(name) not in (before.get(name), checksum) for name, checksum in after.items()):
        raise ValueError('ownership transaction mismatch')
    if set(before) - set(after):
        raise ValueError('invalid pending removal')
    recovered = dict(owned)
    for name, checksum in after.items():
        if not re.fullmatch(r'[A-Za-z0-9_-]+', name) or not isinstance(checksum, str) or not re.fullmatch(r'[0-9a-f]{64}', checksum):
            raise ValueError('invalid pending output')
        if before.get(name) == checksum:
            continue
        path = output / (name + '.xml')
        if path.is_symlink():
            raise ValueError('symlink pending output refused')
        current = digest(path.read_bytes()) if path.exists() else None
        if current not in (before.get(name), checksum):
            raise ValueError('modified pending output refused')
        if current is None:
            recovered.pop(name, None)
        else:
            recovered[name] = current
    atomic(journal, (json.dumps(recovered, sort_keys=True) + '\n').encode())
    transaction.unlink()
    return recovered


def _refresh(mappings, output, total_provider=None):
    # Read and validate all inputs before publishing any output.
    pending = {}
    for mapping in mappings:
        name, separator, source = mapping.partition('=')
        if not separator or not re.fullmatch(r'[A-Za-z0-9_-]+', name) or name in pending:
            raise ValueError('invalid or duplicate system mapping')
        theme = ET.Element('theme')
        view = ET.SubElement(theme, 'view', name='system')
        text = ET.SubElement(view, 'text', name='system-playtime', extra='true')
        ET.SubElement(text, 'text').text = total_provider(name, source) if total_provider else total(source)
        pending[name] = ET.tostring(theme, encoding='utf-8', xml_declaration=True) + b'\n'
    if output.is_symlink() or any(parent.is_symlink() for parent in output.parents):
        raise ValueError('symlink output directory refused')
    output.mkdir(parents=True, exist_ok=True)
    journal = output / '.owned.json'
    if journal.is_symlink():
        raise ValueError('symlink ownership file refused')
    owned = json.loads(journal.read_text()) if journal.exists() else {}
    if not isinstance(owned, dict):
        raise ValueError('invalid ownership journal')
    owned = recover_commit(output, journal, owned)
    for name in pending:
        path = output / (name + '.xml')
        if path.is_symlink() or (path.exists() and owned.get(name) != digest(path.read_bytes())):
            raise ValueError('unmanaged or modified output refused')
    after = {**owned, **{name: digest(data) for name, data in pending.items()}}
    transaction = output / '.pending.json'
    atomic(transaction, (json.dumps({'before': owned, 'after': after}, sort_keys=True) + '\n').encode())
    for name, data in pending.items():
        atomic(output / (name + '.xml'), data)
    atomic(journal, (json.dumps(after, sort_keys=True) + '\n').encode())
    transaction.unlink()
    return len(pending)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--system', action='append', required=True, metavar='NAME=GAMELIST')
    parser.add_argument('--output', type=Path, default=Path(DEFAULT_OUTPUT))
    args = parser.parse_args()
    try:
        count = refresh(args.system, args.output)
    except (OSError, ValueError, ET.ParseError):
        # No raw filesystem paths, gamelist contents or personal metadata in logs.
        parser.exit(1, 'System playtime refresh refused: invalid input or unsafe output. Existing totals may be stale.\n')
    print(f'Refreshed {count} saved system total(s). Reload the theme to display them.')

if __name__ == '__main__':
    main()

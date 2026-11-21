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

def refresh(mappings, output):
    output = Path(output).absolute()
    if output.resolve() != output:
        raise ValueError('symlinked output path refused')
    output.mkdir(parents=True, exist_ok=True)
    fd = os.open(output / '.refresh.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _refresh(mappings, output)


def _refresh(mappings, output):
    # Read and validate all inputs before publishing any output.
    pending = {}
    for mapping in mappings:
        name, separator, source = mapping.partition('=')
        if not separator or not re.fullmatch(r'[A-Za-z0-9_-]+', name) or name in pending:
            raise ValueError('invalid or duplicate system mapping')
        theme = ET.Element('theme')
        view = ET.SubElement(theme, 'view', name='system')
        text = ET.SubElement(view, 'text', name='system-playtime', extra='true')
        ET.SubElement(text, 'text').text = total(source)
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
    for name in pending:
        path = output / (name + '.xml')
        if path.is_symlink() or (path.exists() and owned.get(name) != digest(path.read_bytes())):
            raise ValueError('unmanaged or modified output refused')
    for name, data in pending.items():
        atomic(output / (name + '.xml'), data)
        owned[name] = digest(data)
    atomic(journal, (json.dumps(owned, sort_keys=True) + '\n').encode())
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

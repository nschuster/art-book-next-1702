#!/usr/bin/env python3
"""Create a private RA config interactively; never overwrite an existing one."""
import argparse
import getpass
import json
import os
from pathlib import Path
import re
import sys


def configure(root, username, api_key, mode):
    root = Path(root).absolute()
    if not username.strip() or not api_key.strip() or mode not in ('hardcore', 'softcore'):
        raise ValueError('Nonempty credentials and valid mode required')
    state = root / 'system/retroachievements'
    if any(p.is_symlink() for p in (state, *state.parents)):
        raise ValueError('Symlink state paths are not supported')
    state.mkdir(parents=True, exist_ok=True)
    config = state / 'config.json'
    template = json.loads(Path(__file__).with_name('config.example.json').read_text())
    template.update(username=username.strip(), api_key=api_key.strip(), mode=mode,
                    systems=sorted(p.parent.name for p in (root / 'roms').glob('*/gamelist.xml')
                                   if re.fullmatch(r'[A-Za-z0-9_-]+', p.parent.name)))
    # Empty template follows current helper geometry and the active theme font.
    # Exclusive creation prevents accidental replacement (including symlink targets).
    fd = os.open(config, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(template, stream, indent=2)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    except BaseException:
        config.unlink()
        raise
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', default='/userdata')
    parser.add_argument('--mode', choices=('hardcore', 'softcore'), default='hardcore')
    args = parser.parse_args()
    try:
        username = input('RetroAchievements username: ')
        key = getpass.getpass('RA web API key (hidden): ')
        path = configure(args.data_root, username, key, args.mode)
        print('Created private config. Systems discovered from existing gamelists.')
        print('Next run sync.py using --config', path)
        return 0
    except (OSError, ValueError, EOFError, KeyboardInterrupt):
        print('Setup refused or cancelled; existing config was not overwritten.', file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.exit(main())

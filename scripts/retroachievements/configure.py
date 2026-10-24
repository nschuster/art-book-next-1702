#!/usr/bin/env python3
"""Configure automatic Batocera RA integration; never overwrite existing config."""
import argparse
import getpass
import json
import os
from pathlib import Path
import re
import sys


def configure(root, username=None, api_key=None, mode=None):
    root = Path(root).absolute()
    manual = username is not None or api_key is not None
    if manual and (not username or not api_key or not username.strip() or not api_key.strip() or mode not in ('hardcore', 'softcore')):
        raise ValueError('Nonempty credentials and valid mode required')
    state = root / 'system/retroachievements'
    if any(p.is_symlink() for p in (state, *state.parents)):
        raise ValueError('Symlink state paths are not supported')
    state.mkdir(parents=True, exist_ok=True)
    config = state / 'config.json'
    # Installed examples may predate token support. Never copy their credentials.
    template = {'backend': 'batocera', 'mapping_file': 'mapping.json',
                'cache_ttl': 900, 'min_interval': 1.0, 'retries': 2,
                'backoff': 2.0, 'template': {}}
    if manual:
        template.update(backend='webapi', username=username.strip(), api_key=api_key.strip(), mode=mode)
    template.update(systems=sorted(p.parent.name for p in (root / 'roms').glob('*/gamelist.xml')
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
    parser.add_argument('--backend', choices=('batocera', 'webapi'), default='batocera')
    parser.add_argument('--mode', choices=('hardcore', 'softcore'), default='hardcore')
    args = parser.parse_args()
    try:
        if args.backend == 'webapi':
            username = input('RetroAchievements username: ')
            key = getpass.getpass('RA web API key (hidden): ')
            path = configure(args.data_root, username, key, args.mode)
        else:
            path = configure(args.data_root)
        print('Created private config. Systems discovered from existing gamelists.')
        print('Next run sync.py using --config', path)
        return 0
    except (OSError, ValueError, EOFError, KeyboardInterrupt):
        print('Setup refused or cancelled; existing config was not overwritten.', file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.exit(main())

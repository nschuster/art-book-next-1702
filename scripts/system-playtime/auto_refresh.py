#!/usr/bin/env python3
"""Publish saved system totals after a matching post-game save, never reload ES.

Recovery parentHash is the base gamelist's byte size, not a content digest.
The gameStop caller must spawn this worker and return without waiting.
"""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import re
import time
import xml.etree.ElementTree as ET


def load_sibling(name):
    here = Path(__file__).resolve().parent
    path = here / (name + '.py')
    if not path.is_file() and name == 'playtime_discovery':
        path = here.parent / (name + '.py')
    spec = importlib.util.spec_from_file_location('_system_playtime_' + name, path)
    if spec is None or spec.loader is None:
        raise ValueError('missing worker module')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


publisher = load_sibling('refresh')


class NotReady(ValueError):
    """A save is missing, ambiguous in time, or concurrently being written."""


def identity(value, rom_root):
    if not value or not value.strip() or '\x00' in value:
        raise ValueError('missing ROM identity')
    root = Path(rom_root).resolve()
    path = Path(value)
    path = (path if path.is_absolute() else root / path).resolve()
    try:
        relative = path.relative_to(root)
    except ValueError:
        raise ValueError('ROM outside configured root') from None
    if relative == Path('.'):
        raise ValueError('invalid ROM identity')
    return str(relative)


def read_xml(path):
    before = path.stat()
    data = path.read_bytes()
    after = path.stat()
    signature = lambda st: (st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
    if signature(before) != signature(after) or len(data) != after.st_size:
        raise NotReady('save changed while reading')
    tree = ET.fromstring(data)
    if tree.tag != 'gameList':
        raise ValueError('invalid gamelist root')
    return tree, len(data), after.st_mtime_ns, signature(after)


def records(tree, rom_root):
    result = {}
    for game in tree.findall('game'):
        if len(game.findall('path')) != 1 or len(game.findall('gametime')) > 1:
            raise ValueError('ambiguous game record')
        key = identity(game.findtext('path'), rom_root)
        value = (game.findtext('gametime') or '0').strip()
        if not re.fullmatch(r'[0-9]+', value) or key in result:
            raise ValueError('invalid gametime or duplicate ROM')
        result[key] = int(value)
    return result


def snapshot(detail, recovery, target=None, since=None, initial=None):
    base = Path(detail['gamelist'])
    rom_root = Path(detail['rom_root'])
    tree, size, stamp, signature = read_xml(base)
    games = records(tree, rom_root)
    stamps = {str(base): signature}

    def fresh(path, timestamp, sig):
        # The installed hook captures subsecond time before spawning. Retain
        # conservative handling for callers supplying old second-only stamps.
        return since is not None and (
            (since != math.floor(since) and timestamp >= since * 1_000_000_000) or
            timestamp >= (math.floor(since) + 1) * 1_000_000_000 or
            (timestamp >= since * 1_000_000_000 and initial is not None
             and initial.get(str(path)) != sig))

    ready = target in games and fresh(base, stamp, signature)
    overlays = {}
    files = sorted(recovery.rglob('*.xml')) if recovery.exists() else []
    for path in files:
        tree, _, stamp, signature = read_xml(path)
        stamps[str(path)] = signature
        parent = tree.get('parentHash', '')
        if not re.fullmatch(r'[0-9]+', parent):
            raise ValueError('invalid recovery parentHash')
        if int(parent) != size:
            continue
        saved = records(tree, rom_root)
        if overlays.keys() & saved.keys():
            raise ValueError('ambiguous duplicate recovery ROM')
        overlays.update(saved)
        if target in saved and fresh(path, stamp, signature):
            ready = True
    games.update(overlays)
    # ES may flush its base and remove recovery while we scan. Never mix them.
    if read_xml(base)[3] != stamps[str(base)]:
        raise NotReady('base changed during recovery scan')
    if files != (sorted(recovery.rglob('*.xml')) if recovery.exists() else []):
        raise NotReady('recovery changed during scan')
    for path in files:
        st = path.stat()
        if (st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns) != stamps[str(path)]:
            raise NotReady('recovery changed during scan')
    seconds = sum(games.values())
    return f'{seconds // 3600}h {(seconds // 60) % 60}m', ready, stamps


def run(data_root, *, system=None, rom=None, since=None, refresh_all=False,
        timeout=120, poll_interval=.25, details=None):
    root = Path(data_root)
    disabled = root / 'system/art-book-next-playtime/auto-disabled'
    if not refresh_all and disabled.exists(): return 0
    if not math.isfinite(timeout) or timeout < 0 or not math.isfinite(poll_interval) or poll_interval <= 0:
        raise ValueError('invalid wait bounds')
    if not refresh_all and (not system or rom is None or since is None or not math.isfinite(since)):
        raise ValueError('system, ROM and since required')
    if refresh_all and any(value is not None for value in (system, rom, since)):
        raise ValueError('manual and automatic modes are exclusive')
    if details is None:
        details = load_sibling('playtime_discovery').discover_details(root)
    selected = details if refresh_all else {system: details[system]} if system in details else {}
    if not selected:
        raise ValueError('no supported system mapping')
    if any(not re.fullmatch(r'[A-Za-z0-9_-]+', name) for name in selected):
        raise ValueError('invalid native system')
    target = None if refresh_all else identity(str(rom), selected[system]['rom_root'])
    recovery = root / 'system/configs/emulationstation/recovery'
    output = root / 'system/configs/art-book-next-system-playtime'
    mappings = [f"{name}={detail['gamelist']}" for name, detail in selected.items()]
    deadline = time.monotonic() + timeout
    initial = None

    def provider(name, source):
        nonlocal initial
        total, ready, stamps = snapshot(selected[name], recovery / name, target, since, initial)
        if not refresh_all and disabled.exists():
            raise NotReady('automatic updates disabled')
        if not refresh_all and not ready:
            if initial is None:
                initial = stamps
            raise NotReady('no unambiguous matching post-game save')
        return total

    while True:
        if not refresh_all and disabled.exists(): return 0
        try:
            return publisher.refresh(mappings, output, total_provider=provider)
        except BlockingIOError:
            pass  # Retry contention, never silently drop an exit event.
        except (NotReady, ET.ParseError, FileNotFoundError):
            if refresh_all:
                raise
        if time.monotonic() >= deadline:
            raise TimeoutError('no fresh saved metadata or output lock before deadline')
        time.sleep(min(poll_interval, max(0, deadline - time.monotonic())))


def record_result(root, result, count=0):
    """Best-effort last-completed status; no paths, names or exception details."""
    try:
        directory = Path(root).absolute() / 'system/configs/art-book-next-system-playtime'
        if directory.resolve() != directory:
            return
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / '.last-result.json'
        if path.is_symlink():
            return
        if path.exists() and json.loads(path.read_text()).get('owner') != 'art-book-next-playtime':
            return
        data = {'owner': 'art-book-next-playtime', 'result': result,
                'systems': count, 'completed_at': time.time()}
        publisher.atomic(path, (json.dumps(data, sort_keys=True) + '\n').encode())
    except (OSError, ValueError, AttributeError):
        pass  # Reporting must never change the refresh outcome or replace unsafe files.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, default=Path('/userdata'))
    parser.add_argument('--system')
    parser.add_argument('--rom')
    parser.add_argument('--since', type=float)
    parser.add_argument('--refresh-all', action='store_true')
    parser.add_argument('--timeout', type=float, default=120)
    parser.add_argument('--poll-interval', type=float, default=.25)
    args = parser.parse_args()
    try:
        count = run(**vars(args))
    except (OSError, ValueError, ET.ParseError):
        record_result(args.data_root, 'not-refreshed')
        parser.exit(1, 'System playtime not refreshed: missing fresh save, invalid input, or unsafe output. Existing totals retained.\n')
    record_result(args.data_root, 'updated', count)
    print(f'Refreshed {count} saved system total(s). Display updates on a later theme reload.')


if __name__ == '__main__':
    main()

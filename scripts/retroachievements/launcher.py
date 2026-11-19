#!/usr/bin/env python3
"""Controller launcher for the optional Ports entry; never handles credentials."""
import argparse
import fcntl
import json
import time
from pathlib import Path
import subprocess
import sys

from sync import SyncError, atomic_write, safe_path


def process_identity(pid):
    """Linux start ticks prevent a reused PID from masquerading as our worker."""
    try:
        text = Path('/proc') .joinpath(str(int(pid)), 'stat').read_text()
        fields = text.rsplit(')', 1)[1].split()
        return None if fields[0] in ('Z', 'X') else fields[19]
    except (OSError, ValueError, TypeError, IndexError):
        return None


def start_or_attach(root, test_api_base=None):
    """Start one detached full refresh, or attach without re-enqueuing work.

    The short launcher lock also protects the gap while the child loads mappings,
    before it takes the existing worker lock. The PID marker is not worker status.
    """
    root = safe_path(Path(root).absolute())
    state = safe_path(root / 'system/retroachievements')
    state.mkdir(parents=True, exist_ok=True)
    with safe_path(state/'launcher.lock').open('a') as launching:
        fcntl.flock(launching, fcntl.LOCK_EX)
        marker = safe_path(state/'launcher-process.json')
        previous = {}
        if marker.exists():
            try:
                previous = json.loads(marker.read_text())
                identity = process_identity(previous['pid'])
                if identity and identity == previous['start_ticks']:
                    return None
            except (ValueError, KeyError, TypeError):
                previous = {}
        owner_run_id = None
        with safe_path(state/'sync.lock').open('a') as held:
            active = False
            try:
                fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                active = True
            progress = safe_path(state/'progress.json')
            if active:
                try:
                    owner = json.loads(progress.read_text())
                    owner_run_id = owner.get('run_id')
                except (OSError, ValueError, AttributeError):
                    pass
                # Unknown/older workers are attach-only. For an identified worker,
                # enqueue a full refresh once: it might currently only have a
                # one-game exit hook queued. Reopening must not reset generations.
                if not owner_run_id or previous.get('owner_run_id') == owner_run_id:
                    return None
            elif progress.exists():
                # No worker owns this file now; discard yesterday's completion.
                progress.unlink()
        command = [sys.executable, str(safe_path(state/'sync.py')),
                   '--config', str(safe_path(state/'config.json')),
                   '--data-root', str(root), '--force', '--watch']
        if test_api_base:
            command.extend(['--test-api-base', test_api_base])
        child = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 start_new_session=True, close_fds=True)
        atomic_write(marker, json.dumps({'pid': child.pid, 'owner_run_id': owner_run_id,
                                        'start_ticks': process_identity(child.pid)}).encode())
        return child


class SyncSession:
    """Read-only UI view, including failures occurring before worker ownership."""
    def __init__(self, root, test_api_base=None):
        self.root = root
        self.state = root / 'system/retroachievements'
        self.test_api_base = test_api_base
        self.child = None

    def start(self):
        self.child = start_or_attach(self.root, self.test_api_base)

    def read_status(self):
        if self.child is not None:
            self.child.poll()  # Reap exits so /proc does not mistake a zombie for a worker.
        try:
            path = safe_path(self.state / 'progress.json')
            with path.open() as source:
                status = json.loads(source.read(65537))
            if not isinstance(status, dict): status = {}
        except (OSError, ValueError):
            status = {}
        # Never probe sync.lock from the polling loop: even a brief successful
        # lock could make a starting worker yield and strand its queue.
        active = bool(process_identity(status.get('pid', 0)))
        if not active:
            try:
                marker = json.loads(safe_path(self.state / 'launcher-process.json').read_text())
                identity = process_identity(marker.get('pid', 0))
                active = bool(identity and identity == marker.get('start_ticks'))
            except (OSError, ValueError, AttributeError):
                pass
        if status.get('state') in ('complete', 'failed', 'stopped', 'disabled'):
            return status
        if active and status:
            return status
        if active:
            return dict(schema=1, updated_at=time.time(), state='scanning',
                        total=0, completed=0, updated=0, cached=0, failed=0,
                        pending=0, attempt=0)
        # This is an in-memory display state, never a write to progress.json.
        result = dict(schema=1, updated_at=time.time(), state='failed',
                      reason='worker_ended_without_result', total=0, completed=0,
                      updated=0, cached=0, failed=0, pending=0, attempt=0)
        for key in ('total', 'completed', 'updated', 'cached', 'failed', 'pending', 'attempt'):
            value = status.get(key)
            if type(value) is int and value >= 0: result[key] = value
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', default='/userdata')
    parser.add_argument('--test-api-base', help='TEST ONLY: explicit loopback fixture server')
    parser.add_argument('--windowed', action='store_true', help='development: do not use fullscreen')
    parser.add_argument('--frames', type=int, help='development: exit UI after this many frames; worker continues')
    parser.add_argument('--screenshot', type=Path, help='development: capture actual SDL frame as BMP')
    args = parser.parse_args()
    if args.frames is not None and args.frames < 1:
        parser.error('--frames must be positive')
    try:
        # Lazy import means worker and ordinary hooks never load SDL.
        from progress_ui import run_ui
        root = safe_path(Path(args.data_root).absolute())
        session = SyncSession(root, args.test_api_base)
        return run_ui(root/'system/retroachievements/progress.json',
                      start_callback=session.start, status_reader=session.read_status,
                      fullscreen=not args.windowed, frames=args.frames,
                      screenshot=args.screenshot) or 0
    except (OSError, ValueError, SyncError, RuntimeError):
        print('Cannot open RA sync screen. Check the installed helper, SDL2 video/controller support and private configuration. No credentials are printed.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

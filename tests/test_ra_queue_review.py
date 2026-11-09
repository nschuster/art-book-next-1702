"""Independent acceptance checks for durable queue edge cases."""
import importlib.util
import json
from pathlib import Path
import pytest
from test_ra_queue import queue_rig

PATH = Path(__file__).resolve().parents[1] / 'scripts/retroachievements/sync.py'
spec = importlib.util.spec_from_file_location('review_ra_sync', PATH)
assert spec is not None and spec.loader is not None
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

@pytest.mark.parametrize('due', [float('nan'), float('inf'), -float('inf')])
def test_queue_rejects_nonfinite_deadlines(tmp_path, due):
    (tmp_path / 'pending.json').write_text(json.dumps({'1': {'generation':'x', 'force':True, 'attempts':1, 'due':due}}))
    with pytest.raises(sync.SyncError):
        with sync.pending_queue(tmp_path):
            pass


def test_startup_does_not_reset_existing_failure_backoff(queue_rig):
    import fcntl
    r = queue_rig
    r.status = 503
    assert r.run('--system', 'snes', '--rom', 'Game1.sfc', '--force').returncode == 1
    before = r.pending()['1']
    with (r.state / 'sync.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        assert r.run().returncode == 0
    after = r.pending()['1']
    assert after == before, 'startup enqueue must preserve an existing forced job and its retry deadline'


def test_watch_stops_after_bounded_attempts_and_keeps_pending(queue_rig):
    r = queue_rig
    cfg_path = r.state / 'config.json'
    cfg = json.loads(cfg_path.read_text())
    cfg['queue_attempts'] = 2
    cfg_path.write_text(json.dumps(cfg))
    r.status = 503
    result = r.run('--watch', '--system', 'snes', '--rom', 'Game1.sfc', '--force')
    assert result.returncode == 1
    assert r.requests == [1, 1]
    assert r.pending()['1']['attempts'] == 2
    assert r.run('--watch', '--drain').returncode == 1
    assert r.requests == [1, 1]
    r.status = 200
    assert r.run('--watch', '--system', 'snes', '--rom', 'Game1.sfc', '--force').returncode == 0
    assert r.pending() == {}

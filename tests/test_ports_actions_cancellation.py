"""Automatic cancellation at real HTTP/save boundaries, and manual override."""
import threading
import time
from test_ra_queue import queue_rig
from test_playtime_auto_refresh import library, worker, run, text


def test_disable_during_http_retains_old_outputs_and_pending(queue_rig):
    r = queue_rig
    assert r.run().returncode == 0
    before = (r.state/'extras/snes/Game1.xml').read_bytes()
    r.requests.clear(); r.block = True
    process = r.start('--automatic', '--watch', '--force')
    assert r.entered.wait(5)
    (r.state/'auto-disabled').write_text('disabled')
    r.release.set()
    process.communicate(timeout=10)
    assert r.requests == [1]
    assert (r.state/'extras/snes/Game1.xml').read_bytes() == before
    assert r.pending()
    r.requests.clear()
    assert r.run('--automatic', '--drain', '--watch').returncode == 0
    assert r.requests == []
    assert r.run('--force').returncode == 0  # Explicit manual refresh still works.
    assert r.requests


def test_disabled_auto_queue_not_drained_by_existing_manual_worker(queue_rig):
    r = queue_rig; r.block = True
    process = r.start('--system', 'snes', '--rom', 'Game1.sfc')
    assert r.entered.wait(5)
    assert r.run('--automatic', '--system', 'snes', '--rom', 'Game3.sfc', '--force').returncode == 0
    (r.state/'auto-disabled').write_text('disabled')
    r.release.set(); process.communicate(timeout=10)
    assert r.requests == [1]
    assert '3' in r.pending()


def test_disabled_auto_worker_services_manual_full_refresh(queue_rig):
    r = queue_rig; r.block = True
    process = r.start('--automatic', '--force', '--watch')
    assert r.entered.wait(5)
    (r.state/'auto-disabled').write_text('disabled')
    manual = r.run('--force', '--watch')
    assert manual.returncode == 0
    assert 'request queued' in manual.stdout
    r.release.set()
    out, err = process.communicate(timeout=10)
    assert process.returncode == 0, (out, err)
    assert r.requests == [1, 1, 2, 3]
    assert r.pending() == {}
    assert len(list((r.state/'extras/snes').glob('*.xml'))) == 3


def test_disabled_auto_worker_services_only_manual_target(queue_rig):
    r = queue_rig; r.block = True
    process = r.start('--automatic', '--force', '--watch')
    assert r.entered.wait(5)
    (r.state/'auto-disabled').write_text('disabled')
    assert r.run('--force', '--watch', '--system', 'snes', '--rom', 'Game3.sfc').returncode == 0
    r.release.set()
    process.communicate(timeout=10)
    assert r.requests == [1, 3]
    assert set(r.pending()) == {'1', '2'}
    assert r.pending()['1']['attempts'] == 0
    assert not (r.state/'extras/snes/Game1.xml').exists()
    assert not list((r.state/'cache').rglob('1.json'))
    assert (r.state/'extras/snes/Game3.xml').exists()


def test_explicit_stop_still_retains_manual_handoff(queue_rig):
    r = queue_rig; r.block = True
    process = r.start('--automatic', '--force', '--watch')
    assert r.entered.wait(5)
    (r.state/'auto-disabled').write_text('disabled')
    assert r.run('--force', '--watch').returncode == 0
    stopper = r.start('--stop')
    deadline = time.monotonic() + 5
    while not (r.state/'stop.request').exists() and time.monotonic() < deadline:
        time.sleep(.01)
    assert (r.state/'stop.request').exists()
    r.release.set()
    process.communicate(timeout=10)
    stopper.communicate(timeout=10)
    assert process.returncode == 1
    assert stopper.returncode == 0
    assert r.requests == [1]
    assert set(r.pending()) == {'1', '2', '3'}
    assert all(job['automatic'] is False for job in r.pending().values())
    assert not list((r.state/'extras').rglob('*.xml'))


def test_disable_during_saved_snapshot_does_not_publish(library):
    w = worker(); root = library[0]
    run(w, library, refresh_all=True)
    original = w.snapshot
    def disable(*args, **kwargs):
        marker = root/'system/art-book-next-playtime/auto-disabled'
        marker.parent.mkdir(parents=True, exist_ok=True); marker.write_text('disabled')
        total, ready, stamps = original(*args, **kwargs)
        return '999h 0m', True, stamps
    w.snapshot = disable
    run(w, library, system='nes', rom=library[1]/'sub/a.zip', since=time.time(), timeout=.1)
    assert text(root) == '1h 0m'


def test_enable_achievements_creates_configuration_without_queue(tmp_path):
    from test_ports_actions import module
    m = module(); m.install_features(tmp_path)
    m.apply(tmp_path, 'enable-achievements')
    assert (tmp_path/'system/retroachievements/config.json').exists()
    assert not (tmp_path/'system/retroachievements/pending.json').exists()

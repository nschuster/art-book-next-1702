"""Validated definition cache is separate from account unlock progress."""
import json
import os
import time
from test_ra_batocera import rig


def test_forced_progress_uses_fresh_definition_but_fetches_both_unlock_modes(rig):
    assert rig.sync().returncode == 0
    assert rig.sync('--force').returncode == 0
    assert [fields['r'][0] for _,fields,_ in rig.requests] == ['patch','unlocks','unlocks','unlocks','unlocks']
    path=rig.config.parent/'definitions/1.json'
    assert path.exists()
    data=json.loads(path.read_text())
    assert data == {'ID':1,'core':[10,11]}
    assert 'fixture-user' not in path.read_text()


def test_expired_definition_failure_cannot_refresh_progress_timestamp(rig):
    assert rig.sync().returncode == 0
    definition=rig.config.parent/'definitions/1.json'
    assert definition.exists(), 'definition cache must be separate'
    os.utime(definition,(1,1))
    cache=next((rig.config.parent/'cache').rglob('*.json'))
    before=(cache.read_bytes(),cache.stat().st_mtime_ns,rig.output.read_bytes())
    rig.status=503
    assert rig.sync('--force').returncode == 1
    assert (cache.read_bytes(),cache.stat().st_mtime_ns,rig.output.read_bytes()) == before
    assert rig.requests[-1][1]['r']==['patch']


def test_corrupt_definition_refetched_and_never_trusted(rig):
    assert rig.sync().returncode == 0
    definition=rig.config.parent/'definitions/1.json'
    assert definition.exists()
    definition.write_text(json.dumps({'ID':1,'core':[True,'10']}))
    assert rig.sync('--force').returncode == 0
    assert rig.requests[-3][1]['r']==['patch']
    assert json.loads(definition.read_text()) == {'ID':1,'core':[10,11]}

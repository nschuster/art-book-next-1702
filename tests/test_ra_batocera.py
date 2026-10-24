"""Token backend: subprocess CLI and local HTTP only, no real accounts."""
import json
from pathlib import Path
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs
import xml.etree.ElementTree as ET
import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts/retroachievements'

@pytest.fixture
def rig(tmp_path):
    class Rig:
        root = tmp_path
        requests = []
        status = 200
        bad = None
        bad_unlocks = None
        def cli(self, script, *args):
            return subprocess.run([sys.executable, str(script), '--data-root', str(self.root), *args], input='', text=True, capture_output=True)
        def credentials(self, enabled='1', user='fixture-user', token='fixture-token', hardcore='1'):
            self.conf.write_text(f'global.retroachievements={enabled}\nglobal.retroachievements.username={user}\nglobal.retroachievements.token={token}\nglobal.retroachievements.hardcore={hardcore}\nglobal.retroachievements.password=NEVER-USE-PASSWORD\n')
        def sync(self, *args):
            return self.cli(SCRIPTS/'sync.py', '--config', str(self.config), '--test-api-base', self.url, *args)
        def label(self):
            return ET.parse(self.output).findtext('./view/text/text')
    r = Rig()
    r.conf = tmp_path/'system/batocera.conf'; r.conf.parent.mkdir()
    game = tmp_path/'roms/snes/gamelist.xml'; game.parent.mkdir(parents=True)
    game.write_text('<gameList><game><path>Game.sfc</path><cheevosId>1</cheevosId></game></gameList>')
    r.config = tmp_path/'system/retroachievements/config.json'
    r.output = tmp_path/'system/retroachievements/extras/snes/Game.xml'
    r.credentials()
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            fields = parse_qs(self.rfile.read(int(self.headers['Content-Length'])).decode())
            r.requests.append((self.path, fields, self.headers['Content-Type']))
            payload = {'Success': True, 'PatchData': {'ID': 1, 'Achievements': [{'ID': 10, 'Flags': 3}, {'ID': 11, 'Flags': 3}, {'ID': 11, 'Flags': 3}, {'ID': 12, 'Flags': 5}]}} if fields['r'] == ['patch'] else {'Success': True, 'UserUnlocks': [10, 10, 12, 999] if fields['h'] == ['1'] else [10, 11, 12]}
            if r.bad is not None: payload = r.bad
            if fields['r'] == ['unlocks'] and r.bad_unlocks is not None: payload = r.bad_unlocks
            self.send_response(r.status)
            if r.status == 302: self.send_header('Location', r.url+'stolen')
            self.end_headers(); self.wfile.write(json.dumps(payload).encode())
        def log_message(self, *args): pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    r.url = f'http://127.0.0.1:{server.server_port}/'
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    # Intentionally write the desired new config directly so transport RED is independent of setup RED.
    r.config.parent.mkdir(); r.config.write_text(json.dumps({'backend': 'batocera', 'systems': ['snes'], 'min_interval': 0, 'backoff': 0, 'retries': 1})); r.config.chmod(0o600)
    yield r
    server.shutdown(); server.server_close(); thread.join()


def test_default_setup_installed_cli_no_inputs(rig):
    rig.config.unlink()
    p = rig.cli(SCRIPTS/'install.py'); assert p.returncode == 0, p.stderr
    installed = rig.config.parent
    p = rig.cli(installed/'configure.py'); assert p.returncode == 0, p.stderr
    cfg = json.loads(rig.config.read_text())
    assert cfg['backend'] == 'batocera' and cfg['systems'] == ['snes']
    assert not {'username', 'api_key', 'token', 'password', 'mode'} & cfg.keys()
    assert rig.config.stat().st_mode & 0o777 == 0o600
    p = rig.cli(installed/'sync.py', '--config', str(rig.config), '--test-api-base', rig.url)
    assert p.returncode == 0, p.stderr
    assert rig.label() == '1/2'


def test_post_contract_and_secret_free_persistence(rig):
    before = rig.conf.read_bytes()
    p = rig.sync(); assert p.returncode == 0, p.stderr
    assert rig.label() == '1/2'
    assert len(rig.requests) == 3
    for path, fields, content_type in rig.requests:
        assert path == '/dorequest.php'
        assert content_type == 'application/x-www-form-urlencoded'
        assert fields['u'] == ['fixture-user'] and fields['t'] == ['fixture-token'] and fields['g'] == ['1']
        assert set(fields) == ({'r','u','t','g'} if fields['r'] == ['patch'] else {'r','u','t','g','h'})
    assert {f['h'][0] for _, f, _ in rig.requests if 'h' in f} == {'0','1'}
    assert rig.conf.read_bytes() == before
    for file in rig.config.parent.rglob('*'):
        if file.is_file():
            assert b'fixture-token' not in file.read_bytes() and b'NEVER-USE-PASSWORD' not in file.read_bytes()
    assert 'fixture-token' not in p.stdout+p.stderr


def test_mode_and_account_and_token_are_read_each_run(rig):
    assert rig.sync().returncode == 0
    rig.credentials(hardcore='0'); assert rig.sync().returncode == 0
    assert rig.label() == '2/2' and len(rig.requests) == 3
    rig.credentials(user='other-user', token='new-token'); assert rig.sync().returncode == 0
    assert rig.requests[-1][1]['u'] == ['other-user'] and rig.requests[-1][1]['t'] == ['new-token']
    rig.credentials(user='third-user'); rig.status = 503
    assert rig.sync().returncode != 0
    assert not rig.output.exists()


@pytest.mark.parametrize('enabled,token', [('0','fixture-token'), ('1',''), ('1',None)])
def test_disabled_or_missing_token_prunes_owned_output(rig, enabled, token):
    assert rig.sync().returncode == 0
    rig.credentials(enabled=enabled, token=token or '')
    if token is None: rig.conf.unlink()
    p = rig.sync()
    assert p.returncode == (0 if enabled == '0' else 2)
    assert not rig.output.exists() and len(rig.requests) == 3
    if enabled != '0': assert 'Batocera' in p.stderr and 'reauthenticate' in p.stderr


@pytest.mark.parametrize('bad', [ {'Success':False,'Error':'fixture-token'}, {'Success':True}, {'Success':True,'PatchData':{'ID':True,'Achievements':[]}}, {'Success':True,'PatchData':{'ID':1,'Achievements':[{'ID':True,'Flags':3}]}}, {'Success':True,'PatchData':{'ID':1,'Achievements':[{'ID':1,'Flags':'3'}]}} ])
def test_bad_responses_never_publish_zero(rig, bad):
    rig.bad = bad
    p = rig.sync(); assert p.returncode == 1
    assert not rig.output.exists()
    assert 'fixture-token' not in p.stdout+p.stderr
    assert 'reauthenticate' in p.stderr


def test_retries_and_redirects_are_bounded(rig):
    rig.status=503
    assert rig.sync().returncode == 1 and len(rig.requests) == 2
    rig.requests.clear(); rig.status=302
    assert rig.sync().returncode == 1 and len(rig.requests) == 1


def test_disabled_preserves_modified_extras_with_explicit_error(rig):
    assert rig.sync().returncode == 0
    rig.output.write_text('local-edit'); rig.credentials(enabled='0')
    p = rig.sync(); assert p.returncode == 2
    assert rig.output.read_text() == 'local-edit'
    assert 'modified' in p.stderr and 'disable' in p.stderr


@pytest.mark.parametrize('bad', [{'Success':True}, {'Success':True,'UserUnlocks':[True]}, {'Success':True,'UserUnlocks':['10']}, {'Success':True,'UserUnlocks':[-1]}, {'Success':True,'UserUnlocks':[4294967296]}, {'Success':False,'Error':'fixture-token'}])
def test_invalid_unlocks_preserve_previous_not_false_zero(rig, bad):
    assert rig.sync().returncode == 0
    before = rig.output.read_bytes()
    rig.bad_unlocks = bad
    p = rig.sync('--force')
    assert p.returncode == 1 and rig.output.read_bytes() == before
    assert 'fixture-token' not in p.stderr+p.stdout


def test_upgrade_old_example_cannot_copy_credentials_into_default_config(rig):
    import shutil
    rig.config.unlink()
    installed = rig.config.parent
    shutil.copy(SCRIPTS/'configure.py', installed/'configure.py')
    (installed/'config.example.json').write_text(json.dumps({'username':'old-user','api_key':'old-secret','token':'old-token','password':'old-password','mode':'hardcore','template':{}}))
    p = rig.cli(installed/'configure.py'); assert p.returncode == 0
    cfg = json.loads(rig.config.read_text())
    assert cfg.get('backend') == 'batocera'
    assert not {'username','api_key','token','password','mode'} & cfg.keys()


def test_password_value_is_never_parsed(monkeypatch, tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location('token_sync', SCRIPTS/'sync.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    class PasswordLine(str):
        def partition(self, *args):
            raise AssertionError('password line must not be split into key/value')
    class Stream:
        def __enter__(self): return iter([PasswordLine('global.retroachievements.password=unused'), 'global.retroachievements=1', 'global.retroachievements.username=test', 'global.retroachievements.token=token'])
        def __exit__(self, *args): pass
    monkeypatch.setattr(Path, 'open', lambda *args, **kwargs: Stream())
    result = module.batocera_settings(tmp_path)
    assert result['token'] == 'token' and result['enabled'] is True
    assert 'password' not in result

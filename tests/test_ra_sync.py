"""Offline integration tests; never contact RetroAchievements."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
import xml.etree.ElementTree as ET

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/retroachievements/sync.py'

class SyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.requests = []
        self.status = 200
        self.payload = {'ID': 1, 'NumAchievements': 10, 'NumAwardedToUser': 4, 'NumAwardedToUserHardcore': 2}
        outer = self
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                outer.requests.append(self.path)
                self.send_response(outer.status)
                self.end_headers()
                self.wfile.write(json.dumps(outer.payload).encode())
            def log_message(self, *args): pass
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.config = self.root / 'config.json'
        self.mapping = self.root / 'mapping.json'
        self.cfg = {'username': 'test-user', 'api_key': 'secret-test-key', 'mode': 'hardcore', 'mapping_file': str(self.mapping), 'systems': ['snes'], 'min_interval': 0, 'retries': 1, 'backoff': 0, 'cache_ttl': 3600}
        self.maps = [{'system': 'snes', 'rom': './A & B.sfc', 'game_id': 1}]
        self.save()
    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(); self.tmp.cleanup()
    def save(self):
        self.config.write_text(json.dumps(self.cfg)); self.config.chmod(0o600)
        self.mapping.write_text(json.dumps(self.maps))
    def run_sync(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), '--config', str(self.config), '--data-root', str(self.root), '--test-api-base', f'http://127.0.0.1:{self.server.server_port}/API/', *args], capture_output=True, text=True)
    def output(self): return self.root / 'system/retroachievements/extras/snes/A & B.xml'
    def test_asset_lifecycle_is_bounded_and_offline_safe(self):
        self.assertEqual(self.run_sync().returncode, 0)
        def asset_path(): return Path(ET.parse(self.output()).findtext('./view/image/path'))
        first=asset_path();self.assertTrue(first.exists())
        self.status=503
        self.assertEqual(self.run_sync('--force').returncode,1)
        self.assertTrue(first.exists())
        self.status=200
        for count in [0,1,3,4]:
            self.payload['NumAwardedToUserHardcore']=count
            self.assertEqual(self.run_sync('--force').returncode,0)
            self.assertTrue(asset_path().exists())
            self.assertEqual(len(list(first.parent.glob('*.svg'))),3)  # fill, track, trophy
            for path in ET.parse(self.output()).findall('./view/image/path'):
                self.assertTrue(Path(path.text).exists())
        other=first.parent/'unrelated.svg';other.write_text('keep')
        self.maps=[];self.save()
        self.assertEqual(self.run_sync().returncode,0)
        self.assertEqual(list(first.parent.glob('*.svg')),[other])

    def test_cli_renders_hardcore_and_caches(self):
        p = self.run_sync(); self.assertEqual(p.returncode, 0, p.stderr)
        node = ET.parse(self.output()).find("./view/text[@name='ra_progress']")
        self.assertEqual(node.get('extra'), 'true'); self.assertEqual(node.findtext('text'), '2/10')
        self.assertEqual(node.findtext('pos'), '0.76953125 0.837916666666667'); self.assertEqual(node.findtext('size'), '0.14 0.045833333333333')
        self.assertEqual(node.findtext('fontPath'),'${themePath}/${fontBold}')
        query = parse_qs(urlparse(self.requests[0]).query)
        self.assertEqual(query['g'], ['1']); self.assertEqual(query['u'], ['test-user']); self.assertEqual(query['y'], ['secret-test-key'])
        self.assertIn('API_GetGameInfoAndUserProgress.php', self.requests[0])
        self.assertEqual(self.run_sync().returncode, 0); self.assertEqual(len(self.requests), 1)
    def test_softcore_and_xml_escaping(self):
        self.cfg.update(mode='softcore', template={'label': 'RA & <count>'}); self.save()
        self.assertEqual(self.run_sync().returncode, 0)
        self.assertEqual(ET.parse(self.output()).findtext('./view/text/text'), 'RA & <count> 4/10')
    def test_offline_preserves_bytes_and_redacts_error(self):
        self.assertEqual(self.run_sync().returncode, 0)
        before = self.output().read_bytes(); self.status = 503
        p = self.run_sync('--force'); self.assertEqual(p.returncode, 1)
        self.assertEqual(self.output().read_bytes(), before)
        self.assertEqual(len(self.requests), 3)
        self.assertNotIn('secret-test-key', p.stdout+p.stderr)
    def test_rejects_unsafe_paths_before_network(self):
        for maps in ([{'system': '../bad', 'rom': 'A.sfc', 'game_id': 1}], [{'system': 'snes', 'rom': '../A.sfc', 'game_id': 1}]):
            self.maps = maps; self.save(); self.assertNotEqual(self.run_sync().returncode, 0)
        self.assertEqual(self.requests, [])
    def test_permissions_rejected_before_network(self):
        self.config.chmod(0o644); p = self.run_sync()
        self.assertNotEqual(p.returncode, 0); self.assertEqual(self.requests, [])
    def test_gamelist_discovery_and_explicit_override(self):
        d = self.root / 'roms/snes'; d.mkdir(parents=True)
        g = d / 'gamelist.xml'
        g.write_text('<gameList><game><path>./A &amp; B.sfc</path><cheevosId>99</cheevosId></game><game><path>other.sfc</path><cheevosId>1</cheevosId></game></gameList>')
        before = g.read_bytes(); p = self.run_sync(); self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue((self.output().parent / 'other.xml').exists()); self.assertEqual(g.read_bytes(), before)
        self.assertEqual(len(self.requests), 1)
    def test_invalid_api_does_not_replace_cache(self):
        self.assertEqual(self.run_sync().returncode, 0); before = self.output().read_bytes()
        self.payload = {'Error': 'secret-test-key'}
        p = self.run_sync('--force'); self.assertEqual(p.returncode, 1)
        self.assertEqual(self.output().read_bytes(), before); self.assertNotIn('secret-test-key', p.stderr)
    def test_symlink_output_rejected(self):
        outside = self.root / 'outside'; outside.mkdir()
        parent = self.output().parent; parent.parent.mkdir(parents=True)
        parent.symlink_to(outside, target_is_directory=True)
        self.assertNotEqual(self.run_sync().returncode, 0); self.assertEqual(list(outside.iterdir()), [])

    def test_collision_with_unmapped_gamelist_rom_is_skipped(self):
        d = self.root / 'roms/snes'; d.mkdir(parents=True)
        (d / 'gamelist.xml').write_text('<gameList><game><path>sub/A &amp; B.zip</path></game></gameList>')
        p = self.run_sync()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('skipped 2 games in 1 ambiguous ROM stem groups', p.stderr)
        self.assertFalse(self.output().exists())
        self.assertEqual(self.requests, [])
    def test_lock_skips_concurrent_run_without_network(self):
        import fcntl
        lock = self.root / 'system/retroachievements/sync.lock'; lock.parent.mkdir(parents=True)
        with lock.open('w') as held:
            fcntl.flock(held, fcntl.LOCK_EX)
            p = self.run_sync()
        self.assertEqual(p.returncode, 0); self.assertIn('already running', p.stdout)
        self.assertEqual(self.requests, [])
    def test_loopback_injection_rejects_external_hosts(self):
        p = self.run_sync('--test-api-base', 'http://example.com/API/')
        self.assertEqual(p.returncode, 2); self.assertEqual(self.requests, [])
    def test_failed_shared_game_id_requested_only_once(self):
        self.maps.append({'system': 'nes', 'rom': 'Other.nes', 'game_id': 1}); self.save(); self.status = 503
        self.assertEqual(self.run_sync().returncode, 1)
        self.assertEqual(len(self.requests), 2)
    def test_filter_limits_after_game_exit_refresh(self):
        self.maps.append({'system': 'snes', 'rom': 'Other.sfc', 'game_id': 2}); self.save()
        p = self.run_sync('--system', 'snes', '--rom', str(self.root / 'roms/snes/A & B.sfc'), '--force')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(len(self.requests), 1)
        self.assertFalse((self.output().parent / 'Other.xml').exists())

class InstallTests(unittest.TestCase):
    def test_idempotent_install_rollback_preserves_user_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            other = root / 'system/services/unrelated'; other.parent.mkdir(parents=True); other.write_text('keep')
            installer = SCRIPT.with_name('install.py')
            def run(*args):
                return subprocess.run([sys.executable, str(installer), '--data-root', str(root), *args], capture_output=True, text=True)
            p = run(); self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(run().returncode, 0)
            self.assertTrue((root / 'system/scripts/ra-progress-sync.sh').exists())
            self.assertTrue((root / 'system/services/ra-progress-sync').exists())
            self.assertEqual(run('--uninstall').returncode, 0)
            self.assertFalse((root / 'system/scripts/ra-progress-sync.sh').exists())
            self.assertEqual(other.read_text(), 'keep')
            self.assertTrue((root / 'system/retroachievements/config.example.json').exists())
    def test_install_refuses_unowned_hook_without_partial_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); hook = root / 'system/scripts/ra-progress-sync.sh'
            hook.parent.mkdir(parents=True); hook.write_text('user content')
            p = subprocess.run([sys.executable, str(SCRIPT.with_name('install.py')), '--data-root', str(root)], capture_output=True)
            self.assertEqual(p.returncode, 2)
            self.assertEqual(hook.read_text(), 'user content')
            self.assertFalse((root / 'system/services/ra-progress-sync').exists())

if __name__ == '__main__': unittest.main()

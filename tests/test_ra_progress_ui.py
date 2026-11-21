"""Real SDL tests use the dummy video driver; no live-account fixtures."""
import ctypes
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / 'scripts/retroachievements/progress_ui.py'

class ProgressUITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if MODULE.exists():
            spec = importlib.util.spec_from_file_location('ra_progress_ui_test', MODULE)
            cls.ui = importlib.util.module_from_spec(spec)
            # Match direct script execution without depending on another test's
            # collection-time sys.path changes for the sibling palette module.
            with patch.object(sys, 'path', [str(MODULE.parent), *sys.path]):
                spec.loader.exec_module(cls.ui)

    def setUp(self):
        self.assertTrue(MODULE.exists(), 'Progress UI implementation is missing')

    def status(self, **kw):
        return dict(schema=1, updated_at=time.time(), state='syncing', system='Super Nintendo', game='Super Mario World', total=12, completed=5, updated=3, cached=2, failed=1, pending=6, attempt=1, **kw)

    def test_transport_retry_does_not_masquerade_as_queue_attempt(self):
        s = self.status(); s.update(state='retrying', attempt=1, request_attempt=3)
        detail = self.ui.build_model(s)['detail']
        self.assertIn('job 1', detail)
        self.assertIn('HTTP 3', detail)

    def test_live_model_and_bounded_layout(self):
        s = self.status()
        s['game'] = 'Very long game title ' * 20 + '\x1b\n'
        model = self.ui.build_model(s)
        self.assertEqual(model['title'], 'Syncing achievements')
        self.assertAlmostEqual(model['fraction'], 6/12)
        self.assertEqual(model['system'], 'Super Nintendo')
        for item in self.ui.layout(model):
            x, y, text, scale = item
            self.assertGreaterEqual(x, 32)
            self.assertLessEqual(x + self.ui.text_width(text, scale), 608)
            self.assertLessEqual(y + 30 * scale, 448)
            self.assertNotIn('\x1b', text)

    def test_absent_malformed_stale_never_complete(self):
        for status in (None, [], {'schema': 99}, {'schema': 1, 'state': 'complete', 'updated_at': 1}):
            model = self.ui.build_model(status)
            self.assertIsNone(model['fraction'])
            self.assertNotEqual(model['title'], 'Sync complete')
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'progress.json'
            self.assertIsNone(self.ui.read_status(p))
            p.write_text('{broken')
            self.assertIsNone(self.ui.read_status(p))

    def test_invalid_counters_and_schema_do_not_claim_completion(self):
        for change in ({'schema': True}, {'updated_at': True}, {'total': '12'}, {'completed': -1}, {'failed': True}, {'state': []}):
            s = self.status(); s['state'] = 'complete'; s.update(change)
            model = self.ui.build_model(s)
            self.assertIsNone(model['fraction'])
            self.assertNotIn(model['title'], ('Sync complete', 'Finished with failures'))

    def test_callback_failure_is_safe_and_resources_are_reusable(self):
        import contextlib
        import io
        def fail():
            raise RuntimeError('private-secret')
        error = io.StringIO()
        with patch.dict(os.environ, SDL_VIDEODRIVER='dummy'), contextlib.redirect_stderr(error):
            self.assertEqual(self.ui.run_ui(Path('/missing'), fail, fullscreen=False, frames=1), 2)
            self.assertEqual(self.ui.run_ui(Path('/missing'), fullscreen=False, frames=1), 0)
        self.assertNotIn('private-secret', error.getvalue())
        self.assertIn('may continue', error.getvalue())

    def test_secondary_readability_uses_full_size_glyphs(self):
        self.assertEqual(self.ui.clean('Yoshi’s Island — “Special”'), 'Yoshi\'s Island - "Special"')
        for _, _, _, scale in self.ui.layout(self.ui.build_model(self.status())):
            self.assertEqual(scale, 1.0, 'Avoid sub-12px glyphs on 320x240')

    def test_terminal_and_retry_states(self):
        for state, title in [('retrying','Retrying request'), ('complete','Finished with failures'), ('stopped','Sync stopped'), ('failed','Sync failed'), ('disabled','Achievements disabled')]:
            s = self.status(); s['state'] = state
            self.assertEqual(self.ui.build_model(s)['title'], title)
        s['state'] = 'complete'; s['failed'] = 0
        self.assertEqual(self.ui.build_model(s)['title'], 'Sync complete')

    def test_quit_actions_conservative_mapping(self):
        for event in (self.ui.event(0x100), self.ui.event(0x300, key=27), self.ui.event(0x651, button=1), self.ui.event(0x651, button=4)):
            self.assertTrue(self.ui.should_quit(event))
        self.assertFalse(self.ui.should_quit(self.ui.event(0x603, button=1)))
        self.assertTrue(self.ui.should_quit(self.ui.event(0x603, button=7), raw_back_button=7))
        self.assertFalse(self.ui.should_quit(self.ui.event(0x651, button=0)))

    def test_real_sdl_render_callback_and_screenshot(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, SDL_VIDEODRIVER='dummy'):
            p = Path(d) / 'progress.json'; p.write_text(json.dumps(self.status()))
            for size in ((640,480), (320,240)):
                bmp = Path(d) / ('%s.bmp' % size[0]); called = []
                result = self.ui.run_ui(p, lambda: called.append(True), fullscreen=False, size=size, frames=2, screenshot=bmp)
                self.assertEqual(result, 0)
                self.assertEqual(called, [True])
                data = bmp.read_bytes()
                self.assertEqual(data[:2], b'BM')
                self.assertEqual(struct.unpack_from('<ii', data, 18), size)
                self.assertGreater(len(set(data[54:])), 8)

    def test_live_json_changes_are_polled_without_restart(self):
        import threading
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, SDL_VIDEODRIVER='dummy'):
            p = Path(d) / 'progress.json'
            first = self.status(); first['state'] = 'scanning'
            last = self.status(); last['state'] = 'complete'; last['failed'] = 0
            p.write_text(json.dumps(first))
            models = []
            build = self.ui.build_model
            def record(*args, **kwargs):
                model = build(*args, **kwargs); models.append(model['title']); return model
            def update():
                time.sleep(.1)
                tmp = p.with_suffix('.tmp'); tmp.write_text(json.dumps(last)); tmp.replace(p)
            thread = threading.Thread(target=update)
            with patch.object(self.ui, 'build_model', side_effect=record):
                self.assertEqual(self.ui.run_ui(p, thread.start, fullscreen=False, frames=9), 0)
            thread.join()
            self.assertIn('Scanning library', models)
            self.assertIn('Sync complete', models)

    def test_real_failed_video_initialization_never_calls_worker(self):
        import contextlib
        import io
        calls = []
        with patch.dict(os.environ, SDL_VIDEODRIVER='no-such-driver'), contextlib.redirect_stderr(io.StringIO()):
            result = self.ui.run_ui(Path('/missing'), lambda: calls.append(1), frames=1)
        self.assertEqual(result, 2)
        self.assertEqual(calls, [])

    def test_real_sdl_quit_event_and_init_failure(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, SDL_VIDEODRIVER='dummy'):
            def close():
                lib = self.ui.load_sdl()
                ev = self.ui.event(0x651, button=1)
                lib.SDL_PushEvent(ctypes.byref(ev))
            self.assertEqual(self.ui.run_ui(Path(d)/'missing', close, fullscreen=False, frames=100), 0)
        calls = []
        with patch.object(self.ui, 'load_sdl', side_effect=OSError('secret')):
            self.assertEqual(self.ui.run_ui(Path('/missing'), lambda: calls.append(1)), 2)
        self.assertEqual(calls, [])

if __name__ == '__main__':
    unittest.main()

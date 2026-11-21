"""Pinned native RA limitation checks; passing is NOT a palette-fill fix.

These inspect actual upstream sources (skip explicitly when unavailable).
No invented theme properties or changes to native progress are made.
"""
import os
from pathlib import Path
import re
import subprocess
import unittest

PIN = '4adf26b43900d1a33887af6d8af3da2e99e398a5'


class NativeRAProgressContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(os.environ.get('BATOCERA_ES_SOURCE', '/tmp/ra-es-source'))
        if not (source / '.git').exists():
            raise unittest.SkipTest('Set BATOCERA_ES_SOURCE to the pinned ES checkout')
        def read(path):
            return subprocess.check_output(['git', 'show', PIN + ':' + path], cwd=source, text=True)
        cls.overview = read('es-app/src/guis/GuiRetroAchievements.cpp')
        cls.detail = read('es-app/src/guis/GuiGameAchievements.cpp')
        cls.header = read('es-app/src/guis/GuiRetroAchievements.h')
        cls.schema = read('es-core/src/ThemeData.cpp')

    def test_both_dialogs_use_same_non_themed_fill_component(self):
        for source in (self.overview, self.detail):
            self.assertIn('std::make_shared<RetroAchievementProgress>', source)
        self.assertIn('mProgress->render(trans);', self.detail)
        component = self.header.split('class RetroAchievementProgress :')[1]
        self.assertNotIn('applyTheme', component)
        self.assertNotRegex(component, r'(?i)(fill|track|hardcorecolor|softcorecolor)')

    def test_actual_draw_calls_are_fixed_track_softcore_hardcore_colors(self):
        render = self.overview.split('void RetroAchievementProgress::render(')[1].split('#include')[0]
        colors = re.findall(r'Renderer::drawRect\([^;]+;', render)
        self.assertEqual(len(colors), 3)
        self.assertIn('0x00000032, 0x00000032', colors[0])
        self.assertIn('0x0B71C1FF', colors[1])
        self.assertIn('0xCC9900FF', colors[2])
        self.assertNotIn('getMenuTheme', render)
        self.assertNotIn('applyTheme', render)

    def test_supported_color_setter_changes_only_label(self):
        setter = self.overview.split('void RetroAchievementProgress::setColor(unsigned int color)')[1].split('void RetroAchievementProgress::render')[0]
        self.assertEqual(re.sub(r'\s+', '', setter), '{mText->setColor(color);}')
        self.assertIn('label, theme->TextSmall.font, theme->Text.color', self.overview)
        self.assertIn('getElement("menu", "menutext", "menuText")', self.schema)
        self.assertIn('Text.color = elem->get<unsigned int>("color");', self.schema)

    def test_menu_schema_has_no_progress_fill_or_track_properties(self):
        # Actual menu-only schema range, not the unrelated splash images.
        schema = self.schema.split('{ "menuText", {', 1)[1].split('\n};', 1)[0]
        properties = re.findall(r'\{\s*"([^"]+)"\s*,\s*(?:COLOR|FLOAT|STRING|PATH|BOOLEAN|NORMALIZED_PAIR)', schema)
        self.assertIn('selectorColor', properties)
        self.assertIn('color', properties)
        self.assertFalse(any('progress' in p.lower() or 'track' in p.lower() for p in properties))
        self.assertNotIn('"menuProgress"', self.schema)


if __name__ == '__main__':
    unittest.main()

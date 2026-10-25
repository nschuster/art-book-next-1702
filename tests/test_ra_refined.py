"""Palette-independent extras, exact sidebar tint and metadata-sized count."""
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from test_ra_bar import helper
from test_ra_palettes import base, preview

class RefinedTests(unittest.TestCase):
    def test_empty_sample_full_progress_use_same_dynamic_sidebar_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            for scheme in ('famicom','commodore-64'):
                _,variables=base.resolve(scheme)
                for h in (240,480):
                    for count in (0,12,40):
                        image,records=preview.render(h,scheme,Path(tmp),unlocked=count)
                        text=records['ra_progress']
                        self.assertEqual(text['display'],f'{count}/40')
                        self.assertEqual(text['color'],variables['gamelistListTextlistUnselectedColor'])
                        self.assertLessEqual(text['glyph_height'],records['ra_progress_track']['bounds'][3])

    def test_setup_example_does_not_override_native_defaults(self):
        import json
        from test_metadata import ROOT
        cfg=json.loads((ROOT/'scripts/retroachievements/config.example.json').read_text())
        self.assertEqual(cfg['template'],{})

    def test_native_bindings_and_metadata_geometry(self):
        data=dict(ID=1,NumAchievements=40,NumAwardedToUser=18,NumAwardedToUserHardcore=12)
        doc=ET.fromstring(helper.render(data,{},Path('/userdata')))
        track=doc.find("./view/image[@name='ra_progress_track']")
        self.assertIsNotNone(track)
        self.assertEqual(track.findtext('color'),'${raProgressTrackColor}')
        text=doc.find('./view/text')
        self.assertEqual(text.findtext('color'),'${gamelistListTextlistUnselectedColor}')
        self.assertEqual(text.findtext('fontPath'),'${themePath}/${fontBold}')
        self.assertIsNone(text.find('backgroundColor'))
        for node in doc.find('view'):
            expected = '0.041666666666667' if node.get('name') == 'ra_progress_trophy' else '0.045833333333333'
            self.assertEqual(node.findtext('size').split()[1], expected)
        self.assertEqual(text.findtext('fontSize'),'0.027777777777777')

    def test_actual_generated_layers_all_palettes_both_resolutions(self):
        with tempfile.TemporaryDirectory() as tmp:
            for scheme in base.registered_schemes():
                state,variables=base.resolve(scheme)
                for h in (240,480):
                    image,records=preview.render(h,scheme,Path(tmp))
                    x,y,w,z=records['ra_progress_track']['bounds']
                    sidebar=base.color(variables['raProgressTrackColor'])
                    for dx in (w-1,w-2):
                        self.assertEqual(image.getpixel((x+dx,y+z//2)),sidebar)
                    count=records['ra_progress']
                    self.assertEqual(count['color'],variables['gamelistListTextlistUnselectedColor'])
                    self.assertLess(count['font_pixels'],records['md_genre']['font_pixels'])
                    self.assertEqual(count['font_pixels'],9 if h==240 else 17)
                    self.assertEqual(count['bounds'][3],records['md_genre']['bounds'][3])
                    self.assertEqual(count['display'],'12/40')
                    self.assertLessEqual(count['glyph_height'],z)
                    self.assertAlmostEqual(count['bounds'][1]+count['bounds'][3]/2,y+z/2,delta=1)

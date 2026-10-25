"""Real helper assets: proportional geometry, mode selection and safe collection."""
import importlib.util
import tempfile
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
from test_metadata import ROOT
spec=importlib.util.spec_from_file_location('ra_bar_sync',ROOT/'scripts/retroachievements/sync.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)

class BarTests(unittest.TestCase):
    def test_native_asset_and_exact_fraction_both_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for total,soft,hard in [(40,18,12),(0,0,0),(40,0,0),(40,40,40),(3,2,1)]:
                data=dict(ID=1,NumAchievements=total,NumAwardedToUser=soft,NumAwardedToUserHardcore=hard)
                for mode,count in [('softcore',soft),('hardcore',hard)]:
                    doc=ET.fromstring(helper.render(data,{'mode':mode},root))
                    image=doc.find('./view/image')
                    self.assertIsNotNone(image,'Native image progress extra is missing')
                    self.assertEqual(image.attrib,dict(name='ra_progress_bar',extra='true'))
                    self.assertEqual(image.findtext('pos'),'0.5890625 0.815')
                    self.assertEqual(image.findtext('size'),'0.3609375 0.045833333333333')
                    asset,content=helper.progress_asset(data,{'mode':mode},root)
                    self.assertEqual(image.findtext('path'),str(asset));self.assertTrue(asset.is_absolute())
                    svg=ET.fromstring(content);ns={'s':'http://www.w3.org/2000/svg'}
                    self.assertEqual(svg.get('viewBox'),'0 0 1000 85.9375')
                    self.assertEqual(svg.find('s:rect',ns).get('height'),'85.9375')
                    fill=svg.find("s:rect[@id='fill']",ns)
                    self.assertAlmostEqual(float(fill.get('width'))/1000,count/total if total else 0)
                    self.assertGreaterEqual(len(svg.findall('.//s:stop',ns)),5)
                    self.assertIn(f'{count}/{total}',doc.findtext('./view/text/text'))

    def test_owned_asset_collection_preserves_unrelated_and_changed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);state=root/'system/retroachievements'
            data=dict(ID=1,NumAchievements=40,NumAwardedToUser=18,NumAwardedToUserHardcore=12)
            asset,content=helper.progress_asset(data,{},root)
            helper.store_asset(state,asset,content)
            other=asset.parent/'user.svg';other.write_text('keep')
            helper.collect_assets(state,{})
            self.assertFalse(asset.exists());self.assertEqual(other.read_text(),'keep')
            helper.store_asset(state,asset,content);asset.write_text('edited')
            helper.collect_assets(state,{})
            self.assertEqual(asset.read_text(),'edited')

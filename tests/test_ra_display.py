"""Render generated extras with the existing static renderer; sample data only."""
import importlib.util
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
from test_metadata import ROOT

class ProgressDisplayTests(unittest.TestCase):
    def test_preview_exact_extras_layering_and_bottom_clearance(self):
        import sys
        sys.path.insert(0,str(ROOT/'tools'))
        import render_ra_preview as preview
        for h in (240,480):
            for scheme in ('default','commodore-64'):
                image, records=preview.render(h,scheme)
                x,y,w,z=records['ra_progress_bar']['bounds']
                tx,ty,tw,th=records['ra_progress']['bounds']
                self.assertAlmostEqual(tx+tw/2,x+w/2,delta=1)
                self.assertAlmostEqual(ty+th/2,y+z/2,delta=1)
                self.assertGreater(y,records['md_genre']['bounds'][1]+records['md_genre']['bounds'][3])
                self.assertLess(y+z,h*(1-0.114583333333333))
                self.assertEqual(image.getpixel((tx+2,ty+2)),image.getpixel((x+w-1,y+z//2)))
                self.assertEqual(records['ra_progress']['display'],'12/40')

    def test_count_alignment_and_full_sample_width(self):
        spec=importlib.util.spec_from_file_location('ra_sync',ROOT/'scripts/retroachievements/sync.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        doc=ET.fromstring(module.render({'ID':1,'NumAchievements':100,'NumAwardedToUser':25,'NumAwardedToUserHardcore':12}, {'mode':'hardcore'}, Path('/userdata')))
        text=doc.find('./view/text')
        props={p.tag:p.text for p in text}
        self.assertEqual(props.get('origin'),'0.5 0.5')
        self.assertEqual(props['pos'],'0.76953125 0.837916666666667')
        self.assertEqual(props['size'],'0.14 0.045833333333333')
        self.assertEqual(props['text'],'12/100')
        self.assertEqual(props['alignment'],'center')
        self.assertEqual(props['color'],'${gamelistListTextlistUnselectedColor}')
        self.assertNotIn('backgroundColor',props)
        self.assertGreater(float(props['zIndex']),float(doc.findtext('./view/image/zIndex')))
        self.assertEqual(props.get('multiLine'),'false')
        self.assertEqual(props.get('fontSize'),'0.027777777777777')
        self.assertEqual(props['fontPath'],'${themePath}/${fontBold}')
        from PIL import ImageFont
        for h,w in [(240,320),(480,640)]:
            size=max(1,int(int(float(props['fontSize'])*h)*(1.5 if h==240 else 1.31)))
            font=ImageFont.truetype(str(ROOT/'_inc/fonts/Roboto-Bold.ttf'),size)
            self.assertLessEqual(font.getlength(props['text']),float(props['size'].split()[0])*w)
            box=font.getbbox(props['text'])
            self.assertLessEqual(box[3]-box[1],float(props['size'].split()[1])*h)
            self.assertEqual(size,9 if h==240 else 17)

if __name__=='__main__':unittest.main()

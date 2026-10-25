"""Track-edge regression and complete registered palette preview coverage."""
import io
import re
import sys
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET
import unittest
from test_metadata import ROOT
from test_ra_bar import helper
sys.path.insert(0, str(ROOT/'tools'))
import render_metadata_panel as base
import render_ra_preview as preview
import cairosvg
from PIL import Image

class AllPaletteTests(unittest.TestCase):
    def test_fill_transparency_and_white_track_have_no_pale_edge(self):
        for count in (0,12,40):
            data=dict(ID=1,NumAchievements=40,NumAwardedToUser=count,NumAwardedToUserHardcore=count)
            _, content=helper.progress_asset(data,{},ROOT)
            doc=ET.fromstring(content)
            self.assertFalse(any(n.get('stroke') for n in doc.iter()))
            with Image.open(io.BytesIO(cairosvg.svg2png(bytestring=content,output_width=256,output_height=22))) as source:
                raster=source.convert('RGBA')
            if count<40:
                for x in (100,254,255):
                    for y in (0,11,21):
                        self.assertEqual(raster.getpixel((x,y))[3],0)
            else:
                self.assertEqual(raster.getchannel('A').getextrema(),(255,255))
                self.assertLess(raster.getpixel((255,11))[0],100)
        _,content=helper.track_asset(ROOT)
        for w,h in ((256,22),(128,11)):
            with Image.open(io.BytesIO(cairosvg.svg2png(bytestring=content,output_width=w,output_height=h))) as track:
                self.assertEqual(track.convert('RGBA').getextrema(),((255,255),)*4)

    def test_all_registered_palettes_are_resolved_and_rendered(self):
        registrations=ET.fromstring(re.sub(r'&(?!#?\w+;)', '&amp;', (ROOT/'theme.xml').read_text())).find("subset[@name='color-scheme']")
        expected={n.get('name'):n.get('displayName') for n in registrations}
        self.assertEqual(base.registered_schemes(),expected)
        palette_doc=ET.parse(ROOT/'colors.xml').getroot()
        signatures=set()
        for scheme in expected:
            state,values=base.resolve(scheme)
            block=next(b for b in palette_doc.findall('variables') if scheme in b.get('ifSubset').split(':')[1].split('|'))
            for prop in block:
                self.assertEqual(values[prop.tag],prop.text, (scheme,prop.tag))
            self.assertFalse(any('${' in v for p in state.values() for v in p.values()))
            image,records=preview.render(480,scheme)
            self.assertEqual(image.size,(640,480))
            self.assertEqual(records['ra_progress_bar']['bounds'],[377,391,231,22])
            self.assertEqual(records['ra_progress']['display'],'12/40')
            signatures.add(image.tobytes())
        # Shipped Custom template intentionally equals Default; seven distinct designs.
        self.assertEqual(len(signatures),len(expected)-1)

    def test_gallery_covers_every_registration_and_labels_custom_provenance(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            preview.render_gallery(out)
            manifest=json.loads((out/'manifest.json').read_text())
            self.assertEqual(list(manifest['schemes']),list(base.registered_schemes()))
            self.assertIn('shipped',manifest['schemes']['custom']['palette_source'])
            for scheme in base.registered_schemes():
                with Image.open(out/f'{scheme}-480.png') as image:
                    self.assertEqual(image.size,(640,480))
                with Image.open(out/f'{scheme}-480-labeled.png') as image:
                    self.assertEqual(image.size,(640,535))
                with Image.open(out/f'{scheme}-240.png') as image:
                    self.assertEqual(image.size,(320,240))
            self.assertEqual(len(list(out.glob('contact-sheet-*.png'))),2)

    def test_custom_palette_is_actually_loaded_not_silently_defaulted(self):
        with tempfile.TemporaryDirectory() as tmp:
            palette=Path(tmp)/'colors.xml'
            palette.write_text('<theme><variables><gamelistListBackgroundColor>123456</gamelistListBackgroundColor></variables></theme>')
            state,values=base.resolve('custom',custom_palette=palette)
            self.assertEqual(state['image','background']['color'],'123456')
            with self.assertRaises(FileNotFoundError):
                base.resolve('custom',custom_palette=Path(tmp)/'missing.xml')
        with self.assertRaises(ValueError):
            base.resolve('not-a-registered-scheme')

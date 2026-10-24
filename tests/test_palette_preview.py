"""Optional Pillow/CairoSVG static preview checks (not native renderer QA)."""
import sys
import unittest
from test_metadata import ROOT
sys.path.insert(0, str(ROOT/'tools'))
try:
    import render_metadata_panel as renderer
except ImportError:
    renderer = None


@unittest.skipIf(renderer is None, 'Preview requires Pillow and CairoSVG')
class PalettePreviewTests(unittest.TestCase):
    def test_c64_resolves_and_renders_real_palette_not_default_strip(self):
        state, values = renderer.resolve('commodore-64')
        self.assertEqual(state['image', 'background']['color'], '40318d')
        for h in (240, 480):
            im, records = renderer.render(h, 'commodore-64')
            self.assertEqual(im.getpixel((im.width-1, 0)), (64, 49, 141))
            self.assertEqual(im.getpixel((0, 0)), (48, 37, 104))
            self.assertEqual(im.getpixel((0, h-1)), (48, 37, 104))
            footer = im.crop((0, round(h*.886), im.width, h))
            self.assertIn((184, 176, 255), {rgb for count, rgb in footer.getcolors(footer.width*footer.height)})
            self.assertEqual(sum(k.startswith('md_') for k in records), 7)
            default, _ = renderer.render(h)
            self.assertEqual(default.getpixel((im.width-1, 0)), (34, 34, 34))
            self.assertEqual(default.getpixel((0, h-1)), (0, 0, 0))

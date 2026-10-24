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
        self.assertEqual(state['image', 'background']['color'], 'd8cfb6')
        self.assertEqual(state['textlist', 'gamelist']['selectorImagePath'], './_inc/commodore-selector.svg')
        for h in (240, 480):
            im, records = renderer.render(h, 'commodore-64')
            self.assertEqual(im.getpixel((im.width-1, 0)), (216, 207, 182))
            self.assertEqual(im.getpixel((0, 0)), (48, 43, 38))
            self.assertEqual(im.getpixel((0, h-1)), (41, 41, 41))
            footer = im.crop((0, round(h*.886), im.width, h))
            self.assertIn((194, 190, 180), {rgb for count, rgb in footer.getcolors(footer.width*footer.height)})
            self.assertEqual(sum(k.startswith('md_') for k in records), 6)
            self.assertEqual(records['game-gametime-totalhours']['display'], '2h 35m')
            p = state['textlist', 'gamelist']
            x, y = renderer.xy(p, im.width, h)
            bw, bh = renderer.wh(p, im.width, h)
            row = bh/int(p['lines'])
            stripe = im.crop((round(x), round(y+3*row), round(x+bw), round(y+4*row)))
            pixels = {rgb for count, rgb in stripe.getcolors(stripe.width*stripe.height)}
            for accent in ('ad5144', 'c88046', 'd4b65c', '73946b', '648c9b'):
                self.assertIn(tuple(bytes.fromhex(accent)), pixels)
            default, _ = renderer.render(h)
            self.assertEqual(default.getpixel((im.width-1, 0)), (34, 34, 34))
            self.assertEqual(default.getpixel((0, h-1)), (0, 0, 0))

"""Standalone launch-theme semantics; source-schema checks are not renderer QA."""
import os
from pathlib import Path
import re
import subprocess
import unittest
import xml.etree.ElementTree as ET

from test_metadata import ROOT
from test_c64 import contrast

PIN = '4adf26b43900d1a33887af6d8af3da2e99e398a5'
PALETTES = ['default', 'light', 'steam-os', 'snes', 'famicom', 'oled', 'commodore-64', 'custom']


def resolve_launch(scheme='default', distribution='batocera', custom=None):
    """Ordered variables/includes, subset OR, and typed views used by this file.

    External custom colors are supplied as XML fixtures, never read from userdata.
    Runtime {game:...} bindings deliberately survive this theme-variable pass.
    """
    options = {'color-scheme': scheme, 'distribution': distribution}
    variables, elements, includes = {}, {}, []

    def active(node):
        for clause in node.get('ifSubset', '').split(','):
            if clause:
                key, values = clause.split(':')
                selected = options.get(key)
                if not selected:
                    return True  # native accepts unknown/unset subset
                if selected not in values.split('|'):
                    return False
        return True

    def expand(text):
        return re.sub(r'\$\{([^}]+)\}', lambda m: variables[m[1]], (text or '').strip())

    def load(root):
        for node in root:
            if not active(node):
                continue
            if node.tag == 'subset':
                if not options.get(node.get('name')):
                    options[node.get('name')] = node[0].get('name')
            elif node.tag == 'variables':
                for var in node:
                    if active(var):
                        variables[var.tag] = expand(var.text)
            elif node.tag == 'include':
                path = expand(node.text)
                includes.append(path)
                if path == './colors.xml':
                    load(ET.parse(ROOT / 'colors.xml').getroot())
                elif path == variables['themeCustomizationsPath'] + 'colors.xml':
                    if custom is not None:
                        load(ET.fromstring(custom))
                else:
                    raise AssertionError('Unexpected include: ' + path)
            elif node.tag == 'view' and node.get('name') == 'splash':
                for elem in node:
                    if active(elem):
                        key = (elem.tag, elem.get('name'))
                        elements.setdefault(key, {}).update({p.tag: expand(p.text) for p in elem if active(p)})
    load(ET.parse(ROOT / 'gamesplash.xml').getroot())
    return variables, elements, includes


class GameSplashTests(unittest.TestCase):
    def test_unset_subset_defaults_are_registered_locally(self):
        # Native node filtering accepts EVERY ifSubset when both the setting
        # and local subset list are empty. Avoid last-palette-wins on first run.
        root = ET.parse(ROOT / 'gamesplash.xml').getroot()
        for name, default in [('color-scheme', 'default'), ('distribution', 'batocera')]:
            subset = root.find(f"subset[@name='{name}']")
            assert subset is not None, name
            variables = root.find('variables')
            assert variables is not None
            self.assertEqual(subset[0].get('name'), default)
            self.assertLess(list(root).index(subset), list(root).index(variables))
        self.assertEqual(resolve_launch('', '')[1:], resolve_launch()[1:])

    def test_standalone_launch_entry_exists(self):
        self.assertTrue((ROOT / 'gamesplash.xml').is_file(), 'Missing standalone game-launch theme')

    def test_palette_resolution_and_contrast(self):
        for scheme in PALETTES:
            variables, elements, _ = resolve_launch(scheme)
            bg = elements['splash', 'splash']['backgroundColor']
            fg = elements['text', 'label']['color']
            self.assertEqual(bg, variables['gamelistListBackgroundColor'])
            self.assertEqual(fg, variables['gamelistListDescriptionColor'])
            # Composite the existing palette's text alpha before contrast.
            alpha = int(fg[6:8], 16) / 255 if len(fg) == 8 else 1
            opaque = ''.join(f'{round(int(fg[i:i+2],16)*alpha + int(bg[i:i+2],16)*(1-alpha)):02x}' for i in (0,2,4))
            self.assertGreaterEqual(contrast(bg, opaque), 4.5, scheme)

    def test_custom_colors_override_defaults_in_order(self):
        fixture = '<theme><variables><gamelistListBackgroundColor>123456</gamelistListBackgroundColor><gamelistListDescriptionColor>fedcba</gamelistListDescriptionColor></variables></theme>'
        for distribution, prefix in [('batocera', '/userdata/'), ('retrobat', '~/.emulationstation/')]:
            _, elements, includes = resolve_launch('custom', distribution, fixture)
            self.assertEqual(includes, ['./colors.xml', prefix + 'theme-customizations/art-book-next/colors.xml'])
            self.assertEqual(elements['splash', 'splash']['backgroundColor'], '123456')
            self.assertEqual(elements['text', 'label']['color'], 'fedcba')
        self.assertEqual(resolve_launch('custom')[1], resolve_launch('default')[1])
        self.assertEqual(resolve_launch('oled', custom=fixture)[2], ['./colors.xml'])

    def test_boxart_replaces_runtime_scraped_image_and_missing_art_stays_blank(self):
        _, elements, _ = resolve_launch()
        image = elements['image', 'background']
        self.assertEqual(image['path'], '{game:thumbnail}')
        self.assertNotIn('default', image)  # no screenshot substitution
        self.assertNotIn('minSize', image)
        self.assertNotIn('size', image)
        self.assertEqual(image['roundCorners'], '0')
        # Model Splash's path selection BEFORE file-existence loading. A binding
        # overrides its initial screenshot even if boxart is empty/nonexistent.
        for boxart in ['/media/cover.png', '', '/missing/cover.png']:
            initial_image = '/media/screenshot.png'
            selected = image.get('path', initial_image)
            bound = selected.replace('{game:thumbnail}', boxart)
            self.assertEqual(bound, boxart)
            self.assertNotEqual(bound, initial_image)

    def test_4_3_bounds_and_aspect_fit(self):
        _, elements, _ = resolve_launch()
        image, label = elements['image', 'background'], elements['text', 'label']
        pair = lambda p: tuple(map(float, p.split()))
        self.assertEqual(pair(image['origin']), (.5, .5))
        self.assertEqual(pair(image['pos']), (.5, .42))
        self.assertEqual(pair(image['maxSize']), (.70, .60))
        self.assertEqual(pair(label['origin']), (.5, 0))
        self.assertEqual(label['multiLine'], 'false')
        self.assertEqual(label['alignment'], 'center')
        self.assertEqual(label['forceUppercase'], 'false')
        self.assertNotIn('text', label)  # Window supplies getName() after construction
        self.assertTrue((ROOT / label['fontPath']).is_file())
        for w, h in [(640, 480), (320, 240)]:
            maxw, maxh = (v * dim for v, dim in zip(pair(image['maxSize']), (w, h)))
            for iw, ih in [(600,900), (900,600), (600,600), (1800,300)]:
                scale = min(maxw/iw, maxh/ih)
                aw, ah = iw*scale, ih*scale
                self.assertAlmostEqual(aw/ah, iw/ih)
                self.assertGreaterEqual(.5*w-aw/2, .05*w)
                self.assertGreaterEqual(.42*h-ah/2, .05*h)
                self.assertLessEqual(.42*h+ah/2, .72*h + 1e-6)
            x, y = pair(label['pos'])
            lw, lh = pair(label['size'])
            self.assertGreaterEqual(x-lw/2, .05)
            self.assertLessEqual(x+lw/2, .95)
            self.assertGreater(y, .72)
            self.assertLessEqual(y+lh, .95)
            self.assertGreaterEqual(int(h*float(label['fontSize'])), 12)

    def test_only_native_builtins_no_fake_progress_or_extras(self):
        root = ET.parse(ROOT / 'gamesplash.xml').getroot()
        self.assertEqual(root.findtext('formatVersion'), '7')
        self.assertEqual([v.get('name') for v in root.findall('view')], ['splash'])
        _, elements, _ = resolve_launch()
        self.assertEqual(set(elements), {('splash','splash'), ('image','background'), ('text','label'), ('image','progressbar'), ('image','progressbar:active')})
        for name in ['progressbar', 'progressbar:active']:
            self.assertEqual(elements['image', name]['visible'], 'false')
        self.assertFalse(root.findall('.//*[@extra]'))

    def test_existing_runtime_xml_unchanged(self):
        paths = subprocess.check_output(['git','ls-tree','-r','--name-only','2a93d44'], cwd=ROOT, text=True).splitlines()
        for path in paths:
            if path.endswith('.xml') and not path.startswith(('previews/', 'tests/')):
                old = subprocess.check_output(['git','show', '2a93d44:'+path], cwd=ROOT)
                self.assertEqual((ROOT/path).read_bytes(), old, path)

    def test_pinned_native_schema_and_launch_binding_contract(self):
        source = Path(os.environ.get('BATOCERA_ES_SOURCE', '/tmp/ra-es-source'))
        if not (source / '.git').exists():
            self.skipTest('Set BATOCERA_ES_SOURCE to ES checkout containing ' + PIN)
        def read(path):
            return subprocess.check_output(['git','show', PIN+':'+path], cwd=source, text=True)
        schema = read('es-core/src/ThemeData.cpp')
        # Check EVERY emitted property against the actual native element map,
        # not a copied hand-maintained whitelist. This is not a parser execution.
        view = ET.parse(ROOT / 'gamesplash.xml').getroot().find('view')
        assert view is not None
        for elem in view:
            block = re.search(r'\{ "'+elem.tag+r'", \{(.*?\})(?=\s*\})', schema, re.S)
            assert block is not None, elem.tag
            native = dict(re.findall(r'\{ "(\w+)", (\w+) \}', block[1]))
            for prop in elem:
                self.assertIn(prop.tag, native, (elem.tag, prop.tag))
                if native[prop.tag] == 'NORMALIZED_PAIR':
                    self.assertEqual(len(list(map(float, prop.text.split()))), 2)
                elif native[prop.tag] == 'BOOLEAN':
                    self.assertIn(prop.text, ['true', 'false'])
                elif native[prop.tag] == 'FLOAT':
                    float(prop.text)
        splash = read('es-core/src/Splash.cpp')
        for token in ['"/gamesplash.xml"', 'theme->loadFile("splash"', 'std::string imagePath = image;', 'tmp.find("{game:")', 'ThemeFlags::ALL ^ (ThemeFlags::PATH)', 'mBackground.setExtraType(ExtraType::EXTRA)', 'BindingManager::updateBindings(&mBackground, bindable)', 'if (mPercent >= 0)']:
            self.assertIn(token, splash)
        self.assertIn('float percent = -1', read('es-core/src/Splash.h'))
        filedata = read('es-app/src/FileData.cpp')
        self.assertIn('setCustomSplashScreen(gameToUpdate->getImagePath(), gameToUpdate->getName(), gameToUpdate)', filedata)
        self.assertIn('std::string finalValue = md.get(name);', filedata)
        self.assertIn('return BindableProperty(finalValue, BindablePropertyType::Path);', filedata)
        self.assertIn('file->getThumbnailPath(false)', filedata)
        from test_c64 import parse
        main_theme = parse((ROOT / 'theme.xml').read_bytes())
        self.assertTrue(any(p.text == '{game:thumbnail}' for p in main_theme.findall('.//path')
                            if p.get('ifSubset') == 'gamelist-view-artwork:boxart'))
        window = read('es-core/src/Window.cpp')
        self.assertIn('imagePath, false, bindable', window)
        self.assertIn('mSplash->update(customText);', window)
        self.assertIn('element.properties[name + "_binding"] = path;', schema)
        self.assertIn('mBindingExpressions[Utils::String::replace(prop.first, "_binding", "")] = prop.second.s;', read('es-core/src/GuiComponent.cpp'))
        image = read('es-core/src/components/ImageComponent.cpp')
        self.assertIn('setImage(value.s);', image)
        self.assertIn('mTexture.reset();', image)


if __name__ == '__main__':
    unittest.main()

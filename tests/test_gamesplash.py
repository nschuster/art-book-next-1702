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
    variables, elements, includes = {'themePath': str(ROOT)}, {}, []

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

    def test_logo_replaces_runtime_scraped_image_and_missing_art_stays_blank(self):
        _, elements, _ = resolve_launch()
        image = elements['image', 'background']
        self.assertEqual(image['path'], '{game:marquee}')
        self.assertNotIn('default', image)  # no screenshot substitution
        self.assertNotIn('minSize', image)
        self.assertNotIn('size', image)
        self.assertEqual(image['roundCorners'], '0')
        for logo in ['/media/logo.png', '', '/missing/logo.png']:
            initial_image = '/media/screenshot.png'
            selected = image.get('path', initial_image)
            bound = selected.replace('{game:marquee}', logo)
            self.assertEqual(bound, logo)
            self.assertNotEqual(bound, initial_image)

    def test_4_3_bounds_and_aspect_fit(self):
        _, elements, _ = resolve_launch()
        image, label = elements['image', 'background'], elements['text', 'label']
        pair = lambda p: tuple(map(float, p.split()))
        self.assertEqual(pair(image['origin']), (.5, .5))
        self.assertEqual(pair(image['pos']), (.5, .37))
        self.assertEqual(pair(image['maxSize']), (.78, .40))
        self.assertEqual(pair(label['origin']), (.5, .5))
        self.assertEqual(pair(label['pos']), (.5, .37))
        self.assertEqual(pair(label['size']), (.84, .16))
        self.assertEqual(label['multiLine'], 'true')
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
                self.assertGreaterEqual(.37*h-ah/2, .05*h)
                self.assertLessEqual(.37*h+ah/2, .57*h + 1e-6)
            self.assertGreaterEqual(int(h*float(label['fontSize'])), 12)

    def test_missing_logo_title_uses_native_exists_not_empty_only(self):
        _, elements, _ = resolve_launch()
        self.assertEqual(elements['text', 'label'].get('visible'), '!exists( {game:marquee} )')

    def test_hardware_uses_source_system_not_collection_or_wordmark(self):
        _, elements, _ = resolve_launch()
        self.assertIn(('image', 'launchHardware'), elements)
        hardware = elements['image', 'launchHardware']
        self.assertEqual(hardware['path'], '"'+str(ROOT)+'/_inc/launch-hardware/" + {game:system:name} + ".svg"')
        self.assertEqual(hardware['maxSize'], '0.36 0.22')
        self.assertEqual(hardware['pos'], '0.5 0.73')
        self.assertNotIn('default', hardware)
        self.assertNotIn('opacity', hardware)  # Splash overwrites this every frame
        import json
        manifest = ROOT / '_inc/launch-hardware/manifest.json'
        self.assertTrue(manifest.is_file())
        data = json.loads(manifest.read_text())
        self.assertEqual(data['license_status'], 'unresolved; redistribution not cleared')
        self.assertEqual(data['publication_status'], 'local unpublished candidate')
        mapping = data['systems']
        self.assertGreaterEqual(len(mapping), 20)
        self.assertNotIn('ports', mapping)
        self.assertNotIn('auto-allgames', mapping)
        self.assertFalse((manifest.parent / '_default.svg').exists())
        import hashlib
        self.assertEqual(set(p.stem for p in manifest.parent.glob('*.svg')), set(mapping))
        for unsupported in ['3ds', 'n3ds', 'nds', 'switch', 'wiiu', 'psvita', 'ps2', 'psp', 'gc', 'wii', 'mame', 'fbneo']:
            self.assertNotIn(unsupported, mapping)
        self.assertIn('controller', mapping['snes']['depiction'].lower())
        for system, entry in mapping.items():
            asset = manifest.parent / (system+'.svg')
            self.assertEqual(hashlib.sha256(asset.read_bytes()).hexdigest(), entry['asset_sha256'])
            self.assertRegex(entry['source_sha256'], r'^[0-9a-f]{64}$')
            self.assertTrue(entry['source_path'].endswith('/controller.svg'))
            svg = ET.parse(asset).getroot()
            self.assertEqual(svg.get('viewBox'), entry['viewBox'])
            self.assertEqual(svg.get('opacity'), '0.45')
            self.assertFalse(svg.findall('.//{*}image'))
            for node in svg.iter():
                for color in re.findall(r'(?:fill|stroke):([^;]+)', node.get('style', '')):
                    self.assertIn(color, ['#ffffff', 'none'])
        for alias, target in data['aliases'].items():
            self.assertEqual((manifest.parent/(alias+'.svg')).read_bytes(), (manifest.parent/(target+'.svg')).read_bytes())

    def test_eudora_archive_geometry_and_source_checksums_when_available(self):
        import hashlib
        import json
        import zipfile
        archive = Path(os.environ.get('EUDORA_ARCHIVE', '/root/.hermes/cache/documents/doc_a34c2139f583_recalbox-themes-master-themes-eudora.zip'))
        if not archive.exists():
            self.skipTest('Set EUDORA_ARCHIVE to supplied source archive for source fidelity check')
        folder = ROOT / '_inc/launch-hardware'
        data = json.loads((folder/'manifest.json').read_text())
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), data['archive_sha256'])
        with zipfile.ZipFile(archive) as source:
            expected = {p.split('/')[-2] for p in source.namelist() if p.endswith('/controller.svg')} - set(data['excluded_source_ids'])
            self.assertEqual(set(data['systems']) - set(data['aliases']), expected)
            for system, entry in data['systems'].items():
                raw = source.read(entry['source_path'])
                self.assertEqual(hashlib.sha256(raw).hexdigest(), entry['source_sha256'])
                original = ET.fromstring(raw)
                actual = ET.parse(folder/(system+'.svg')).getroot()
                # Every node, geometry attribute, transform and text survives;
                # only fill/stroke colors and root opacity may differ.
                def geometry(root):
                    return [(n.tag, {k:v for k,v in n.attrib.items() if k not in ('fill','stroke','style','opacity')}, n.text) for n in root.iter()]
                self.assertEqual(geometry(actual), geometry(original), system)
                for old, new in zip(original.iter(), actual.iter()):
                    old_style = re.sub(r'((?:fill|stroke):)#[0-9a-fA-F]+', r'\1#ffffff', old.get('style', ''))
                    self.assertEqual(new.get('style', ''), old_style, system)

    def test_native_expression_execution_when_probe_is_available(self):
        probe = os.environ.get('BATOCERA_LAUNCH_EXPR_PROBE')
        if not probe:
            self.skipTest('Set BATOCERA_LAUNCH_EXPR_PROBE to pinned MathExpr harness')
        _, elements, _ = resolve_launch()
        expression = elements['text', 'label']['visible']
        # BindingManager quotes Path values, including empty strings; Null is bare.
        for binding, expected in [('"'+str(ROOT/'_inc/launch-hardware/snes.svg')+'"', '0'),
                                  ('"/missing/launch/logo.png"', '1'), ('""', '1'), ('', '1')]:
            actual = subprocess.check_output([probe, expression.replace('{game:marquee}', binding)], text=True).strip()
            self.assertEqual(actual, expected, binding)
        hardware = elements['image', 'launchHardware']['path']
        for system in ['snes', 'c64', 'unknown-system', 'ports']:
            actual = subprocess.check_output([probe, hardware.replace('{game:system:name}', '"'+system+'"')], text=True).strip()
            self.assertEqual(actual, str(ROOT/'_inc/launch-hardware'/(system+'.svg')))

    def test_only_native_builtins_and_hardware_no_fake_progress(self):
        root = ET.parse(ROOT / 'gamesplash.xml').getroot()
        self.assertEqual(root.findtext('formatVersion'), '7')
        self.assertEqual([v.get('name') for v in root.findall('view')], ['splash'])
        _, elements, _ = resolve_launch()
        self.assertEqual(set(elements), {('splash','splash'), ('image','background'), ('text','label'), ('image','progressbar'), ('image','progressbar:active'), ('image','launchHardware'), ('text','launchStatus')})
        for name in ['progressbar', 'progressbar:active']:
            self.assertEqual(elements['image', name]['visible'], 'false')
        self.assertEqual([n.get('name') for n in root.findall('.//*[@extra]')], ['launchHardware', 'launchStatus'])

    def test_static_loading_status(self):
        from PIL import ImageFont
        for palette in PALETTES:
            variables, elements, _ = resolve_launch(palette)
            status = elements['text', 'launchStatus']
            self.assertEqual(status['text'], 'LOADING…')
            self.assertEqual(status['color'], variables['gamelistListDescriptionColor'])
            self.assertEqual(status['pos'], '0.5 0.89')
            self.assertEqual(status['origin'], '0.5 0.5')
            self.assertEqual(status['size'], '0.6 0.06')
            self.assertEqual(status['alignment'], 'center')
            self.assertEqual(status['visible'], 'true')
            for w, h in [(640,480), (320,240)]:
                font = ImageFont.truetype(str(ROOT/status['fontPath']), int(int(h*float(status['fontSize']))*1.31))
                box = font.getbbox(status['text'])
                self.assertLess(box[2]-box[0], .6*w)
                self.assertLessEqual(box[3]-box[1], .06*h)
                self.assertGreater(.89-.06/2, .73+.22/2)
                self.assertLess(.89+.06/2, .95)

    def test_existing_runtime_xml_unchanged(self):
        paths = subprocess.check_output(['git','ls-tree','-r','--name-only','2a93d44'], cwd=ROOT, text=True).splitlines()
        for path in paths:
            if path.endswith('.xml') and not path.startswith(('previews/', 'tests/')):
                old = subprocess.check_output(['git','show', '2a93d44:'+path], cwd=ROOT)
                if path == 'theme.xml':
                    from test_c64 import parse, structure
                    from test_controller_status import approved_controller_transform
                    expected = parse(old)
                    approved_controller_transform(expected)
                    from test_canvas_carousel import approved_canvas_transform
                    approved_canvas_transform(expected)
                    self.assertEqual(structure(parse((ROOT/path).read_bytes())), structure(expected), path)
                elif path == 'system-playtime.xml':
                    from test_c64 import parse, structure
                    from test_system_playtime import approved_hours_snapshot_transform
                    expected = parse(old)
                    approved_hours_snapshot_transform(expected)
                    self.assertEqual(structure(parse((ROOT/path).read_bytes())), structure(expected), path)
                else:
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
                if '{game:' in (prop.text or ''):
                    continue  # binding expressions checked separately
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
        self.assertIn('file->getMarqueePath()', filedata)
        self.assertIn('auto sys = getSourceFileData()->getSystem();', filedata)
        self.assertIn('return BindableProperty(sys);', filedata)
        self.assertIn('sys->getName()', read('es-app/src/SystemData.cpp'))
        binding = read('es-core/src/BindingManager.cpp')
        self.assertIn('root = value.bindable;', binding)
        self.assertIn('Utils::MathExpr::evaluate(evaluableExpression.c_str())', binding)
        self.assertIn('value = (ret.number != 0);', binding)
        self.assertIn('setVisible(value.b);', read('es-core/src/GuiComponent.cpp'))
        self.assertIn('"exists", 1', read('es-core/src/utils/MathExpr.cpp'))
        self.assertIn('mText.setText(text);', splash)
        self.assertIn('BindingManager::updateBindings(&mText, bindable);', splash)
        self.assertIn('BindingManager::updateBindings(extra, bindable);', splash)
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

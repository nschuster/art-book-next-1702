"""Additive palette contract against the approved layout revision."""
import re
import subprocess
import unittest
import xml.etree.ElementTree as ET
from test_metadata import ROOT

BASE = 'd3109da'


def original(path):
    return subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)


def parse(data):
    return ET.fromstring(re.sub(rb'&(?!#?\w+;)', b'&amp;', data),
                         parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))


def structure(node):
    # Preserve child ordering, attributes, meaningful text/tails and comments.
    return (node.tag, dict(node.attrib), (node.text or '').strip(),
            (node.tail or '').strip(), tuple(structure(c) for c in node))


def contrast(a, b):
    def luminance(s):
        rgb = [int(s[i:i+2], 16)/255 for i in (0, 2, 4)]
        return sum(w*(v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4)
                   for w, v in zip((.2126, .7152, .0722), rgb))
    lo, hi = sorted((luminance(a), luminance(b)))
    return (hi+.05)/(lo+.05)


class C64Tests(unittest.TestCase):
    def test_only_new_palette_and_registration_differ_from_approved_layout(self):
        for path in ('theme.xml', 'colors.xml'):
            root = parse((ROOT/path).read_bytes())
            parent = root.find("subset[@name='color-scheme']") if path == 'theme.xml' else root
            matches = parent.findall("include[@name='commodore-64']" if path == 'theme.xml'
                                     else "variables[@ifSubset='color-scheme:commodore-64']")
            self.assertEqual(len(matches), 1, path)
            parent.remove(matches[0])
            if path == 'theme.xml':
                # The separately tested opt-in RA registration is the only new
                # exception; test_ra_theme compares its full surrounding tree.
                ra = root.find("subset[@name='retroachievements-progress']")
                self.assertIsNotNone(ra)
                self.assertEqual([(n.get('name'), n.get('displayName')) for n in ra],
                                 [('off', 'Off'), ('on', 'On (sync helper required)')])
                root.remove(ra)
                inc = root.find("include[.='./retroachievements.xml']")
                self.assertIsNotNone(inc)
                self.assertEqual(inc.attrib, {'ifSubset': 'retroachievements-progress:on'})
                root.remove(inc)
                overlays = root.findall(".//textlist[@ifSubset='color-scheme:commodore-64']")
                self.assertEqual(len(overlays), 1)
                overlay = overlays[0]
                self.assertEqual(overlay.attrib, {'name': 'gamelist', 'ifSubset': 'color-scheme:commodore-64'})
                self.assertEqual({e.tag: e.text for e in overlay}, {
                    'selectorImagePath': './_inc/commodore-selector.svg', 'selectorColor': 'ffffff'})
                self.assertEqual(len(overlay), 2)
                for view in root.findall('view'):
                    if overlay in list(view): view.remove(overlay)
            self.assertEqual(structure(root), structure(parse(original(path))), path)


    def test_approved_layout_allows_only_requested_metadata_reorder(self):
        expected = parse(original('aspect-ratio-4-3.xml'))
        # Transform only the six named final overrides, then compare the entire
        # ordered tree including media, comments, attributes and other properties.
        changes = [
            ('image', 'game-players-icon', '0.55 0.64', '0.55 0.76'),
            ('text', 'md_players', '0.59 0.64', '0.59 0.76'),
            ('image', 'game-gametime-icon', '0.55 0.70', '0.55 0.64'),
            ('text', 'md_gametime', '0.59 0.70', '0.59 0.64'),
            ('image', 'game-lastplayed-icon', '0.55 0.76', '0.55 0.70'),
            ('datetime', 'md_lastplayed', '0.59 0.76', '0.59 0.70'),
        ]
        for kind, name, old, new in changes:
            nodes = expected.findall(f"./view/{kind}[@name='{name}'][pos]")
            self.assertEqual(len(nodes), 1, name)
            node = nodes[0]
            self.assertEqual(node.findtext('pos'), old)
            node.find('pos').text = new
            if name == 'md_players':
                self.assertEqual(node.findtext('size'), '0.16 0.045833333333333')
                node.find('size').text = '0.36 0.045833333333333'
            elif name == 'md_gametime':
                self.assertIsNone(node.find('size'))
                ET.SubElement(node, 'size').text = '0.16 0.045833333333333'
        self.assertEqual(structure(parse((ROOT/'aspect-ratio-4-3.xml').read_bytes())),
                         structure(expected))

    def test_registration_is_opt_in_and_has_exact_label(self):
        subset = parse((ROOT/'theme.xml').read_bytes()).find("subset[@name='color-scheme']")
        self.assertEqual(subset[0].get('name'), 'default')
        entry = subset.find("include[@name='commodore-64']")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.attrib, {'name': 'commodore-64', 'displayName': 'Commodore 64'})
        self.assertEqual(len(entry), 0)
        self.assertFalse((entry.text or '').strip())

    def test_complete_opaque_hardware_palette_and_contrast(self):
        root = parse((ROOT/'colors.xml').read_bytes())
        entry = root.find("variables[@ifSubset='color-scheme:commodore-64']")
        self.assertIsNotNone(entry)
        values = {e.tag: e.text.strip() for e in entry if isinstance(e.tag, str)}
        default = root.find("variables[@ifSubset='color-scheme:default|custom']")
        self.assertEqual(set(values), {e.tag for e in default if isinstance(e.tag, str)})
        self.assertEqual(len(values), len([e for e in entry if isinstance(e.tag, str)]))
        self.assertEqual(values['systemArtSaturation'], '1')
        for key, value in values.items():
            if key != 'systemArtSaturation':
                self.assertRegex(value, r'^[0-9a-fA-F]{6}$', key)
        self.assertEqual(values['gamelistListBackgroundColor'], 'd8cfb6')
        self.assertEqual(values['gamelistListMetadataColor'], '3b3028')
        self.assertEqual(values['gamelistListTextlistBackgroundColor'], '302b26')
        self.assertEqual(values['gamelistListTextlistUnselectedColor'], 'e9e1cc')
        self.assertEqual(values['gamelistListTextlistSelectedColor'], 'f1c879')
        self.assertEqual(values['helpBackgroundColor'], '292929')
        self.assertEqual(values['helpIconColor'], 'c2beb4')
        for fg, bg in [
            ('gamelistListMetadataColor', 'gamelistListBackgroundColor'),
            ('gamelistListMetadataIconColor', 'gamelistListBackgroundColor'),
            ('gamelistListRatingColor', 'gamelistListBackgroundColor'),
            ('gamelistListTextlistSelectedColor', 'gamelistListTextlistBackgroundColor'),
            ('gamelistListTextlistUnselectedColor', 'gamelistListTextlistBackgroundColor'),
            ('helpTextColor', 'helpBackgroundColor'), ('helpIconColor', 'helpBackgroundColor'),
            ('splashProgressBarTextColor', 'splashBackgroundColor')]:
            self.assertGreaterEqual(contrast(values[fg], values[bg]), 4.5, fg)
        # Existing menu foreground is white; selector must not wash it out.
        for bg in ('menuBackgroundColor', 'menuSelectorColor'):
            self.assertGreaterEqual(contrast('ffffff', values[bg]), 4.5)
        self.assertNotEqual(values['gamelistListTextlistSelectedColor'], values['gamelistListTextlistUnselectedColor'])

    def test_existing_line_endings_preserved(self):
        for path in ('colors.xml', 'theme.xml'):
            old, new = original(path), (ROOT/path).read_bytes()
            if b'\r\n' in old:
                self.assertNotIn(b'\n', new.replace(b'\r\n', b''), path)
            else:
                self.assertNotIn(b'\r\n', new, path)
            self.assertEqual(old.endswith(b'\n'), new.endswith(b'\n'))

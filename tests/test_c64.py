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
            self.assertEqual(structure(root), structure(parse(original(path))), path)
        self.assertEqual((ROOT/'aspect-ratio-4-3.xml').read_bytes(), original('aspect-ratio-4-3.xml'))

    def test_registration_is_opt_in_and_has_exact_label(self):
        subset = parse((ROOT/'theme.xml').read_bytes()).find("subset[@name='color-scheme']")
        self.assertEqual(subset[0].get('name'), 'default')
        entry = subset.find("include[@name='commodore-64']")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.attrib, {'name': 'commodore-64', 'displayName': 'Commodore 64'})
        self.assertEqual(len(entry), 0)
        self.assertFalse((entry.text or '').strip())

    def test_complete_opaque_blue_palette_and_contrast(self):
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
        self.assertEqual(values['gamelistListBackgroundColor'], '40318d')
        self.assertEqual(values['gamelistListMetadataColor'], 'b8b0ff')
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

"""Targeted format-7 resolver, not an EmulationStation renderer.
Run: python -m unittest discover -s tests -v
Baseline must remain available in git history (the fork's upstream parent).
"""
import itertools
from pathlib import Path
import re
import subprocess
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = '9a50ef366e750aabfab29e6915a2867607212971'


def source(path, baseline=False):
    if baseline:
        return subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)
    return (ROOT / path).read_bytes()


def resolve(ratio='4-3', metadata='mixed', help=True, font='default', artwork='image', view='detailed', baseline=False):
    options = {'aspect-ratio': ratio, 'gamelist-view-metadata': metadata,
               'font-size': font, 'gamelist-view-artwork': artwork,
               'system-view-artwork': 'default', 'system-logos': 'default',
               'fonts': 'default', 'color-scheme': 'default', 'distribution': 'batocera'}
    result = {}

    def active(node):
        if 'ifHelpPrompts' in node.attrib and (node.get('ifHelpPrompts') == 'true') != help:
            return False
        for clause in node.get('ifSubset', '').split(','):
            if not clause:
                continue
            key, values = clause.strip().split(':')
            if options.get(key) not in values.split('|'):
                return False
        return True

    def component(node):
        props = {p.tag: (p.text or '').strip() for p in node if active(p) and not p.get('name')}
        children = [(p.tag, p.get('name'), component(p)) for p in node if active(p) and p.get('name')]
        if children:
            props['children'] = children
        return props

    def load(path):
        # Upstream uses bare ampersands, tolerated by pugixml (not strict ET).
        xml = re.sub(rb'&(?!#?\w+;)', b'&amp;', source(path, baseline))
        for node in ET.fromstring(xml):
            if not active(node):
                continue
            if node.tag == 'include' and node.text and '${' not in node.text:
                load(node.text.strip().removeprefix('./'))
            if node.tag != 'view' or view not in re.split(r'[\s,]+', node.get('name', '')):
                continue
            for elem in node:
                if not active(elem):
                    continue
                for name in re.split(r'[\s,]+', elem.get('name', '').strip()):
                    if name:
                        result.setdefault((elem.tag, name), {}).update(component(elem))
    load('theme.xml')
    return result


class MetadataTests(unittest.TestCase):
    # Pair/description assertions were intentionally superseded by
    # test_all_metadata.py: enabled help-off modes now also show all nine fields.
    def test_metadata_off_help_off_is_identical_to_upstream(self):
        for ratio, font in itertools.product(['4-3', '4-3-auto'], ['small', 'default', 'large', 'xlarge']):
            self.assertEqual(resolve(ratio, metadata='off', help=False, font=font),
                             resolve(ratio, metadata='off', help=False, font=font, baseline=True))

    def test_off_and_basic_system_views_are_unchanged(self):
        for help in [True, False]:
            self.assertEqual(resolve(metadata='off', help=help), resolve(metadata='off', help=help, baseline=True))
            for view in ['basic', 'system']:
                self.assertEqual(resolve(view=view, help=help), resolve(view=view, help=help, baseline=True))

    def test_other_ratios_and_shared_theme_byte_identical(self):
        # Palette/theme preservation is checked structurally against d3109da
        # in test_c64.py; all other upstream byte guards remain unchanged.
        for path in ['fonts.xml', 'splash.xml', 'aspect-ratio-16-9.xml',
                     'aspect-ratio-16-10.xml', 'aspect-ratio-3-2.xml', 'aspect-ratio-1-1.xml']:
            self.assertEqual(source(path), source(path, True), path)



if __name__ == '__main__':
    unittest.main()

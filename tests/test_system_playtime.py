"""Independent system total; full ordered include resolver, not native rendering."""
import itertools
import subprocess
import unittest
import xml.etree.ElementTree as ET
from test_metadata import ROOT, resolve
from test_c64 import parse, structure

EXPRESSION = 'Playtime unavailable'  # Generated include replaces only text, not geometry.
REGISTRATION = '<subset name="system-playtime" displayName="System Playtime"><include name="off" displayName="Off" /><include name="on" displayName="On" /></subset>'
INCLUDE = '<include ifSubset="system-playtime:on">./system-playtime.xml</include>'

def approved_hours_snapshot_transform(root):
    """Only replace the native timecode text and add the generated text include."""
    target = root.find("view/text[@name='system-playtime']")
    target.find('text').text = 'Playtime unavailable'
    for child in target:
        if child.tag is ET.Comment:
            child.text = ' Saved full-gamelist total; unavailable until independent helper refresh. '
    root.append(ET.fromstring('<include>/userdata/system/configs/art-book-next-system-playtime/${system.name}.xml</include>'))


def approved_system_playtime_transform(root):
    """Add exactly the approved two nodes to older preservation baselines."""
    count = root.find("subset[@name='system-count']")
    root.insert(list(root).index(count)+1, ET.fromstring(REGISTRATION))
    root.append(ET.fromstring(INCLUDE))

class SystemPlaytimeTests(unittest.TestCase):
    def test_opt_in_and_preservation(self):
        actual = parse((ROOT/'theme.xml').read_bytes())
        # Pin the pre-feature baseline: HEAD already contains these additions
        # after publication, so applying the transforms to HEAD duplicates them.
        baseline = parse(subprocess.check_output(['git','show','596c30d:theme.xml'],cwd=ROOT))
        approved_system_playtime_transform(baseline)
        from test_menu_fonts import approved_menu_transform
        approved_menu_transform(baseline)
        from test_controller_status import approved_controller_transform
        approved_controller_transform(baseline)
        from test_canvas_carousel import approved_canvas_transform
        approved_canvas_transform(baseline)
        self.assertEqual(structure(actual), structure(baseline))

    def test_independent_count_full_include_graph(self):
        for ratio, count, help_on, font in itertools.product(
            ['4-3','4-3-auto','16-9','16-9-auto','16-10','3-2','1-1','720-square-auto'],
            ['off','on'], [False,True], ['small','default','large','xlarge']):
            kw=dict(view='system',ratio=ratio,system_count=count,help=help_on,font=font)
            off=resolve(**kw)
            on=resolve(**kw,system_playtime='on')
            self.assertIn(('text','system-playtime'),on)
            p=on.pop(('text','system-playtime'))
            self.assertEqual(on,off)
            self.assertEqual(p['text'],EXPRESSION)
            self.assertEqual(p['emptyTextDefaults'],'false')
            self.assertEqual(p['pos'],'0.5 0.85')
            self.assertEqual(p['origin'],'0.5 0.5')
            self.assertEqual(p['size'],'0.9 0.05')
            self.assertLess(.85+.05/2,1-.114583333333333)
            if count=='on':
                c=on['text','system-count']
                self.assertEqual(c['pos'],'0.5 0.78')
                for key in ['fontPath','fontSize','color','alignment']:
                    self.assertEqual(p[key],c[key])
                self.assertGreater(.85-.025,.78+.025)

    def test_non_system_views_unchanged(self):
        for view in ['basic','detailed']:
            self.assertEqual(resolve(view=view),resolve(view=view,system_playtime='on'))

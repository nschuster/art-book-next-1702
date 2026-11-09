"""Independent system total; full ordered include resolver, not native rendering."""
import itertools
import subprocess
import unittest
import xml.etree.ElementTree as ET
from test_metadata import ROOT, resolve
from test_c64 import parse, structure

EXPRESSION = 'empty( {system:gameTime} ) ? "00:00" : {system:gameTime}'
REGISTRATION = '<subset name="system-playtime" displayName="System Playtime"><include name="off" displayName="Off" /><include name="on" displayName="On" /></subset>'
INCLUDE = '<include ifSubset="system-playtime:on">./system-playtime.xml</include>'

def approved_system_playtime_transform(root):
    """Add exactly the approved two nodes to older preservation baselines."""
    count = root.find("subset[@name='system-count']")
    root.insert(list(root).index(count)+1, ET.fromstring(REGISTRATION))
    root.append(ET.fromstring(INCLUDE))

class SystemPlaytimeTests(unittest.TestCase):
    def test_opt_in_and_preservation(self):
        actual = parse((ROOT/'theme.xml').read_bytes())
        baseline = parse(subprocess.check_output(['git','show','HEAD:theme.xml'],cwd=ROOT))
        approved_system_playtime_transform(baseline)
        from test_menu_fonts import approved_menu_transform
        approved_menu_transform(baseline)
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

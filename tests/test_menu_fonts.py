"""Stock Batocera 42 menu-font contract; semantic tests, not GUI captures."""
import itertools
import os
from pathlib import Path
import subprocess
import unittest
import xml.etree.ElementTree as ET
from test_metadata import ROOT, resolve

REGISTRATION = '''<subset name="menu-font-size" displayName="Menu Font Size">
<include name="default" displayName="Default" />
<include name="large" displayName="Large" />
<include name="xlarge" displayName="Extra Large" />
</subset>'''

def approved_menu_transform(root):
    root.append(ET.fromstring(REGISTRATION))
    ET.SubElement(root, 'include').text = './menu-font-size.xml'

class MenuFontTests(unittest.TestCase):
    def test_registration_and_final_include(self):
        from test_c64 import parse, structure
        root = parse((ROOT/'theme.xml').read_bytes())
        self.assertEqual(structure(root.find("subset[@name='menu-font-size']")),
                         structure(ET.fromstring(REGISTRATION)))
        self.assertEqual(root[-1].tag, 'include')
        self.assertEqual(root[-1].text.strip(), './menu-font-size.xml')

    def test_real_include_resolution_and_nonmenu_preservation(self):
        for font, ratio in itertools.product(['small','default','large','xlarge'], ['4-3','4-3-auto','16-9']):
            for choice in ['default','large','xlarge']:
                for view in ['system','basic','detailed']:
                    self.assertEqual(resolve(font=font,ratio=ratio,view=view,menu_font=choice),
                                     resolve(font=font,ratio=ratio,view=view))
                menu=resolve(font=font,ratio=ratio,view='menu',menu_font=choice)
                if choice == 'default':
                    self.assertEqual(menu, resolve(font=font,ratio=ratio,view='menu',baseline=True))
                if choice != 'default':
                    expected = {'large': ('0.04166667','0.03333334'),
                                'xlarge': ('0.05','0.04166667')}[choice]
                    self.assertEqual(menu['menuText','menutext']['fontSize'],expected[0])
                    self.assertEqual(menu['menuTextSmall','menutextsmall']['fontSize'],expected[1])

    def test_default_noop_and_only_supported_font_properties(self):
        root=ET.parse(ROOT/'menu-font-size.xml').getroot()
        self.assertEqual(len(root),2)
        for view, choice in zip(root,['large','xlarge']):
            self.assertEqual(view.attrib,{'name':'menu','ifSubset':'menu-font-size:'+choice})
            self.assertEqual([(e.tag,e.get('name')) for e in view],
                [('menuText','menutitle'),('menuText','menufooter'),('menuText','menutext'),
                 ('menuTextSmall','menutextsmall'),('menuGroup','menugroup')])
            for e in view:
                self.assertEqual([p.tag for p in e],['fontSize'])
                self.assertLessEqual(int(480*float(e[0].text))*1.31,32)

    def test_pinned_runtime_and_schema(self):
        source=Path(os.environ.get('BATOCERA_ES_SOURCE','/tmp/ra-es-source'))
        if not (source/'.git').exists(): self.skipTest('Set BATOCERA_ES_SOURCE to pinned ES checkout')
        pin='4adf26b43900d1a33887af6d8af3da2e99e398a5'
        def read(p): return subprocess.check_output(['git','show',pin+':'+p],cwd=source,text=True)
        schema=read('es-core/src/ThemeData.cpp')
        for kind,name in [('menuText','menutext'),('menuTextSmall','menutextsmall'),('menuGroup','menugroup')]:
            self.assertIn('"'+kind+'", {',schema.replace(',{',', {'))
            self.assertIn('getElement("menu", "'+name+'", "'+kind+'")',schema)
        for filename in ['GuiRetroAchievements.cpp','GuiGameAchievements.cpp']:
            text=read('es-app/src/guis/'+filename)
            self.assertIn('ThemeData::getMenuTheme()',text)
            self.assertIn('theme->TextSmall.font',text)
            self.assertIn('theme->Text.font',text)
            self.assertNotIn('Font::get(FONT_SIZE',text)
        self.assertIn('${menu.text.font.size}',read('es-app/src/guis/GuiRetroAchievements.cpp'))
        self.assertIn('menuFontScale()',read('es-core/src/resources/Font.cpp'))

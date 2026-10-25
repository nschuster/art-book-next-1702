"""Optional RA integration must not change the approved theme when disabled."""
import subprocess
import unittest
from test_c64 import parse, structure
from test_metadata import ROOT

class AchievementThemeTests(unittest.TestCase):
    def test_resolved_overlay_changes_only_extras_and_date_width(self):
        from test_metadata import resolve
        import itertools
        for ratio, metadata, help_on, artwork, view in itertools.product(
                ['4-3', '4-3-auto', '16-9', '1-1'],
                ['on', 'mixed', 'play-stats', 'off'], [True, False],
                ['image', 'image-cropped', 'boxart', 'logo'], ['detailed', 'basic', 'system']):
            kw=dict(ratio=ratio, metadata=metadata, help=help_on, artwork=artwork, view=view)
            off=resolve(**kw)
            on=resolve(**kw, achievements='on')
            if ratio in ['4-3','4-3-auto'] and metadata != 'off' and view == 'detailed':
                self.assertIn(('gameextras','gameextras'),on)
                del on[('gameextras','gameextras')]
                self.assertEqual(on[('datetime','md_lastplayed')]['size'], '0.18 0.045833333333333')
                on[('datetime','md_lastplayed')]['size']=off[('datetime','md_lastplayed')]['size']
                for key, changes in {('image','game-players-icon'):{'pos':'0.78 0.70'}, ('text','md_players'):{'pos':'0.82 0.70','size':'0.13 0.045833333333333'}, ('image','game-genre-icon'):{'pos':'0.55 0.76'}, ('text','md_genre'):{'pos':'0.59 0.76'}}.items():
                    for prop, value in changes.items():
                        self.assertEqual(on[key][prop], value)
                        on[key][prop]=off[key][prop]
            self.assertEqual(on,off,kw)

    def test_opt_in_registration_and_exact_integration(self):
        root = parse((ROOT/'theme.xml').read_bytes())
        subset = root.find("subset[@name='retroachievements-progress']")
        self.assertIsNotNone(subset, 'Achievement progress option is missing')
        self.assertEqual(subset.attrib, {'name':'retroachievements-progress','displayName':'Achievement Progress'})
        self.assertEqual([(n.get('name'),n.get('displayName')) for n in subset], [('off','Off'),('on','On (sync helper required)')])
        root.remove(subset)
        include = root.find("include[.='./retroachievements.xml']")
        self.assertIsNotNone(include)
        self.assertEqual(include.attrib, {'ifSubset':'retroachievements-progress:on'})
        root.remove(include)
        baseline=parse(subprocess.check_output(['git','show','777618c:theme.xml'],cwd=ROOT))
        from test_oled import approved_oled_transform
        approved_oled_transform(baseline, 'theme.xml')
        self.assertEqual(structure(root), structure(baseline))

    def test_overlay_is_scoped_and_preserves_media(self):
        path=ROOT/'retroachievements.xml'
        self.assertTrue(path.exists(), 'Achievement integration XML missing')
        root=parse(path.read_bytes())
        self.assertEqual(root.attrib, {})
        view=root.find('view')
        self.assertEqual(view.attrib, {'name':'detailed','ifSubset':'aspect-ratio:4-3|4-3-auto'})
        self.assertEqual([e.tag for e in view], ['gameextras','datetime','image','text','image','text'])
        self.assertEqual(view[0].attrib, {'name':'gameextras','ifSubset':'gamelist-view-metadata:on|mixed|play-stats'})
        self.assertEqual(view[0].findtext('path'), '/userdata/system/retroachievements/extras/${system.name}/')
        self.assertEqual(view[1].attrib, {'name':'md_lastplayed','ifSubset':'gamelist-view-metadata:on|mixed|play-stats'})
        self.assertEqual(view[1].findtext('size'), '0.18 0.045833333333333')

if __name__ == '__main__': unittest.main()

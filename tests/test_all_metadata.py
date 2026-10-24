"""Icon-based 4:3 metadata; original media geometry is an invariant."""
import itertools
import unittest
from test_metadata import resolve

FIELDS=[('datetime','releasedate'),('rating','rating'),('text','players'),('text','genre'),('text','gametime'),('text','playcount'),('datetime','lastplayed')]

class MetadataStyleTests(unittest.TestCase):
    def test_media_and_list_are_exactly_original(self):
        for help,art,mode in itertools.product([True,False],['image','image-cropped','boxart','logo'],['on','mixed','play-stats','off']):
            with self.subTest(help=help,art=art,mode=mode):
                old=resolve(metadata=mode,help=help,artwork=art,baseline=True)
                new=resolve(metadata=mode,help=help,artwork=art)
                for key in [('image','game-artwork'),('video','game-video'),('image','game-logo'),('textlist','gamelist'),('image','logo')]:
                    self.assertEqual(new.get(key),old.get(key),key)

    def test_seven_fields_no_description_or_table_labels(self):
        for ratio,help,font,mode in itertools.product(['4-3','4-3-auto'],[True,False],['small','default','large','xlarge'],['on','mixed','play-stats']):
            state=resolve(ratio=ratio,metadata=mode,help=help,font=font)
            for kind,field in FIELDS:
                name='game-gametime-totalhours' if field=='gametime' else 'md_'+field
                self.assertEqual(state[kind,name]['visible'],'true')
                if field=='gametime':self.assertEqual(state[kind,'md_'+field]['visible'],'false')
                self.assertEqual(state['text','md_lbl_'+field]['visible'],'false')
            for name in ['md_developer','md_publisher','md_lbl_developer','md_lbl_publisher','md_description','game-description','game-gametime-formatted']:
                self.assertEqual(state['text',name]['visible'],'false')
            self.assertEqual(state['stackpanel','gamedata']['visible'],'false')

    def test_original_metadata_assets_and_palette(self):
        state=resolve()
        for name in ['releasedate','players','gametime','playcount','lastplayed','genre']:
            icon=state['image','game-'+name+'-icon']
            self.assertEqual(icon['visible'],'true')
            self.assertEqual(icon['path'],'./_inc/images/metadata-icon-'+name+'.svg')
            self.assertEqual(icon['color'],'${gamelistListMetadataIconColor}')
        for kind,name in FIELDS:
            p=state[kind,'md_'+name]
            if kind!='rating':
                self.assertEqual(p['fontPath'],'${fontBold}')
                self.assertEqual(p['color'],'${gamelistListMetadataColor}')
            else:
                self.assertEqual(p['filledPath'],'./_inc/images/metadata-icon-star-filled.svg')
                self.assertEqual(p['color'],'${gamelistListRatingColor}')

    def test_players_directly_above_genre_and_play_time_shares_count_row(self):
        for ratio, help, mode in itertools.product(['4-3', '4-3-auto'], [True, False], ['on', 'mixed', 'play-stats']):
            s = resolve(ratio=ratio, help=help, metadata=mode)
            for kind, name, y, width in [
                ('datetime', 'releasedate', .58, .19),
                ('text', 'gametime', .64, .16),
                ('datetime', 'lastplayed', .70, .36),
                ('text', 'players', .76, .36),
                ('text', 'genre', .82, .36),
                ('text', 'playcount', .64, .13),
            ]:
                with self.subTest(ratio=ratio, help=help, mode=mode, field=name):
                    x = .82 if name == 'playcount' else .59
                    ix = .78 if name == 'playcount' else .55
                    self.assertEqual(tuple(map(float, s[kind, 'md_'+name]['pos'].split())), (x, y))
                    self.assertEqual(tuple(map(float, s['image', 'game-'+name+'-icon']['pos'].split())), (ix, y))
                    self.assertEqual(float(s[kind, 'md_'+name]['size'].split()[0]), width)
            self.assertEqual(s['rating', 'md_rating']['pos'], '0.95 0.58')

    def test_metadata_inside_original_description_region(self):
        s=resolve()
        for kind,name in FIELDS:
            p=s[kind,'md_'+name];x,y=map(float,p['pos'].split());w,h=map(float,p['size'].split());ox,oy=map(float,p['origin'].split())
            if kind=='rating' and w==0:w=h*5*3/4
            self.assertGreaterEqual(x-w*ox,.54)
            self.assertGreater(y-h*oy,.541666666666667)
            self.assertLessEqual(x+w*(1-ox),.965)
            self.assertLessEqual(y+h*(1-oy),.86)

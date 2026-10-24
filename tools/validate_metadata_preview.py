"""Check sample icon-panel renders at 240p/480p, not native CRT output."""
from render_metadata_panel import render
FIELDS={'md_releasedate','md_rating','md_players','md_genre','md_gametime','md_playcount','md_lastplayed'}
for scheme in ['default', 'commodore-64']:
    for h in [240,480]:
        im,records=render(h, scheme)
        assert {n for n in records if n.startswith('md_')}==FIELDS-{'md_gametime'}
        assert records['game-gametime-totalhours']['display']=='2h 35m'
        for n,p in records.items():
            if 'text' in p:assert p['text']==p['display'],(scheme,h,n,p)
            x,y,w,hh=p['bounds']
            assert x>=im.width*.54 and x+w<=im.width*.965+1,(scheme,h,n,p)
            assert y>=h*.5416666 and y+hh<h*.86,(scheme,h,n,p)
        names=list(records)
        for i,a in enumerate(names):
            ax,ay,aw,ah=records[a]['bounds']
            for b in names[i+1:]:
                bx,by,bw,bh=records[b]['bounds']
                assert min(ax+aw,bx+bw)<=max(ax,bx) or min(ay+ah,by+bh)<=max(ay,by),(scheme,h,a,b,'overlap')
print('Both palettes: seven sample values and six icons fit, without truncation/overlap, at 240p and 480p.')

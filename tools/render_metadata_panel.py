"""Render the candidate 4:3 metadata panel from resolved theme XML.
Static approximation, not native Batocera; sample game records. Requires Pillow
and CairoSVG. Run: python3 tools/render_metadata_panel.py
"""
from pathlib import Path
import re, io, json, xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont
import cairosvg
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'previews'/'original-style'
OPTIONS={'aspect-ratio':'4-3','gamelist-view-metadata':'mixed','font-size':'default','fonts':'default','color-scheme':'default','distribution':'batocera','gamelist-view-artwork':'image','system-view-artwork':'default','system-logos':'default'}
LABELS={'rating':'Rating:','releasedate':'Released:','developer':'Developer:','publisher':'Publisher:','genre':'Genre:','players':'Players:','gametime':'Game time:','playcount':'Times played:','lastplayed':'Last played:','favorite':'Favorite:'}
VALUES={'releasedate':'1994-03-19','developer':'Nintendo R&D1','publisher':'Nintendo','genre':'Action / Adventure','players':'1','gametime':'2 h 35 mn','playcount':'12','lastplayed':'2026-10-20','favorite':'Yes'}

def registered_schemes():
    """Use native registrations, including the user-editable Custom slot."""
    xml=re.sub(rb'&(?!#?\w+;)',b'&amp;', (ROOT/'theme.xml').read_bytes())
    subset=ET.fromstring(xml).find("subset[@name='color-scheme']")
    return {node.get('name'):node.get('displayName') for node in subset}


def resolve(scheme='default', custom_palette=None):
    if scheme not in registered_schemes():
        raise ValueError('Unregistered color scheme: '+scheme)
    # Explicit shipped Custom template, not a skipped /userdata include.
    custom_palette=Path(custom_palette) if custom_palette is not None else ROOT/'resources/customizations/colors.xml'
    options=dict(OPTIONS, **{'color-scheme':scheme})
    variables={'system.theme':'snes','system.name':'snes'};components={}
    def active(e):
        if e.get('ifHelpPrompts')=='false':return False
        for clause in e.get('ifSubset','').split(','):
            if clause:
                k,v=clause.split(':')
                if options.get(k) not in v.split('|'):return False
        return True
    def expand(s):
        for _ in range(5):s=re.sub(r'\$\{([^}]+)\}',lambda m:variables.get(m[1],m[0]),s)
        return s
    def load(path):
        xml=re.sub(rb'&(?!#?\w+;)',b'&amp;',path.read_bytes())
        for e in ET.fromstring(xml):
            if not active(e):continue
            if e.tag=='include' and e.text:
                p=expand(e.text.strip())
                if e.text.strip()=='${themeCustomizationsPath}colors.xml':
                    load(custom_palette)
                    continue
                if '${' not in p and (path.parent/p).exists():load(path.parent/p)
            if e.tag=='variables':
                for p in e:
                    if active(p):variables[p.tag]=expand((p.text or '').strip())
            if e.tag=='view' and 'detailed' in re.split(r'[\s,]+',e.get('name','')):
                for c in e:
                    if not active(c):continue
                    for name in re.split(r'[\s,]+',c.get('name','').strip()):
                        if not name:continue
                        props=components.setdefault((c.tag,name),{})
                        for p in c:
                            if active(p) and not p.get('name'):props[p.tag]=expand((p.text or '').strip())
    load(ROOT/'theme.xml')
    unresolved=[(key,prop,value) for key,props in components.items() for prop,value in props.items() if '${' in value]
    if unresolved:raise ValueError('Unresolved preview properties: '+repr(unresolved))
    return components,variables

def pair(s):return tuple(map(float,s.split()))
def xy(p,w,h):
    x,y=pair(p.get('pos','0 0'));return float(p.get('x',x))*w,float(p.get('y',y))*h

def wh(p,w,h):
    a,b=pair(p.get('size','0 0'));return float(p.get('w',a))*w,float(p.get('h',b))*h

def color(s,bg='222222'):
    s=s.lstrip('#');a=int(s[6:8],16)/255 if len(s)==8 else 1
    return tuple(round(x*a+y*(1-a)) for x,y in zip(bytes.fromhex(s[:6]),bytes.fromhex(bg)))

def font(p,h):
    size=max(1,int(int(float(p.get('fontSize','.03333333'))*h)*(1.5 if h==240 else 1.31)))
    path=p.get('fontPath','./_inc/fonts/Roboto-Bold.ttf')
    return ImageFont.truetype(str(ROOT/path),size)

def asset(path,bounds,tint=None):
    path=ROOT/path
    if path.suffix=='.svg':im=Image.open(io.BytesIO(cairosvg.svg2png(url=str(path)))).convert('RGBA')
    else:im=Image.open(path).convert('RGBA')
    im.thumbnail((max(1,round(bounds[0])),max(1,round(bounds[1]))),Image.Resampling.LANCZOS)
    if tint:
        rgb=tuple(bytes.fromhex(tint[:6]));a=int(tint[6:8],16) if len(tint)==8 else 255
        mask=im.getchannel('A').point([round(i*a/255) for i in range(256)])
        im=Image.new('RGBA',im.size,rgb+(0,));im.putalpha(mask)
    return im

def text(im,p,value,h,bg='222222'):
    w=im.width;x,y=xy(p,w,h);bw,bh=wh(p,w,h);f=font(p,h)
    if not bw:bw=f.getlength(value)
    if not bh:bh=sum(f.getmetrics())
    ox,oy=pair(p.get('origin','0 0'));x-=bw*ox;y-=bh*oy
    bw=max(1,round(bw));bh=max(1,round(bh));layer=Image.new('RGBA',(bw,bh));d=ImageDraw.Draw(layer)
    full=value
    if f.getlength(value)>bw:
        shortened=value
        while shortened and f.getlength(shortened+'...')>bw:shortened=shortened[:-1]
        value=shortened+'...'
    align=p.get('alignment','left');px=bw/2 if align=='center' else bw if align=='right' else 0
    anchor=('m' if align=='center' else 'r' if align=='right' else 'l')+'m'
    ink=p.get('color','ffffff')
    fill=tuple(bytes.fromhex(ink if len(ink)==8 else ink+'ff')) if bg is None else color(ink,bg)
    d.text((px,bh/2),value,font=f,anchor=anchor,fill=fill)
    im.alpha_composite(layer,(round(x),round(y)))
    return {'text':full,'display':value,'bounds':[round(x),round(y),bw,bh],'font_pixels':f.size}

def render(h, scheme='default'):
    state,v=resolve(scheme);w=round(h*4/3)
    assert state['text','game-description'].get('visible')=='false','Candidate must replace description'
    bg=state['image','background']['color']
    listbg=state['image','gamelist-background']['color']
    im=Image.new('RGBA',(w,h),'#'+bg);d=ImageDraw.Draw(im)
    p=state['image','gamelist-background'];x,y=xy(p,w,h);bw,bh=wh(p,w,h)
    d.rectangle((round(x),round(y),round(x+bw)-1,round(y+bh)-1),fill='#'+listbg)
    p=state['image','logo'];a,b=pair(p['maxSize']);logo=asset(p['path'],(a*w,b*h),p['color']);x,y=xy(p,w,h);im.alpha_composite(logo,(round(x-logo.width/2),round(y-logo.height/2)))
    p=state['textlist','gamelist'];x,y=xy(p,w,h);bw,bh=wh(p,w,h);f=font(p,h)
    layer=Image.new('RGBA',(round(bw),round(bh)));ld=ImageDraw.Draw(layer)
    if p.get('selectorImagePath'):
        # Native TextListComponent stretches the selector to list width × row height.
        # The image has a transparent body and a short rainbow underline only.
        row_height=bh/int(p['lines'])
        selector=Image.open(io.BytesIO(cairosvg.svg2png(
            url=str(ROOT/p['selectorImagePath']), output_width=round(bw),
            output_height=round(row_height)))).convert('RGBA')
        layer.alpha_composite(selector,(0,round(3*row_height)))
    for i,name in enumerate(['Donkey Kong Country','F-Zero','Mega Man X','Super Metroid','Super Mario World','Super Castlevania IV','The Legend of Zelda']):
        ld.text((0,(i+.5)*bh/int(p['lines'])),name,font=f,anchor='lm',fill=color(p['selectedColor' if i==3 else 'primaryColor'],listbg))
    im.alpha_composite(layer,(round(x),round(y)))
    p=state['image','game-artwork'];a,b=pair(p['maxSize']);shot=asset('previews/super-metroid.png',(a*w,b*h));x,y=xy(p,w,h);im.alpha_composite(shot,(round(x-shot.width/2),round(y-shot.height/2)))
    records={}
    for (kind,name),p in state.items():
        if p.get('visible')!='true':continue
        if kind=='image' and name.startswith('game-') and name.endswith('-icon'):
            a,b=pair(p['maxSize']);icon=asset(p['path'],(a*w,b*h),p['color'])
            x,y=xy(p,w,h);ox,oy=pair(p.get('origin','0 0'))
            im.alpha_composite(icon,(round(x-icon.width*ox),round(y-icon.height*oy)))
            records[name]={'asset':p['path'],'bounds':[x-icon.width*ox,y-icon.height*oy,icon.width,icon.height]}
        elif name.startswith('md_lbl_'):
            key=name.removeprefix('md_lbl_');records[name]=text(im,p,LABELS.get(key,key),h,bg)
        elif name.startswith('md_') and kind in ['text','datetime'] and name.removeprefix('md_') in VALUES:
            key=name.removeprefix('md_');records[name]=text(im,p,VALUES[key],h,bg)
        elif name=='md_rating' and kind=='rating':
            bw,bh=wh(p,w,h)
            if not bw:bw=bh*5
            x,y=xy(p,w,h);ox,oy=pair(p.get('origin','0 0'));x-=bw*ox;y-=bh*oy
            for i in range(5):
                path=p['filledPath' if i<4 else 'unfilledPath'];star=asset(path,(bw/5,bh),p['color']);im.alpha_composite(star,(round(x+i*bw/5),round(y)))
            records[name]={'bounds':[x,y,bw,bh],'sample_rating':.8}
    for key in ['releasedate','rating','players','genre','gametime','playcount','lastplayed']:
        assert 'md_'+key in records,f'Missing rendered native field {key}'
    # Render a sample prompt row from current XML colors/assets, never a screenshot crop.
    p=state['image','help-background'];x,y=xy(p,w,h);bw,bh=wh(p,w,h)
    ox,oy=pair(p.get('origin','0 0'));helpbg=p['color']
    d.rectangle((round(x-bw*ox),round(y-bh*oy),w,h),fill='#'+helpbg)
    p=state['helpsystem','help'];f=font(p,h);icon_size=max(1,round(h*.035))
    prompts=[('iconUpDown','CHOOSE'),('iconB','LAUNCH'),('iconA','BACK')]
    gap=round(h*.022);inner=round(h*.01)
    widths=[icon_size+inner+f.getlength(label) for _,label in prompts]
    cx,cy=xy(p,w,h);x=cx-(sum(widths)+gap*(len(prompts)-1))/2
    for (key,label),width in zip(prompts,widths):
        icon=asset(p[key],(icon_size,icon_size),p['iconColor'])
        im.alpha_composite(icon,(round(x),round(cy-icon.height/2)))
        d.text((x+icon_size+inner,cy),label,font=f,anchor='lm',fill=color(p['textColor'],helpbg))
        x+=width+gap
    return im.convert('RGB'),records

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scheme',default='default',choices=list(registered_schemes()))
    args=parser.parse_args()
    if args.scheme!='default':OUT=ROOT/'previews'/args.scheme
    OUT.mkdir(parents=True,exist_ok=True)
    manifest={}
    for h in [480,240]:
        im,records=render(h,args.scheme);im.save(OUT/f'metadata-{h}.png');manifest[str(h)]=records
        big=im.resize((960,720),Image.Resampling.NEAREST);sheet=Image.new('RGB',(960,800),'#101820');sheet.paste(big,(0,80));d=ImageDraw.Draw(sheet)
        f=ImageFont.truetype(str(ROOT/'_inc/fonts/Roboto-Bold.ttf'),24)
        d.text((18,12),f'{args.scheme} — {im.width}×{h} / static preview',font=f,fill='white')
        f=ImageFont.truetype(str(ROOT/'_inc/fonts/Roboto-Regular.ttf'),16)
        d.text((18,47),'Actual candidate geometry / sample values / static approximation, not native Batocera',font=f,fill='#b6c1cc')
        sheet.save(OUT/f'metadata-{h}-enlarged.png')
    (OUT/'geometry.json').write_text(json.dumps(manifest,indent=2))
    print('Saved metadata-panel previews and geometry manifest')

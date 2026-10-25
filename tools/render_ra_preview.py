"""Static RA display preview using helper-generated XML, never live account data."""
import importlib.util
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont
import render_metadata_panel as base

ROOT=Path(__file__).resolve().parents[1]

def render(h, scheme, fixture_root=None, unlocked=12):
    if fixture_root is None:
        from tempfile import TemporaryDirectory
        with TemporaryDirectory(prefix='ra-preview-') as tmp:
            return render(h, scheme, Path(tmp), unlocked)
    spec=importlib.util.spec_from_file_location('ra_sync',ROOT/'scripts/retroachievements/sync.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    sample={'ID':1,'NumAchievements':40,'NumAwardedToUser':max(18,unlocked),'NumAwardedToUserHardcore':unlocked}
    # Explicit fictional fixture. No network requests or credentials involved.
    fixture_root=Path(fixture_root)
    cfg={'mode':'hardcore'}
    asset,content=helper.progress_asset(sample,cfg,fixture_root)
    helper.store_asset(fixture_root/'system/retroachievements',asset,content)
    track,content=helper.track_asset(fixture_root)
    helper.store_asset(fixture_root/'system/retroachievements',track,content)
    trophy,content=helper.trophy_asset(fixture_root)
    helper.store_asset(fixture_root/'system/retroachievements',trophy,content)
    xml_bytes=helper.render(sample,cfg,fixture_root)
    (fixture_root/'sample.xml').write_bytes(xml_bytes)
    xml=ET.fromstring(xml_bytes)
    original_options=base.OPTIONS
    base.OPTIONS=dict(original_options, **{'retroachievements-progress':'on'})
    try:
        state,variables=base.resolve(scheme)
        image,records=base.render(h,scheme)
    finally:
        base.OPTIONS=original_options
    image=image.convert('RGBA')
    for node in sorted(xml.find('view'),key=lambda n:float(n.findtext('zIndex','0'))):
        props={p.tag:p.text for p in node}
        for _ in range(5):
            for key,value in dict(variables,themePath=str(ROOT)).items():
                props={p:v.replace('${'+key+'}',value) for p,v in props.items()}
        if node.tag=='text':
            font_resource=props.get('fontPath')
            if font_resource==':/fontawesome-webfont.ttf':
                props['fontPath']=str(ROOT/'tools/assets/batocera42-fontawesome-webfont.ttf')
            x,y=base.xy(props,image.width,h);w,z=base.wh(props,image.width,h)
            ox,oy=base.pair(props.get('origin','0 0'))
            if 'backgroundColor' in props:
                # Native TextComponent paints backgroundColor over its entire box.
                bg=tuple(bytes.fromhex(props['backgroundColor']))
                badge=Image.new('RGBA',(round(w),round(z)),bg)
                image.alpha_composite(badge,(round(x-w*ox),round(y-z*oy)))
            record=base.text(image,props,props['text'],h,None)
            record['color']=props['color']
            record['font_resource']=font_resource
            record['glyph_height']=base.font(props,h).getbbox(props['text'])[3]-base.font(props,h).getbbox(props['text'])[1]
            if record['text']!=record['display']:raise ValueError('Sample RA value truncated')
            records[node.get('name')]=record
            continue
        x,y=base.xy(props,image.width,h);w,z=base.wh(props,image.width,h)
        ox,oy=base.pair(props.get('origin','0 0'));x-=w*ox;y-=z*oy
        # Rasterize the exact helper-generated asset, at the native image size.
        import io, cairosvg
        with Image.open(io.BytesIO(cairosvg.svg2png(url=props['path'],output_width=round(w),output_height=round(z)))) as source:
            bar=source.convert('RGBA')
        # Native ImageComponent multiplies RGBA by the resolved theme color.
        from PIL import ImageChops
        tint=props.get('color','FFFFFFFF')
        rgba=tuple(bytes.fromhex(tint if len(tint)==8 else tint+'FF'))
        bar=ImageChops.multiply(bar,Image.new('RGBA',bar.size,rgba))
        image.alpha_composite(bar,(round(x),round(y)))
        records[node.get('name')]={'asset':props['path'],'bounds':[round(x),round(y),round(w),round(z)]}
    for ra_name in ['ra_progress','ra_progress_bar','ra_progress_track','ra_progress_trophy']:
        bounds=records[ra_name]['bounds']
        for name,record in records.items():
            if name==ra_name:continue
            if name in ['ra_progress','ra_progress_bar','ra_progress_track']:continue  # Intentional layered bar.
            a,b,c,d=record['bounds'];x,y,w,z=bounds
            if min(a+c,x+w)>max(a,x) and min(b+d,y+z)>max(b,y):
                raise ValueError(ra_name+' overlaps '+name)
    return image.convert('RGB'),records

def render_gallery(out):
    """Full-size framebuffer images with external labels; four per contact sheet."""
    import hashlib
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    manifest={'notice':'Static approximation, not native Batocera; fictional RA 12/40.',
              'framebuffer':[640,480], 'labeled_canvas':[640,535], 'schemes':{}}
    tiles=[]
    title_font=ImageFont.truetype(str(ROOT/'_inc/fonts/Roboto-Bold.ttf'),18)
    note_font=ImageFont.truetype(str(ROOT/'_inc/fonts/Roboto-Regular.ttf'),12)
    for scheme,label in base.registered_schemes().items():
        image,records=render(480,scheme,out/'fixture')
        image.save(out/f'{scheme}-480.png')
        secondary,_=render(240,scheme,out/'fixture')
        secondary.save(out/f'{scheme}-240.png')
        tile=Image.new('RGB',(640,535),'#101820');tile.paste(image,(0,55))
        draw=ImageDraw.Draw(tile)
        title=label+(' — shipped template (= Default)' if scheme=='custom' else '')
        draw.text((10,4),title,font=title_font,fill='white')
        draw.text((10,30),'640 × 480 | static approximation | RA 12/40 sample, not your account',font=note_font,fill='#c2ccd6')
        tile.save(out/f'{scheme}-480-labeled.png');tiles.append(tile)
        _,variables=base.resolve(scheme)
        manifest['schemes'][scheme]={'label':label,'palette_source':
            'shipped resources/customizations/colors.xml; not on-device Custom colors' if scheme=='custom' else 'colors.xml: '+scheme,
            'resolved_variables':variables,'geometry':records,
            'pixel_sha256':hashlib.sha256(image.tobytes()).hexdigest()}
    for start in range(0,len(tiles),4):
        sheet=Image.new('RGB',(1280,1070),'#101820')
        for i,tile in enumerate(tiles[start:start+4]):sheet.paste(tile,((i%2)*640,(i//2)*535))
        sheet.save(out/f'contact-sheet-{start//4+1}.png')
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    return manifest


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--all-palettes',action='store_true')
    args=parser.parse_args()
    if args.all_palettes:
        out=ROOT/'previews/retroachievements-final-text'
        manifest=render_gallery(out)
        print(f"Rendered {len(manifest['schemes'])} registered palettes to {out}")
        raise SystemExit(0)
    out=ROOT/'previews/retroachievements-bottom';out.mkdir(parents=True,exist_ok=True)
    manifest={}
    for scheme in ['default','commodore-64']:
        for h in [240,480]:
            image,records=render(h,scheme)
            image.save(out/f'{scheme}-{h}.png')
            sheet=Image.new('RGB',(image.width,image.height+55),'#101820')
            sheet.paste(image,(0,55));draw=ImageDraw.Draw(sheet)
            font=ImageFont.truetype(str(ROOT/'_inc/fonts/Roboto-Regular.ttf'),12)
            draw.text((8,6),f'{image.width} x {h} | static approximation',font=font,fill='white')
            draw.text((8,25),'RA 12/40 is sample data, not your account',font=font,fill='white')
            sheet.save(out/f'{scheme}-{h}-labeled.png')
            manifest[f'{scheme}-{h}']=records
    (out/'geometry.json').write_text(json.dumps(manifest,indent=2))
    print('Four static fixture previews rendered; no sample truncation or metadata overlap.')

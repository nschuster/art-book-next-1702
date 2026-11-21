"""Isolated development renderer: Pillow/CairoSVG approximation, NOT native ES.
Reads actual showcase geometry, host logos/fonts/palette and imported hardware.
No writes on import or render(); only main writes to the explicitly chosen folder.
No device data: status/count/playtime omitted; help prompts are static samples.
"""
import argparse
import io
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import cairosvg
from PIL import Image, ImageChops, ImageDraw, ImageFont, PngImagePlugin

ROOT=Path(__file__).resolve().parents[1]

def active(node, options):
    for clause in node.get('ifSubset','').split(','):
        if clause:
            key,values=clause.strip().split(':')
            if options.get(key) not in values.split('|'): return False
    return True

def substitute(value, variables):
    for _ in range(4):
        value=re.sub(r'\$\{([^}]+)\}',lambda m:variables.get(m[1],m[0]),value)
    return value

def configuration(system,palette):
    options={'color-scheme':palette,'fonts':'default','system-logos':'default','system-count':'off','system-playtime':'off'}
    variables={'themePath':str(ROOT),'system.theme':system,'system.fullName':system}
    paths=[ROOT/'fonts.xml',ROOT/'colors.xml']
    if palette=='custom': paths.append(ROOT/'resources/customizations/colors.xml')
    # Follow the runtime's actual metadata/spec include order.
    paths += [ROOT/substitute(n.text,variables) for n in ET.parse(ROOT/'console-showcase.xml').getroot().findall('include')]
    for path in paths:
        if not path.exists(): continue
        for block in ET.parse(path).getroot().findall('variables'):
            if active(block,options):
                for p in block:
                    variables[p.tag]=substitute(p.text or '',variables)
    manifest=json.loads((ROOT/'_inc/canvas-hardware/manifest.json').read_text())
    target=manifest['aliases'].get(system,system)
    if target in manifest['systems']: variables['system.fullName']=manifest['systems'][target]['metadata']['systemName']
    result={}
    for view in ET.parse(ROOT/'console-showcase.xml').getroot().findall('view'):
        for node in view:
            if not active(node,options): continue
            for name in node.get('name').split(','):
                result.setdefault((node.tag,name),{}).update({p.tag:substitute(p.text or '',variables) for p in node if active(p,options)})
    return variables,result

def rgba(value):
    value=value.strip('#')
    if len(value)==6: value+='ff'
    return tuple(int(value[i:i+2],16) for i in range(0,8,2))

def fit_art(canvas,path,props,tint=None,ink=None):
    width,height=canvas.size
    if path.suffix=='.svg':
        data=cairosvg.svg2png(url=str(path))
        im=Image.open(io.BytesIO(data)).convert('RGBA')
    else: im=Image.open(path).convert('RGBA')
    mw,mh=map(float,props['maxSize'].split())
    scale=min(mw*width/im.width,mh*height/im.height)
    im=im.resize((max(1,round(im.width*scale)),max(1,round(im.height*scale))),Image.Resampling.LANCZOS)
    if tint: im=ImageChops.multiply(im,Image.new('RGBA',im.size,rgba(tint)))
    x,y=map(float,props['pos'].split());ox,oy=map(float,props.get('origin','0 0').split())
    point=(round(x*width-ox*im.width),round(y*height-oy*im.height))
    if ink is not None:
        bbox=im.getchannel('A').getbbox()
        ink.extend([point[0]+bbox[0],point[1]+bbox[1],point[0]+bbox[2],point[1]+bbox[3]])
    canvas.alpha_composite(im,point)
    return [*point,*im.size]

def put_text(canvas,props,record):
    width,height=canvas.size;layer=Image.new('RGBA',canvas.size);draw=ImageDraw.Draw(layer)
    x,y=map(float,props['pos'].split());w,h=map(float,props['size'].split());ox,oy=map(float,props.get('origin','0 0').split())
    x=(x-ox*w)*width;y=(y-oy*h)*height;w*=width;h*=height
    # Pinned default native short-edge scaling: integer base, then accessibility scale.
    size=max(1,int(int(float(props['fontSize'])*min(width,height))*(1.5 if min(width,height)<320 else 1.31)))
    font=ImageFont.truetype(str(ROOT/props['fontPath']),size)
    text=props['text'];display=text
    # Native single-line TextComponent uses three dots; Pillow metrics are approximate.
    truncated=draw.textlength(display,font=font)>w
    if truncated:
        while display and draw.textlength(display+'...',font=font)>w:display=display[:-1]
        display+='...'
    box=draw.textbbox((0,0),display,font=font)
    tw=draw.textlength(display,font=font);th=box[3]-box[1]
    fits=tw<=w+.5 and th<=h+.5
    if props.get('alignment')=='center':x+=(w-tw)/2
    draw.text((round(x),round(y+(h-th)/2-box[1])),display,font=font,fill=rgba(props['color']))
    canvas.alpha_composite(layer)
    record['text'].append({'value':text,'display':display,'truncated':truncated,'fits':fits,'width':tw,'available':w,'font_px':size,
                           'bounds':[x,y,w,h]})

def render(system,width=640,height=480,palette='commodore-64'):
    variables,props=configuration(system,palette)
    image=Image.new('RGBA',(width,height),rgba(variables['systemBackgroundColor']))
    record={'system':system,'palette':palette,'size':[width,height],'approximation':True,'text':[],
            'limitations':'Static Pillow/CairoSVG composition; no native transitions, live controller/clock/network, real counts, or physical CRT proof. Sample help only.'}
    logo=ROOT/props['image','canvas-logo']['path']
    if logo.exists():
        record['logo_ink_bounds']=[]
        record['logo_path']=str(logo.relative_to(ROOT));record['logo_bounds']=fit_art(image,logo,props['image','canvas-logo'],props['image','canvas-logo']['color'],record['logo_ink_bounds'])
    else:put_text(image,props['text','canvas-name'],record)
    hp=props['image','canvas-hardware'];hardware=Path(hp['path'])
    if hp['visible']=='true' and hardware.exists():
        record['hardware_path']=str(hardware.relative_to(ROOT));record['hardware_maxSize']=hp['maxSize']
        record['hardware_ink_bounds']=[]
        record['hardware_bounds']=fit_art(image,hardware,hp,ink=record['hardware_ink_bounds'])
    else:put_text(image,props['text','canvas-missing'],record)
    for (kind,name),p in props.items():
        if kind=='text' and name.startswith('canvas-') and name not in ['canvas-name','canvas-missing']:
            put_text(image,p,record)
    # Host footer dimensions from theme.xml; representative English prompts only.
    root=ET.fromstring(re.sub(r'&(?!#?\w+;)', '&amp;', (ROOT/'theme.xml').read_text()))
    footer=root.find(".//image[@name='help-background']")
    footer_height=float(footer.findtext('size').split()[1])
    draw=ImageDraw.Draw(image);draw.rectangle((0,round(height*(1-footer_height)),width,height),fill=rgba(variables['helpBackgroundColor']))
    font=ImageFont.truetype(str(ROOT/variables['fontBold']),max(1,int(int(.03125*height)*(1.5 if height<320 else 1.31))))
    # This is explicitly approximate help, not evidence for native prompt width/layout.
    text='SYSTEM     SELECT     MENU';box=draw.textbbox((0,0),text,font=font)
    layer=Image.new('RGBA',image.size);help_draw=ImageDraw.Draw(layer)
    help_draw.text(((width-draw.textlength(text,font=font))/2,height*.942708333333333-(box[3]-box[1])/2-box[1]),text,font=font,fill=rgba(variables['helpTextColor']))
    image.alpha_composite(layer)
    record['hardware_tint']=hp['color']
    record['resolved_colors']={key:variables[key] for key in ['systemBackgroundColor','systemLogoColor','helpBackgroundColor','helpTextColor']}
    record['palette_source']='resources/customizations/colors.xml' if palette=='custom' else 'colors.xml'
    record['palette_label']=dict(registered_palettes())[palette]
    return image.convert('RGB'),record

def registered_palettes():
    root=ET.fromstring(re.sub(r'&(?!#?\w+;)', '&amp;', (ROOT/'theme.xml').read_text()))
    return [(p.get('name'),p.get('displayName')+(' (shipped template)' if p.get('name')=='custom' else ''))
            for p in root.find("subset[@name='color-scheme']")]

def palette_gallery(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    records=[];palettes=registered_palettes()
    for palette,label in palettes:
        for w,h in [(640,480),(320,240)]:
            image,record=render('c64',w,h,palette)
            name=f'{palette}-c64-{w}x{h}.png'
            info=PngImagePlugin.PngInfo();info.add_text('Description','STATIC APPROXIMATION — not a native ES/CRT capture')
            image.save(output/name,pnginfo=info);record['file']=name;records.append(record)
    for w,h in [(640,480),(320,240)]:
        # Native-size frames, external labels; four palettes per readable sheet.
        for start in range(0,len(palettes),4):
            sheet=Image.new('RGB',(w*2,(h+64)*2),'#272727');draw=ImageDraw.Draw(sheet)
            font=ImageFont.truetype(str(ROOT/'_inc/fonts/Roboto-Bold.ttf'),18 if w==640 else 13)
            for i,(palette,label) in enumerate(palettes[start:start+4]):
                x=i%2*w;y=i//2*(h+64)
                draw.text((x+12,y+7),label,font=font,fill='white')
                draw.text((x+12,y+34),f'C64 | {w}x{h} | static approximation',font=font,fill='#cccccc')
                sheet.paste(Image.open(output/f'{palette}-c64-{w}x{h}.png'),(x,y+64))
            sheet.save(output/f'palettes-{w}-sheet-{start//4+1}.{ "jpg" if w==640 else "png"}',**({'quality':95} if w==640 else {}))
    (output/'manifest.json').write_text(json.dumps(records,indent=2)+'\n')
    (output/'README.md').write_text('# Canvas left-column palette review\n\nAll registered palettes; Custom is the shipped template, not device settings. C64 fixture identical throughout. Native-size 640x480 and independently composed 320x240 frames; 2x2 externally labeled sheets. Original runtime Art Book SVG, multiplicative resolved tint; actual imported Canvas PNG (lossless alpha crop of source WebP), never recolored. Original logo transparency is retained; aligned image rectangles do not guarantee identical ink edges for every system/custom logo.\n\nStatic Pillow/CairoSVG approximations, NOT native ES captures. Footer prompts are samples; live status/counts/playtime omitted. No CRT proof. Several schemes intentionally share system-view colors and thus look alike here; their game-list palettes differ. Source artwork rights conflict remains unresolved; no publication permission claimed.\n')
    return records

def metadata_gallery(output):
    """Dedicated refined gallery; never writes to older review folders."""
    output=Path(output);records=palette_gallery(output)
    for system in ['snes','psx','gb','unlisted-system']:
        for w,h in [(640,480),(320,240)]:
            image,record=render(system,w,h,'commodore-64')
            name=f'commodore-64-{system}-{w}x{h}.png'
            info=PngImagePlugin.PngInfo();info.add_text('Description','STATIC APPROXIMATION — not native ES')
            image.save(output/name,pnginfo=info);record['file']=name;records.append(record)
    for w,h in [(640,480),(320,240)]:
        sheet=Image.new('RGB',(2*w,2*(h+50)),'#272727');draw=ImageDraw.Draw(sheet)
        font=ImageFont.truetype(str(ROOT/'_inc/fonts/Roboto-Bold.ttf'),16 if w==640 else 11)
        for i,system in enumerate(['snes','psx','gb','unlisted-system']):
            x=i%2*w;y=i//2*(h+50)
            draw.text((x+10,y+8),f'{system} | {w}x{h} | STATIC, NOT ES',font=font,fill='white')
            sheet.paste(Image.open(output/f'commodore-64-{system}-{w}x{h}.png'),(x,y+50))
        sheet.save(output/f'representatives-{w}.png')
    (output/'manifest.json').write_text(json.dumps(records,indent=2)+'\n')
    (output/'README.md').write_text('# Values-only Canvas metadata — static review only\n\n'
        'All eight registered palettes with C64; Custom is the shipped template, not device settings. '
        'SNES, PlayStation, original Game Boy and unknown-system fixtures use Commodore hardware colors. '
        '640×480 primary, independently composed 320×240 secondary. Externally labeled sheets retain native frame sizes.\n\n'
        'Actual runtime XML typography, geometry, fonts and palette. Original Art Book logos and Canvas hardware unchanged. '
        'Pillow/CairoSVG approximations, NOT EmulationStation screenshots or CRT proof; live status/count/playtime omitted and help prompts are samples. '
        'Long text uses an approximate native three-dot abbreviation; manifests retain full strings and truncation flags.\n\n'
        'Type, year, architecture, CPU, RAM and launch price values only; no repeated manufacturer or metadata headings. '
        'Existing field-level evidence and variant/market notes unchanged: `_inc/canvas-hardware/specs.json`; QA: `docs/qa/canvas-metadata-values.md`. '
        'Unknown is deliberate where reviewed sources do not establish a fact. Prices are nominal market launch prices, not conversions. '
        'Artwork redistribution rights remain unresolved. No publication or device changes.\n')
    return records


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--all-palettes',action='store_true');parser.add_argument('--metadata-refined',action='store_true');args=parser.parse_args()
    if args.metadata_refined:
        metadata_gallery(args.output)
        return
    if args.all_palettes:
        palette_gallery(args.output)
        return
    args.output.mkdir(parents=True,exist_ok=True);records=[]
    for system in ['snes','gb','c64','megadrive','psx','unlisted-system']:
        for palette in ['commodore-64','oled']:
            for w,h in [(640,480),(320,240)]:
                image,record=render(system,w,h,palette)
                name=f'{palette}-{system}-{w}x{h}.png'
                info=PngImagePlugin.PngInfo();info.add_text('Description','STATIC APPROXIMATION — not a native ES/CRT capture')
                image.save(args.output/name,pnginfo=info);record['file']=name;records.append(record)
    sheet=Image.new('RGB',(1280,3*520),'#272727');draw=ImageDraw.Draw(sheet)
    for i,system in enumerate(['snes','gb','c64','megadrive','psx','unlisted-system']):
        x=i%2*640;y=i//2*520
        draw.text((x+12,y+12),f'STATIC APPROXIMATION | {system} | 640x480 | Canvas hardware / Art Book logos',fill='white')
        sheet.paste(Image.open(args.output/f'commodore-64-{system}-640x480.png'),(x,y+40))
    sheet.save(args.output/'overview-640.jpg')
    (args.output/'manifest.json').write_text(json.dumps(records,indent=2)+'\n')
    (args.output/'README.md').write_text('# Static approximations only\n\nActual runtime XML geometry, imported hardware, original Art Book logos/palette/fonts. Independently rendered at both resolutions, not whole-frame downsampling. No live system status/counts/playtime. Footer labels are sample approximations; CairoSVG/Pillow differ from native rendering. Unknown-system name is a fixture. No CRT/device claims.\n')

if __name__=='__main__': main()

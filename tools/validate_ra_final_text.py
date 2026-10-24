"""Validate final gallery and record actual alpha-aware count/track contrast.
Static fixture evidence only, not a native Batocera or CRT certification.
"""
import io
import json
from pathlib import Path
import cairosvg
from PIL import Image, ImageDraw, ImageFont
import render_ra_preview as preview

OUT = preview.ROOT / 'previews/retroachievements-final-text'


def luminance(rgb):
    c = [v / 255 for v in rgb]
    c = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in c]
    return sum(a * b for a, b in zip(c, (.2126, .7152, .0722)))


def contrast(fg, bg):
    a, b = sorted((luminance(fg), luminance(bg)))
    return (b + .05) / (a + .05)


def main():
    results = {}
    sheet = Image.new('RGB', (800, 420), '#101820')
    draw = ImageDraw.Draw(sheet)
    label_font = ImageFont.truetype(str(preview.ROOT / '_inc/fonts/Roboto-Regular.ttf'), 14)
    row = 0
    for scheme in ('famicom', 'commodore-64'):
        _, variables = preview.base.resolve(scheme)
        ink = variables['gamelistListTextlistUnselectedColor']
        rgba = bytes.fromhex(ink if len(ink) == 8 else ink + 'ff')
        bg = tuple(bytes.fromhex(variables['gamelistListTextlistBackgroundColor']))
        for count in (0, 12, 40):
            for h in (480, 240):
                image, records = preview.render(h, scheme, OUT / 'contrast-fixture', unlocked=count)
                image.save(OUT / f'{scheme}-{h}-progress-{count}.png')
                x, y, w, z = records['ra_progress_track']['bounds']
                text = records['ra_progress']
                assert text['display'] == text['text']
                assert text['glyph_height'] <= z
                # Same generated SVG, before text compositing: sample full-coverage glyph contrast.
                fill = Image.open(io.BytesIO(cairosvg.svg2png(url=records['ra_progress_bar']['asset'], output_width=w, output_height=z))).convert('RGBA')
                track = Image.new('RGBA', fill.size, bg + (255,))
                track.alpha_composite(fill)
                font = ImageFont.truetype(str(preview.ROOT / '_inc/fonts/Roboto-Bold.ttf'), text['font_pixels'])
                width = font.getlength(text['text'])
                assert width <= text['bounds'][2]
                ratios = []
                for dx in range(round(w/2-width/2), round(w/2+width/2)):
                    surface = track.getpixel((dx, z//2))[:3]
                    foreground = tuple(round(a*rgba[3]/255+b*(1-rgba[3]/255)) for a,b in zip(rgba[:3], surface))
                    ratios.append(contrast(foreground, surface))
                results[f'{scheme}-{h}-{count}'] = dict(color=ink, font_pixels=font.size, glyph_width=width, glyph_height=text['glyph_height'], text_box=text['bounds'], track_box=[x,y,w,z], contrast_min=min(ratios), contrast_max=max(ratios))
                if h == 480:
                    draw.text((10, row*70+4), f'{scheme} | {count}/40 | native 640x480 crop enlarged 2x', font=label_font, fill='white')
                    sheet.paste(image.crop((x,y,x+w,y+z)).resize((w*2,z*2),Image.Resampling.NEAREST),(280,row*70+23))
                    row += 1
    sheet.save(OUT / 'contrast-inspection.png')
    (OUT / 'contrast.json').write_text(json.dumps(results, indent=2))
    manifest = json.loads((OUT / 'manifest.json').read_text())
    assert len(manifest['schemes']) == 8
    assert len(list(OUT.glob('contact-sheet-*.png'))) == 2
    for scheme in manifest['schemes']:
        for h,w in ((480,640),(240,320)):
            with Image.open(OUT / f'{scheme}-{h}.png') as image:
                image.load()
                assert image.size == (w,h)
    print('PASS: 8 palettes x 2 resolutions, 2 contact sheets, 12 zero/sample/full contrast fixtures; no count truncation or glyph-height overflow.')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()

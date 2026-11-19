"""Development only: regenerate bundled Roboto ASCII/Latin-1 bitmap atlas."""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[3]
out = Path(__file__).resolve().parent
font = ImageFont.truetype(str(root / '_inc/fonts/Roboto-Regular.ttf'), 24)
im = Image.new('RGB', (32 * 16, 32 * 14), (255, 0, 255))
draw = ImageDraw.Draw(im)
draw.fontmode = '1'
widths = {}
for i in range(32, 256):
    x, y = ((i-32) % 16)*32, ((i-32)//16)*32
    draw.text((x, y+2), chr(i), font=font, fill=(233,225,204), stroke_width=0)
    widths[str(i)] = round(font.getlength(chr(i)))
im.save(out / 'font.bmp')
(out / 'widths.json').write_text(json.dumps(widths, sort_keys=True)+'\n')

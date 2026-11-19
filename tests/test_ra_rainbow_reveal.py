"""The partial fill must retain the same colours as the full-track rainbow."""
import io
import os
import subprocess
import tempfile
from pathlib import Path
import pytest
from PIL import Image
from test_ra_bar import helper

@pytest.mark.parametrize('native', [False, True])
def test_partial_rainbow_is_fixed_full_track_prefix(native):
    if native:
        probe = os.environ.get('BATOCERA_SVG_RASTER')
        if not probe:
            pytest.skip('Set BATOCERA_SVG_RASTER to pinned NanoSVG CLI: input width height output.rgba')
    else:
        import cairosvg
    with tempfile.TemporaryDirectory() as tmp:
        frames = {}
        for count in (0, 1, 25, 50, 75, 100):
            _, svg = helper.progress_asset(dict(ID=1, NumAchievements=100, NumAwardedToUser=count, NumAwardedToUserHardcore=count), {}, tmp)
            if native:
                source, out = Path(tmp)/'bar.svg', Path(tmp)/'bar.rgba'
                source.write_bytes(svg)
                subprocess.run([probe,str(source),'256','22',str(out)],check=True)
                im = Image.frombytes('RGBA',(256,22),out.read_bytes())
            else:
                im = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg,output_width=256,output_height=22))).convert('RGBA')
            frames[count] = im
        full = frames[100]
        assert frames[0].getbbox() is None
        for count in (1,25,50,75):
            edge = 256*count/100
            for x in range(max(0,int(edge)-1)):
                assert frames[count].getpixel((x,11)) == full.getpixel((x,11)), (native,count,x)
            for x in range(int(edge)+1,256):
                assert frames[count].getpixel((x,11))[3] == 0
        assert full.getpixel((20,11)) != full.getpixel((220,11))

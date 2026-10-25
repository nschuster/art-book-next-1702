"""Metadata-only outline of exact native U+F091, not a substituted trophy."""
import hashlib
import io
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET
import cairosvg
from PIL import Image
import pytest
from test_metadata import ROOT
from test_ra_bar import helper
from test_ra_palettes import base, preview

FONT_SHA256 = '9e540a087924a6e64790149d735cac022640e4fa6bff6bd65f5e9f41529bf0b3'
DATA = dict(ID=1, NumAchievements=40, NumAwardedToUser=12, NumAwardedToUserHardcore=12)

@pytest.mark.parametrize('mode', ['softcore', 'hardcore'])
@pytest.mark.parametrize('total,count', [(0,0),(40,0),(40,12),(40,40)])
def test_native_trophy_and_panel_geometry(mode, total, count):
    data = dict(DATA, NumAchievements=total, NumAwardedToUser=count, NumAwardedToUserHardcore=count)
    doc = ET.fromstring(helper.render(data, {'mode':mode}, Path('/userdata')))
    trophy = doc.find("./view/image[@name='ra_progress_trophy']")
    assert trophy is not None, 'Scalable native outline must avoid quantized font undersizing'
    assert trophy.get('extra') == 'true'
    assert trophy.findtext('path') == str(helper.trophy_asset(Path('/userdata'))[0])
    assert trophy.findtext('color') == '${gamelistListMetadataIconColor}'
    assert trophy.findtext('size') == '0.03125 0.041666666666667'
    assert trophy.findtext('origin') == '0 0.5'
    assert trophy.find('fontSize') is None
    for name in ('ra_progress_track','ra_progress_bar'):
        bar = doc.find(f"./view/image[@name='{name}']")
        assert bar.findtext('pos') == '0.5890625 0.815'
        assert bar.findtext('size') == '0.3609375 0.045833333333333'
    count_node = doc.find("./view/text[@name='ra_progress']")
    assert count_node.findtext('pos') == '0.76953125 0.837916666666667'
    assert count_node.findtext('fontSize') == '0.027777777777777'
    assert count_node.findtext('size') == '0.14 0.045833333333333'
    assert count_node.findtext('color') == '${gamelistListTextlistUnselectedColor}'
    assert len(doc.find('view')) == 4

@pytest.mark.parametrize('h', [480, 240])
def test_trophy_ink_matches_metadata_icon_scale_without_clipping(h):
    _, content = helper.trophy_asset(Path('/userdata'))
    size = 20 if h == 480 else 10
    icon = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=content, output_width=size, output_height=size)))
    ink = icon.getbbox()
    assert ink[2]-ink[0] == size  # no more 18px/9px near-match
    assert size-1 <= ink[3]-ink[1] <= size
    assert abs((ink[1]+ink[3])/2-size/2) <= .5
    state, _ = base.resolve('commodore-64')
    widths = []
    for (kind,name), props in state.items():
        if kind == 'image' and name.startswith('game-') and name.endswith('-icon') and props.get('visible') == 'true':
            a,b = base.pair(props['maxSize'])
            native = base.asset(props['path'], (a*round(h*4/3), b*h))
            box = native.getbbox(); widths.append(box[2]-box[0])
    assert ink[2]-ink[0] == max(widths)

@pytest.mark.parametrize('h', [480, 240])
def test_progress_visible_gap_matches_metadata_ink(h):
    image, records = preview.render(h, 'commodore-64')
    x,y,w,z = records['ra_progress_trophy']['bounds']
    bx,by,bw,bh = records['ra_progress_bar']['bounds']
    assert bx-(x+w) == (6 if h == 480 else 3)
    assert bx+bw == round(image.width*.95)
    assert (by,bh) == ((391,22) if h == 480 else (196,11))
    assert abs((y+z/2)-(by+bh/2)) <= .5


def test_default_preview_does_not_write_unrelated_preview_fixtures():
    import inspect
    source = inspect.getsource(preview.render)
    assert 'TemporaryDirectory' in source
    assert "ROOT/'previews/retroachievements-bottom/fixture'" not in source


def test_preview_uses_identical_pinned_resource_font():
    font = ROOT/'tools/assets/batocera42-fontawesome-webfont.ttf'
    assert hashlib.sha256(font.read_bytes()).hexdigest() == FONT_SHA256
    with tempfile.TemporaryDirectory() as tmp:
        for scheme in base.registered_schemes():
            for h in (240,480):
                image, records = preview.render(h, scheme, Path(tmp))
                trophy = records['ra_progress_trophy']
                assert Path(trophy['asset']).read_bytes() == helper.trophy_asset(Path(tmp))[1]
                tx,ty,tw,th = records['ra_progress']['bounds']
                bx,by,bw,bh = records['ra_progress_bar']['bounds']
                assert abs(tx+tw/2-(bx+bw/2)) <= 1


def test_trophy_asset_is_owned_and_collected_safely():
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp); state=root/'system/retroachievements'
        path,content=helper.trophy_asset(root)
        helper.store_asset(state,path,content)
        xml=helper.render(DATA,{},root)
        extra=state/'extras/snes/sample.xml';extra.parent.mkdir(parents=True);extra.write_bytes(xml)
        manifest={'snes/sample.xml':{'sha256':hashlib.sha256(xml).hexdigest()}}
        helper.collect_assets(state,manifest);assert path.exists()
        helper.collect_assets(state,{});assert not path.exists()
        helper.store_asset(state,path,content);path.write_text('user edit')
        helper.collect_assets(state,{});assert path.read_text() == 'user edit'

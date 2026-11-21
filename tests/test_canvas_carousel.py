"""Opt-in Canvas hardware showcase; static/source evidence, not a CRT capture."""
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET
import pytest
from test_metadata import ROOT, resolve
from test_c64 import parse, structure

REGISTRATION = '''<subset name="console-showcase" displayName="Console Hardware &amp; Info"><include name="off" displayName="Off"/><include name="on" displayName="On (Canvas hardware)"/></subset>'''
INCLUDE = '<include ifSubset="console-showcase:on">./console-showcase.xml</include>'

def approved_canvas_transform(root):
    root.insert(len(root)-1, ET.fromstring(REGISTRATION))
    root.insert(len(root)-1, ET.fromstring(INCLUDE))

def test_default_off_registration_and_only_system_scope():
    root = parse((ROOT/'theme.xml').read_bytes())
    node = root.find("subset[@name='console-showcase']")
    assert node is not None, 'Missing opt-in hardware carousel mode'
    assert structure(node) == structure(ET.fromstring(REGISTRATION))
    assert structure(root[-2]) == structure(ET.fromstring(INCLUDE))
    mode = ET.parse(ROOT/'console-showcase.xml').getroot()
    assert all(n.get('name') == 'system' for n in mode.findall('view'))

@pytest.mark.parametrize('art', ['default','noir','nintendont','circuit','outline','custom','custom-fullscreen'])
def test_off_preserves_every_resolved_property_including_custom_fullscreen(art):
    for ratio, help_on in itertools.product(['4-3','4-3-auto','16-9'], [True,False]):
        kw = dict(view='system',ratio=ratio,help=help_on,system_art=art)
        assert resolve(**kw,showcase='off') == resolve(**kw,baseline=True)
        on = resolve(**kw,showcase='on')
        assert on[('image','logo')]['visible'] == 'false'
        assert on[('image','system-artwork')]['visible'] == 'false'
        assert on[('image','canvas-hardware')]['maxSize'] == '0.43 0.36'
        assert on[('image','canvas-logo')]['path'] == './_inc/systems/logos/${system.theme}.svg'
        for view in ['basic','detailed','screen','menu']:
            assert resolve(**(kw|{'view':view}),showcase='on') == resolve(**(kw|{'view':view}),showcase='off')

def test_assets_metadata_and_provenance():
    directory = ROOT/'_inc/canvas-hardware'
    assert (directory/'manifest.json').exists(), 'Missing source asset inventory'
    manifest = json.loads((directory/'manifest.json').read_text())
    assert manifest['revision'] == 'bf010295778b2756310edfc3a61fe5e20d31e5b9'
    assert 'conflict' in manifest['rights'].lower()
    assert len(manifest['systems']) == 24
    for name, record in manifest['systems'].items():
        path = ROOT/record['asset']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record['sha256']
        assert record['source'].startswith('_inc/systems/carousel-icons-icons/')
        variables = ET.parse(directory/f'metadata/{name}.xml').getroot()
        assert variables.findtext('variables/canvasHasHardware') == 'true'
    default_visibility = ET.parse(directory/'metadata/default.xml').getroot()
    assert default_visibility.findtext('variables/canvasHasHardware') == 'false'
    for name, record in manifest['systems'].items():
        path = ROOT/record['asset']
        from PIL import Image
        im = Image.open(path)
        assert im.mode == 'RGBA' and im.getbbox() == (0,0,*im.size)
        source = Path('/tmp/canvas-es-reference')
        if source.exists():
            original = Image.open(source/record['source']).convert('RGBA')
            assert im.tobytes() == original.crop(tuple(record['crop'])).tobytes()
            metadata = ET.parse(source/record['metadata_source']).getroot().find('variables')
            assert record['metadata'] == {key:metadata.findtext(key) for key in ['systemName','systemManufacturer','systemReleaseYear','systemHardwareType']}
    default = ET.parse(directory/'metadata/default.xml').getroot()
    assert default.findtext('variables/canvasManufacturer') == 'Unknown'
    assert default.findtext('variables/canvasYear') == 'Unknown'
    assert default.findtext('variables/canvasMissing') == 'Artwork unavailable'
    for alias, target in manifest['aliases'].items():
        assert (directory/f'metadata/{alias}.xml').read_bytes() == (directory/f'metadata/{target}.xml').read_bytes()

def test_native_schema_and_runtime_factory():
    source = Path(os.environ.get('BATOCERA_ES_SOURCE','/tmp/ra-es-source'))
    if not (source/'.git').exists(): pytest.skip('Pinned Batocera source unavailable')
    def read(path):
        return subprocess.check_output(['git','show','4adf26b43900d1a33887af6d8af3da2e99e398a5:'+path],cwd=source,text=True)
    schema = read('es-core/src/ThemeData.cpp')
    root = ET.parse(ROOT/'console-showcase.xml').getroot()
    for view in root.findall('view'):
        for component in view:
            section = schema.split('{ "'+component.tag+'", {',1)[1].split('\n\t} },',1)[0]
            allowed = set(re.findall(r'\{ "(\w+)",',section))
            assert {p.tag for p in component} <= allowed
    system = read('es-app/src/views/SystemView.cpp')
    assert 'ThemeData::makeExtras' in system
    assert '"logo", "logoText", "systemcarousel"' in system

def test_isolated_preview_renderer_and_real_layout(tmp_path):
    import importlib.util
    renderer = ROOT/'tools/render_canvas_carousel.py'
    assert renderer.exists(), 'Missing isolated actual-layout preview renderer'
    spec = importlib.util.spec_from_file_location('canvas_preview', renderer)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert not list(tmp_path.iterdir())
    from PIL import Image
    for width,height in [(640,480),(320,240)]:
        for system in ['snes','gb','c64','unlisted-system']:
            image,record = module.render(system,width,height,'commodore-64')
            assert image.size == (width,height)
            assert record['approximation'] is True
            if system != 'unlisted-system':
                assert record['hardware_path'] == f'_inc/canvas-hardware/{system}.png'
                assert record['logo_path'] == f'_inc/systems/logos/{system}.svg'
                assert record['hardware_maxSize'] == '0.43 0.36'
            assert all(row['fits'] for row in record['text'])
            output=tmp_path/f'{system}-{width}.png';image.save(output)
            assert Image.open(output).size == (width,height)

def test_layout_safe_regions():
    props=resolve(view='system',showcase='on')
    for width,height in [(640,480),(320,240)]:
        for name in ['canvas-type','canvas-year','canvas-architecture','canvas-cpu','canvas-ram','canvas-price']:
            p=props['text',name]
            x,y=map(float,p['pos'].split());w,h=map(float,p['size'].split())
            assert x>=.53 and x+w<=.950001 and y>=.18 and y+h<=.80
        p=props['image','canvas-hardware']
        assert p['origin']=='0 0.5'
        assert float(p['pos'].split()[0]) + float(p['maxSize'].split()[0]) < .53


def test_logo_and_hardware_share_left_column():
    props=resolve(view='system',showcase='on')
    logo=props['image','canvas-logo'];hardware=props['image','canvas-hardware']
    assert logo['origin'] == hardware['origin'] == '0 0.5'
    assert logo['pos'].split()[0] == hardware['pos'].split()[0] == '0.07'
    assert logo['maxSize'] == '0.43 0.17'
    assert props['text','canvas-name']['alignment'] == 'left'
    assert props['text','canvas-missing']['alignment'] == 'left'


def test_all_registered_palette_gallery(tmp_path):
    import importlib.util
    spec=importlib.util.spec_from_file_location('canvas_preview',ROOT/'tools/render_canvas_carousel.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    registered=parse((ROOT/'theme.xml').read_bytes()).find("subset[@name='color-scheme']")
    assert hasattr(module,'registered_palettes'), 'Renderer must enumerate actual registrations'
    assert [p[0] for p in module.registered_palettes()] == [p.get('name') for p in registered]
    records=module.palette_gallery(tmp_path)
    assert len(records)==len(registered)*2
    from PIL import Image
    for r in records:
        assert r['system']=='c64'
        assert all(t['fits'] for t in r['text'])
        assert abs(r['logo_ink_bounds'][0]-r['hardware_ink_bounds'][0]) <= 1
        assert r['logo_ink_bounds'][3] < r['hardware_ink_bounds'][1]
        assert r['hardware_bounds'][0]+r['hardware_bounds'][2] < r['size'][0]*.53
        assert Image.open(tmp_path/r['file']).size==tuple(r['size'])
        assert r['hardware_tint']=='ffffff'
        if r['palette']=='custom':
            assert r['palette_source']=='resources/customizations/colors.xml'
            assert 'shipped template' in r['palette_label']
    assert len(list(tmp_path.glob('palettes-640-sheet-*.jpg')))==2
    assert len(list(tmp_path.glob('palettes-320-sheet-*.png')))==2
    # Default help text is ffffffaa over black: alpha must not be discarded.
    image,_=module.render('c64',640,480,'default')
    assert max(extreme[1] for extreme in image.crop((0,430,640,480)).getextrema()) <= 170
    # Compare actual resolved surfaces and unchanged opaque hardware across palettes.
    for width,height in [(640,480),(320,240)]:
        hardware_crops=[]
        for palette,_ in module.registered_palettes():
            image,r=module.render('c64',width,height,palette)
            assert image.getpixel((0,0))==module.rgba(r['resolved_colors']['systemBackgroundColor'])[:3]
            x,y,w,h=r['hardware_bounds']
            alpha=Image.open(ROOT/r['hardware_path']).convert('RGBA').resize((w,h),Image.Resampling.LANCZOS).getchannel('A')
            crop=image.crop((x,y,x+w,y+h))
            hardware_crops.append(bytes(channel for yy in range(h) for xx in range(w)
                                        if alpha.getpixel((xx,yy))==255
                                        for channel in crop.getpixel((xx,yy))))
        assert len(set(hardware_crops))==1

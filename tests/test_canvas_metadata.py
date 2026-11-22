"""Refined optional carousel, source-backed additions and unchanged left column."""
import importlib.util
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import pytest
from test_metadata import ROOT

spec=importlib.util.spec_from_file_location('canvas_renderer',ROOT/'tools/render_canvas_carousel.py')
renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)


def test_imported_bytes_and_nonmetadata_components_preserved():
    import hashlib
    baseline=json.loads((ROOT/'tests/fixtures/canvas-metadata-preservation.json').read_text())
    for path,digest in baseline['hashes'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
    view=ET.parse(ROOT/'console-showcase.xml').find('view')
    for serialized in baseline['components']:
        old=ET.fromstring(serialized)
        actual=next(n for n in view if n.tag==old.tag and n.get('name')==old.get('name'))
        # Comic is opt-in; the default component must remain byte-identical.
        # Its new path/tint/fallback behavior is covered by test_comic_logos.py.
        for child in list(actual):
            if child.get('ifSubset') == 'system-logos:comic':
                assert (actual.get('name'), child.tag) in {
                    ('canvas-logo', 'path'), ('canvas-logo', 'color'),
                    ('canvas-name', 'visible'),
                }
                if child is list(actual)[-1]:
                    # Preserve the closing indentation carried by the appended node.
                    list(actual)[-2].tail = child.tail
                actual.remove(child)
        assert ET.tostring(actual,encoding='unicode').strip()==serialized


def test_complete_inventory_fits_and_palette_contrast():
    manifest=json.loads((ROOT/'_inc/canvas-hardware/manifest.json').read_text())
    for system in list(manifest['systems'])+list(manifest['aliases']):
        for size in [(640,480),(320,240)]:
            _,record=renderer.render(system,*size)
            assert all(t['fits'] and not t['truncated'] for t in record['text'])
    def luminance(rgb):
        values=[v/255 for v in rgb]
        values=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in values]
        return sum(v*c for v,c in zip(values,[.2126,.7152,.0722]))
    for palette,_ in renderer.registered_palettes():
        variables,props=renderer.configuration('c64',palette)
        bg=renderer.rgba(variables['systemBackgroundColor'])[:3]
        for (kind,name),p in props.items():
            if kind!='text' or not name.startswith('canvas-'):continue
            rgba=renderer.rgba(p['color']);alpha=rgba[3]/255
            fg=[a*alpha+b*(1-alpha) for a,b in zip(rgba[:3],bg)]
            l1,l2=sorted([luminance(fg),luminance(bg)])
            assert (l2+.05)/(l1+.05)>=4.5,(palette,name)


def test_specs_generator_reproduces_shipped_overlay(tmp_path):
    import shutil
    module_spec=importlib.util.spec_from_file_location('build_specs',ROOT/'tools/build_canvas_specs.py')
    builder=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(builder)
    dest=tmp_path/'_inc/canvas-hardware';dest.mkdir(parents=True)
    for name in ['manifest.json','specs.json']:shutil.copyfile(ROOT/'_inc/canvas-hardware'/name,dest/name)
    builder.build(tmp_path)
    for path in (ROOT/'_inc/canvas-hardware/specs').glob('*.xml'):
        assert path.read_bytes()==(dest/'specs'/path.name).read_bytes()


def test_sourced_overlay_and_aliases():
    data=json.loads((ROOT/'_inc/canvas-hardware/specs.json').read_text())
    original=json.loads((ROOT/'_inc/canvas-hardware/manifest.json').read_text())
    assert set(data['systems'])==set(original['systems'])
    for system,record in data['systems'].items():
        assert set(record['fields'])=={'Architecture','CPU','RAM','Price'}
        for field,fact in record['fields'].items():
            assert fact['value']
            if fact['value']!='Unknown':
                assert fact['sources'] and fact['evidence']
                assert all(source in data['sources'] for source in fact['sources'])
        _,props=renderer.configuration(system,'commodore-64')
        for field,fact in record['fields'].items():
            assert props['text','canvas-'+field.lower()]['text']==fact['value']
    for alias,target in original['aliases'].items():
        a,_=renderer.configuration(alias,'default');t,_=renderer.configuration(target,'default')
        # Explicit Amiga model aliases must not inherit another model's specifications.
        for key in ['Architecture','CPU','RAM','Price']:
            assert a['canvas'+key]==t['canvas'+key]
    _,props=renderer.configuration('unlisted-system','default')
    assert all(props['text','canvas-'+k]['text']=='Unknown' for k in ['architecture','cpu','ram','price'])


@pytest.mark.parametrize('size',[(640,480),(320,240)])
def test_values_only_spacing_and_glyph_fit(size):
    for palette,_ in renderer.registered_palettes():
        for system in ['c64','snes','psx','gb','unlisted-system','amstradcpc','pcengine']:
            variables,props=renderer.configuration(system,palette)
            fields=['type','year','architecture','cpu','ram','price']
            right={name for kind,name in props if kind=='text' and name.startswith('canvas-') and name not in ['canvas-name','canvas-missing']}
            assert right=={'canvas-'+field for field in fields}
            previous_bottom=0
            for field in fields:
                value=props['text','canvas-'+field]
                key={'cpu':'CPU','ram':'RAM'}.get(field,field.title())
                assert value['text']==variables['canvas'+key]
                x,y=map(float,value['pos'].split());w,h=map(float,value['size'].split())
                assert x==.55 and x+w<=.951 and .18<=y<y+h<=.80
                assert y-previous_bottom>=.009
                previous_bottom=y+h
            image,record=renderer.render(system,*size,palette)
            assert all(t['fits'] and not t['truncated'] for t in record['text']), record['text']
            assert [t['value'] for t in record['text']][-6:]==[props['text','canvas-'+f]['text'] for f in fields]


def test_values_gallery_isolated_and_documented(tmp_path):
    records=renderer.metadata_gallery(tmp_path)
    assert len(records)==len(renderer.registered_palettes())*2+8
    assert 'Values-only' in (tmp_path/'README.md').read_text()
    assert 'docs/qa/canvas-metadata-values.md' in (tmp_path/'README.md').read_text()
    for record in records:
        assert (tmp_path/record['file']).is_file()
        assert all(t['fits'] and not t['truncated'] for t in record['text'])


def test_long_text_is_bounded_with_truthful_ellipsis():
    from PIL import Image
    _,props=renderer.configuration('c64','default')
    for size in [(640,480),(320,240)]:
        image=Image.new('RGBA',size);record={'text':[]}
        p=props['text','canvas-cpu'] | {'text':'Very long regional CPU specification '*8}
        renderer.put_text(image,p,record)
        assert record['text'][0]['truncated']
        assert record['text'][0]['display'].endswith('...')
        assert record['text'][0]['fits']
        assert record['text'][0]['value']==p['text']

"""Scoped bound text replacement; arithmetic is separately run in pinned C++ probe."""
import itertools
import subprocess
import xml.etree.ElementTree as ET
from test_metadata import ROOT, resolve

EXPRESSION = '"" + (({game:gametime} / 3600) >> 0) + "h " + ((({game:gametime} / 60) >> 0) - ((({game:gametime} / 3600) >> 0) * 60)) + "m"'
NAME = 'game-gametime-totalhours'


def approved_transform(root):
    """Exact permitted addition, not removal of a broad baseline guard."""
    view = next(v for v in root.findall('view') if v.find("text[@name='md_gametime'][pos]") is not None)
    ET.SubElement(ET.SubElement(view, 'text', {'name': 'md_gametime'}), 'visible').text = 'false'
    extra = ET.SubElement(view, 'text', {'name': NAME, 'extra': 'true'})
    props = [('visible','true'),('origin','0 0.5'),('fontPath','${fontBold}'),('fontSize','0.033333333333333'),('color','${gamelistListMetadataColor}'),('lineSpacing','1'),('multiLine','false'),('autoScroll','none'),('alignment','left'),('verticalAlignment','center'),('zIndex','99'),('pos','0.59 0.64'),('size','0.16 0.045833333333333'),('text',EXPRESSION)]
    for key,value in props: ET.SubElement(extra,key).text=value


def test_bound_extra_is_scoped_and_exactly_preserves_native_style():
    for ratio,mode,help,ra,font in itertools.product(['4-3','4-3-auto'],['on','mixed','play-stats'],[True,False],['off','on'],['small','default','large','xlarge']):
        state=resolve(ratio=ratio,metadata=mode,help=help,achievements=ra,font=font)
        native=state['text','md_gametime']
        assert native['visible']=='false'
        extra=dict(state['text',NAME])
        assert extra.pop('text')==EXPRESSION
        assert extra==dict(native,visible='true')
    root=ET.parse(ROOT/'aspect-ratio-4-3.xml').getroot()
    extra=root.find(f".//text[@name='{NAME}']")
    assert extra.attrib=={'name':NAME,'extra':'true'}
    assert root.find('.//boundtext') is None  # Native schema uses text + text_binding.


def test_only_approved_replacement_changes_whole_ratio_tree():
    from test_c64 import parse,structure
    old=parse(subprocess.check_output(['git','show','fdc9d6a:aspect-ratio-4-3.xml'],cwd=ROOT))
    approved_transform(old)
    assert structure(old)==structure(parse((ROOT/'aspect-ratio-4-3.xml').read_bytes()))


def test_no_extra_outside_enabled_detailed_4_3():
    for ratio,mode,view,ra in itertools.product(['4-3','4-3-auto','16-9','16-10','3-2','1-1'],['off','on','mixed','play-stats'],['detailed','basic','system'],['off','on']):
        if ratio in ['4-3','4-3-auto'] and mode!='off' and view=='detailed':continue
        assert ('text',NAME) not in resolve(ratio=ratio,metadata=mode,view=view,achievements=ra)


def test_preview_renders_replacement_not_hidden_native():
    import sys
    sys.path.insert(0,str(ROOT/'tools'))
    import render_metadata_panel as preview
    for height in [240,480]:
        _,records=preview.render(height,'commodore-64')
        assert 'md_gametime' not in records
        assert records[NAME]['text']=='2h 35m'
        assert records[NAME]['display']=='2h 35m'

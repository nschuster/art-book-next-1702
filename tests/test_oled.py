"""OLED-only empty-state colors; native rating and per-game extras bindings."""
import sys
import xml.etree.ElementTree as ET
from test_metadata import ROOT
from test_ra_bar import helper
sys.path.insert(0, str(ROOT/'tools'))
import render_metadata_panel as base


def approved_oled_transform(root, path):
    """Exactly permitted additions for strict historical tree comparisons."""
    if path != 'theme.xml':
        return
    include = root.find("include[.='${themeCustomizationsPath}colors.xml']")
    block = ET.Element('include')
    block.text = './progress-colors.xml'
    root.insert(list(root).index(include)+1, block)
    rating = root.find("./view/rating[filledPath]")
    ET.SubElement(rating, 'unfilledColor', {'ifSubset':'color-scheme:oled'}).text = '777777'


def test_progress_defaults_live_in_post_palette_include_for_native_prepass():
    from test_c64 import parse
    root = parse((ROOT/'theme.xml').read_bytes())
    includes = [n.text for n in root.findall('include')]
    assert includes.index('./progress-colors.xml') > includes.index('${themeCustomizationsPath}colors.xml')
    assert not root.findall('./variables/raProgressTrackColor')
    defaults = ET.parse(ROOT/'progress-colors.xml').getroot()
    assert defaults.findtext('formatVersion') == '7'
    assert [(n.attrib, n.text) for n in defaults.findall('./variables/raProgressTrackColor')] == [
        ({}, '${gamelistListTextlistBackgroundColor}'), ({'ifSubset':'color-scheme:oled'}, '303030')]


def test_oled_empty_star_only_gets_muted_gray():
    state, values = base.resolve('oled')
    assert state['rating','md_rating'].get('unfilledColor') == '777777'
    assert state['rating','md_rating']['color'] == 'ffffff33'
    assert values['gamelistListTextlistBackgroundColor'] == '000000'
    for scheme in base.registered_schemes():
        if scheme != 'oled':
            state, _ = base.resolve(scheme)
            assert 'unfilledColor' not in state['rating','md_rating']


def test_track_uses_dedicated_variable_resolved_after_custom_palette(tmp_path):
    for scheme in base.registered_schemes():
        _, values = base.resolve(scheme)
        assert values.get('raProgressTrackColor') == ('303030' if scheme == 'oled' else values['gamelistListTextlistBackgroundColor'])
    custom = tmp_path/'colors.xml'
    custom.write_text('<theme><variables><gamelistListTextlistBackgroundColor>123456</gamelistListTextlistBackgroundColor></variables></theme>')
    assert base.resolve('custom', custom_palette=custom)[1]['raProgressTrackColor'] == '123456'
    data=dict(ID=1,NumAchievements=40,NumAwardedToUser=12,NumAwardedToUserHardcore=12)
    xml=ET.fromstring(helper.render(data,{},tmp_path))
    assert xml.findtext("./view/image[@name='ra_progress_track']/color") == '${raProgressTrackColor}'

"""Native controller status theme contract, not a live device/emulator test."""
import itertools
import os
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET
import pytest
from test_metadata import ROOT, resolve
from test_c64 import parse, structure

PIN = '4adf26b43900d1a33887af6d8af3da2e99e398a5'
BASE = 'a22c581b08e55ec34d4cb061f44bb6ccd4ef24cb'
REGISTRATION = '''<subset name="controller-status" displayName="Controller Status Icons">
<include name="on" displayName="On" /><include name="off" displayName="Off" />
</subset>'''
KEY = ('controllerActivity', 'controllerActivity')
RATIOS = ['4-3', '4-3-auto', '16-9', '16-9-auto', '16-10', '16-10-auto',
          '3-2', '3-2-auto', '1-1', '1-1-auto', '720-square-auto']


def approved_controller_transform(root):
    """Only the exact new registration/include, before the final menu overrides."""
    index = list(root).index(root.find("subset[@name='menu-font-size']"))
    root.insert(index, ET.fromstring(REGISTRATION))
    root.insert(index+1, ET.fromstring('<include>./controller-status.xml</include>'))


def test_registration_default_and_exact_preservation():
    actual = parse((ROOT/'theme.xml').read_bytes())
    assert structure(actual.find("subset[@name='controller-status']")) == structure(ET.fromstring(REGISTRATION))
    before = parse(subprocess.check_output(['git', 'show', BASE+':theme.xml'], cwd=ROOT))
    approved_controller_transform(before)
    from test_canvas_carousel import approved_canvas_transform
    approved_canvas_transform(before)
    assert structure(actual) == structure(before)


@pytest.mark.parametrize('ratio', RATIOS)
def test_resolved_on_off_and_other_screen_components_unchanged(ratio):
    for help_on, font in itertools.product([False, True], ['small', 'default', 'large', 'xlarge']):
        on = resolve(view='screen', ratio=ratio, help=help_on, font=font)
        off = resolve(view='screen', ratio=ratio, help=help_on, font=font, controllers='off')
        assert on[KEY]['visible'] == 'true'
        assert off[KEY]['visible'] == 'false'
        assert on[KEY]['pos'] == '0.03125 0.041666666666667'
        assert on[KEY]['size'] == '0.4 0.041666666666667'
        assert on[KEY]['imagePath'] == './_inc/images/controller-status.svg'
        assert on[KEY]['color'] == '${systemIndicatorColor}'
        assert on[KEY]['horizontalAlignment'] == 'left'
        assert on[KEY]['itemSpacing'] == '0.00625'
        off[KEY]['visible'] = 'true'
        assert on == off
        del on[KEY]
        old = resolve(view='screen', ratio=ratio, baseline=True)
        del old[KEY]
        assert on == old


@pytest.mark.parametrize('ratio', RATIOS)
def test_toggle_preserves_all_other_views_and_ra(ratio):
    for view, achievements, metadata in itertools.product(
            ['system', 'basic', 'detailed', 'menu'], ['off', 'on'], ['on', 'mixed', 'play-stats', 'off']):
        kw = dict(ratio=ratio, view=view, achievements=achievements, metadata=metadata)
        assert resolve(**kw, controllers='on') == resolve(**kw, controllers='off')


def test_geometry_at_both_crt_sizes():
    props = resolve(view='screen')[KEY]
    x, y = map(float, props['pos'].split())
    _, height = map(float, props['size'].split())
    for w, h in [(640, 480), (320, 240)]:
        assert (round(x*w), round(y*h), round(height*h)) == ((20,20,20) if h==480 else (10,10,10))
        # Eight pads without optional battery text remain in the left half.
        assert x*w + 8*height*h + 7*float(props['itemSpacing'])*w < .5*w


def test_native_source_contract_and_supported_properties():
    source = Path(os.environ.get('BATOCERA_ES_SOURCE', '/tmp/ra-es-source'))
    if not (source/'.git').exists(): pytest.skip('Set BATOCERA_ES_SOURCE to pinned checkout')
    def read(path):
        return subprocess.check_output(['git', 'show', PIN+':'+path], cwd=source, text=True)
    component = read('es-core/src/components/ControllerActivityComponent.cpp')
    assert 'InputManager::getInstance()->lastKnownPlayersDeviceIndexes()' in component
    assert 'if (pad.index < 0)' in component
    assert 'if (!isVisible())' in component
    assert 'Settings::ShowControllerActivity()' in component
    assert 'Settings::ShowControllerBattery()' in component
    assert 'mView = CONTROLLERS;' in component
    assert 'mPadTexture = TextureResource::get' in component
    assert 'mSpacing' in component and 'Renderer::getScreenWidth()' in component
    window = read('es-core/src/Window.cpp')
    assert 'applyTheme(theme, "screen", "controllerActivity"' in window
    assert 'Settings::ShowControllerActivity() && mControllerActivity != nullptr' in window
    assert '(mGuiStack.size() < 2 || !Renderer::isSmallScreen())' in window
    assert 'IMPLEMENT_STATIC_BOOL_SETTING(ShowControllerActivity, true)' in read('es-core/src/Settings.cpp')
    menu = read('es-app/src/guis/GuiControllersSettings.cpp')
    assert '_("SHOW CONTROLLER ACTIVITY")' in menu
    assert '_("SHOW CONTROLLER BATTERY LEVEL")' in menu
    schema = read('es-core/src/ThemeData.cpp').split('{ "controllerActivity", {',1)[1].split('{ "batteryIndicator", {',1)[0]
    allowed = set(re.findall(r'\{ "(\w+)",', schema))
    root = ET.parse(ROOT/'controller-status.xml').getroot()
    assert len(root) == 1 and root[0].attrib == {'name':'screen'}
    for element in root[0]:
        assert element.tag == 'controllerActivity'
        assert element.attrib == {'name':'controllerActivity'}
        assert {p.tag for p in element} <= allowed
        assert not ({p.tag for p in element} & {'networkIcon','planemodeIcon','full','incharge'})
    path = ROOT / resolve(view='screen')[KEY]['imagePath']
    assert ET.parse(path).getroot().attrib['viewBox'] == '0 0 20 20'

"""Native controller status theme contract, not a live device/emulator test."""
import itertools
import os
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET
import pytest
from test_metadata import ROOT, resolve as base_resolve
import test_metadata
from unittest.mock import patch as mock_patch
import struct


def resolve(*args, small_screen=True, **kwargs):
    """Ordered resolver plus native tinyScreen property filtering."""
    original = test_metadata.source
    def source(path, baseline=False):
        data = original(path, baseline)
        if path.removeprefix('./') != 'controller-status.xml':
            return data
        root = ET.fromstring(data)
        for parent in root.iter():
            for node in list(parent):
                if node.get('tinyScreen') not in (None, str(small_screen).lower()):
                    parent.remove(node)
        return ET.tostring(root)
    with mock_patch.object(test_metadata, 'source', source):
        return base_resolve(*args, **kwargs)


def f32(value):
    return struct.unpack('f', struct.pack('f', value))[0]
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
        assert float(on[KEY]['size'].split()[0]) == 0.4
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


@pytest.mark.parametrize('font', ['small', 'default', 'large', 'xlarge'])
@pytest.mark.parametrize('small_screen', [True, False])
@pytest.mark.parametrize('w,h', [(640, 480), (320, 240)])
def test_geometry_at_both_crt_sizes(font, small_screen, w, h):
    props = resolve(view='screen', font=font, small_screen=small_screen)[KEY]
    panel = resolve(view='system', font=font)[('stackpanel', 'system-indicators')]
    clock = next(p for tag, name, p in panel['children'] if name == 'system-clock')
    clock_request = int(f32(f32(float(clock['fontSize'])) * min(w, h)))
    icon = f32(f32(float(props['size'].split()[1])) * h)
    battery_request = int(f32(icon * f32(.55 if small_screen else .70)))
    assert battery_request == clock_request
    x, y = map(float, props['pos'].split())
    assert (round(x*w), round(y*h)) == ((20,20) if h == 480 else (10,10))
    # Source renderer stride; conservative 4-em budget for "100% ",
    # not an asserted native glyph measurement. Reserve right quarter.
    # Both fonts undergo the same normal (not menu) native FontScale.
    scaled_font = int(battery_request * (1.5 if h < 320 else 1.31))
    spacing = float(props['itemSpacing']) * w
    available = (.75 - x) * w
    stride = icon + 2*spacing + 4*scaled_font
    assert 2*stride <= available
    assert 8*stride > available  # component width does not clip the row
    assert 8*(icon+spacing)-spacing <= available


@pytest.mark.parametrize('palette', ['default', 'light', 'steam-os', 'snes',
                                    'famicom', 'oled', 'commodore-64', 'custom'])
def test_activity_and_hotkey_use_selected_palette(palette):
    # Ordered theme includes resolve the actual screen component, not a detached
    # XML fragment. These palette variables are declared in colors.xml, with
    # custom overrides loaded subsequently by theme.xml.
    props = resolve(view='screen')[KEY]
    variables = {}
    for group in ET.parse(ROOT/'colors.xml').getroot().findall('variables'):
        if palette in group.get('ifSubset', '').split(':')[1].split('|'):
            variables.update({p.tag: (p.text or '').strip() for p in group})
    assert variables
    for state in ('activityColor', 'hotkeyColor'):
        assert props.get(state) == '${menuSelectorColor}'
        selected = variables[props[state][2:-1]]
        assert re.fullmatch('[0-9a-fA-F]{6}', selected)
        assert selected.lower() != variables['systemIndicatorColor'].lower()
        assert selected.lower() != 'ff3675'
    # Custom palettes use their existing selector token without a second setting.
    if palette == 'custom':
        variables['menuSelectorColor'] = '23abcd'
        assert variables[props['activityColor'][2:-1]] == '23abcd'


def test_native_battery_font_is_height_derived_not_menu_or_text_themed():
    source = Path(os.environ.get('BATOCERA_ES_SOURCE', '/tmp/ra-es-source'))
    if not (source/'.git').exists():
        pytest.skip('Set BATOCERA_ES_SOURCE to pinned checkout')
    def read(path):
        return subprocess.check_output(['git', 'show', PIN+':'+path], cwd=source, text=True)
    component = read('es-core/src/components/ControllerActivityComponent.cpp')
    assert 'float szH = mSize.y();' in component
    assert 'Font::get(szH * (Renderer::isSmallScreen() ? 0.55f : 0.70f), FONT_PATH_REGULAR)' in component
    assert 'ThemeMenu' not in component and 'getFromTheme' not in component
    assert 'fontSize' not in component and 'fontPath' not in component
    assert 'padcolor = mActivityColor;' in component
    assert 'padcolor = mHotkeyColor;' in component
    assert 'mPads[idx].batteryText->setColor(padcolor);' in component
    schema = read('es-core/src/ThemeData.cpp').split('{ "controllerActivity", {', 1)[1].split('{ "batteryIndicator", {', 1)[0]
    assert 'fontSize' not in schema and 'fontPath' not in schema
    assert 'bool menuScaling = false' in read('es-core/src/resources/Font.h')
    # Authorized icon enlargement, but no unsupported independent font control.
    props = resolve(view='screen')[KEY]
    assert not {'fontSize', 'fontPath'} & props.keys()
    theme = read('es-core/src/ThemeData.cpp')
    assert 'node.attribute("tinyScreen")' in theme
    assert 'Renderer::isSmallScreen() && tinyScreenAttr == "false"' in theme
    assert 'pushClipRect' not in component


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

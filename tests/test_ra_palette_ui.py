"""Read-only installed palette selection and actual SDL rendering regressions."""
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

SOURCE = Path(__file__).resolve().parents[1] / 'scripts/retroachievements'
sys.path.insert(0, str(SOURCE))
import progress_ui


def fixture(tmp_path, selection='commodore-64', current=None):
    root = tmp_path / 'userdata'
    es = root / 'system/configs/emulationstation'
    es.mkdir(parents=True)
    current_setting = f'<string name="subset.color-scheme" value="{current}"/>' if current is not None else ''
    (es / 'es_settings.cfg').write_text('<config><string name="ThemeSet" value="renamed"/>' + current_setting + '</config>')
    (es / 'themesettings').mkdir()
    (es / 'themesettings/renamed.cfg').write_text('subset.color-scheme=' + selection + '\r')
    theme = root / 'themes/renamed'
    theme.mkdir(parents=True)
    for name in ('theme.xml', 'colors.xml'):
        shutil.copy(SOURCE.parents[1] / name, theme / name)
    return root, es, theme


def test_palette_api_exists():
    assert callable(getattr(progress_ui, 'load_palette', None)), 'UI must resolve the active installed palette'


def test_selection_readonly_and_launch_refresh(tmp_path):
    root, es, theme = fixture(tmp_path)
    before = {p: p.read_bytes() for p in es.rglob('*') if p.is_file()}
    palette = progress_ui.load_palette(root)
    assert palette['background'] == (41, 41, 41)
    assert palette['text'] == (233, 225, 204)
    assert palette['track'] == (101, 81, 60)
    assert all(p.read_bytes() == content for p, content in before.items())
    (es / 'themesettings/renamed.cfg').write_text('subset.color-scheme=oled\r')
    assert progress_ui.load_palette(root)['background'] == (17, 17, 17)
    (es / 'themesettings/renamed.cfg').unlink()
    assert progress_ui.load_palette(root)['background'] == (17, 17, 17)


def test_safe_missing_malformed_and_custom(tmp_path):
    root, es, theme = fixture(tmp_path, 'custom')
    default = progress_ui.load_palette(tmp_path / 'missing')
    custom = root / 'theme-customizations/art-book-next/colors.xml'
    custom.parent.mkdir(parents=True)
    custom.write_text('<theme><variables><menuBackgroundColor>abcdef</menuBackgroundColor><helpTextColor>000000</helpTextColor></variables></theme>')
    assert progress_ui.load_palette(root)['background'] == (171, 205, 239)
    custom.write_text('<broken')
    assert progress_ui.load_palette(root) == default
    (es / 'es_settings.cfg').write_text('<config><string name="ThemeSet" value="../escape"/></config>')
    assert progress_ui.load_palette(root) == default


def test_installed_dummy_captures(tmp_path):
    root, es, theme = fixture(tmp_path)
    subprocess.run([sys.executable, str(SOURCE/'install.py'), '--data-root', str(root), '--ports-menu'], check=True, capture_output=True)
    installed = root/'system/retroachievements'
    assert (installed/'ui_palette.py').is_file()
    state = installed/'progress.json'
    state.write_text(json.dumps(dict(schema=1,state='syncing',updated_at=time.time(),total=40,completed=12,system='Super Nintendo',game='Super Mario World',updated=12,pending=28)))
    env = dict(os.environ, SDL_VIDEODRIVER='dummy')
    for name, bg in [('commodore-64', (41,41,41)), ('oled',(17,17,17)), ('snes',(20,14,38))]:
        (es/'themesettings/renamed.cfg').write_text('subset.color-scheme='+name+'\r')
        for width,height in [(640,480),(320,240)]:
            output = tmp_path/f'{name}-{width}.bmp'
            subprocess.run([sys.executable,'-S',str(installed/'progress_ui.py'),'--data-root',str(installed),'--windowed','--width',str(width),'--height',str(height),'--frames','1','--screenshot',str(output)],check=True,env=env,capture_output=True)
            data=output.read_bytes()
            assert tuple(reversed(data[54:57])) == bg
            assert len(set(data[54:])) > 6

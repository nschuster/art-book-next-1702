"""Comic selection: ordered theme resolution and pinned native contracts, not device QA."""
import itertools
import re
import subprocess
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path
from unittest.mock import patch

import pytest
import test_metadata
from test_metadata import ROOT
from test_c64 import parse, structure

BASE = 'f376e95f211fd345e87a129d8439a47345aff54e'
PIN = '4adf26b43900d1a33887af6d8af3da2e99e398a5'
COMIC = '${themePath}/_inc/systems/logos-comic/${system.theme}.png'
GUARD = 'exists(${themePath} + "/_inc/systems/logos-comic/" + ${system.theme} + ".png")'
VISIBLE = '!exists("${themePath}/_inc/systems/logos/" + {system:theme} + ".svg") && !exists("${themePath}/_inc/systems/logos-comic/" + {system:theme} + ".png")'
RATIOS = ['4-3', '16-9', '16-10', '3-2', '1-1', '720-square-auto']


def approved_comic_transform(root):
    """Exact additive contract for historical structural preservation tests."""
    subset = root.find("subset[@name='system-logos']")
    if subset is not None:
        ET.SubElement(subset, 'include', name='comic', displayName='Comic (Retrorama)')
    for image in root.findall('./view/image'):
        if image.find("path[.='./_inc/systems/logos/${system.theme}.svg']") is not None:
            path = ET.Element('path', {'ifSubset': 'system-logos:comic', 'if': GUARD})
            path.text = './_inc/systems/logos-comic/${system.theme}.png'
            index = list(image).index(image.findall('path')[-1]) + 1
            image.insert(index, path)
            color = ET.Element('color', {'ifSubset': 'system-logos:comic', 'if': GUARD})
            color.text = 'ffffff'
            if image.get('name') == 'canvas-logo':
                image.append(color)
            else:
                image.insert(max(index, list(image).index(image.find('color'))) + 1, color)
    for text in root.findall('./view/text'):
        if text.get('name') in ('system-name', 'canvas-name') and 'exists' in text.findtext('visible', ''):
            visible = ET.Element('visible', {'ifSubset': 'system-logos:comic'})
            visible.text = VISIBLE
            text.insert(list(text).index(text.find('visible')) + 1, visible)


@lru_cache(None)
def old_source(path):
    return subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)


def resolve(*, logos='comic', available=True, baseline=False, **kwargs):
    """Extend shared ordered resolver with subset and parse-time exists filters.

    This intentionally does NOT discard nonexistent PATH values: guards must
    protect the fallback, rather than a test resolver silently doing it for us.
    """
    def source(path, unused=False):
        data = old_source(path) if baseline else (ROOT / path).read_bytes()
        root = ET.fromstring(re.sub(rb'&(?!#?\w+;)', b'&amp;', data))
        for parent in root.iter():
            for node in list(parent):
                clauses = node.get('ifSubset', '').split(',')
                logo_clauses = [c for c in clauses if c.startswith('system-logos:')]
                if any(logos not in c.split(':')[1].split('|') for c in logo_clauses):
                    parent.remove(node)
                    continue
                if logo_clauses:
                    node.set('ifSubset', ','.join(c for c in clauses if c not in logo_clauses))
                if node.get('if') == GUARD and not available:
                    parent.remove(node)
        return ET.tostring(root)
    with patch.object(test_metadata, 'source', source):
        return test_metadata.resolve(**kwargs)


def test_registration_and_exact_additive_xml():
    for path in ['theme.xml', 'console-showcase.xml']:
        expected = parse(old_source(path))
        approved_comic_transform(expected)
        assert structure(parse((ROOT / path).read_bytes())) == structure(expected)
    subset = parse((ROOT/'theme.xml').read_bytes()).find("subset[@name='system-logos']")
    assert subset is not None
    assert [(n.get('name'), n.get('displayName')) for n in subset] == [
        ('default', 'Default'), ('custom', 'Custom'), ('comic', 'Comic (Retrorama)')]


@pytest.mark.parametrize('ratio', RATIOS)
@pytest.mark.parametrize('art', ['default', 'noir', 'nintendont', 'circuit', 'outline', 'custom', 'custom-fullscreen'])
def test_large_consumers_and_fallback_preserve_other_components(ratio, art):
    for view, showcase in [('system', 'off'), ('system', 'on'), ('basic', 'off'), ('detailed', 'off')]:
        kw = dict(ratio=ratio, system_art=art, view=view, showcase=showcase)
        old = resolve(logos='default', baseline=True, **kw)
        missing = resolve(available=False, **kw)
        present = resolve(available=True, **kw)
        targets = {key for key, props in old.items() if props.get('path') == './_inc/systems/logos/${system.theme}.svg'}
        assert targets
        for key in targets:
            assert present[key]['path'] == './_inc/systems/logos-comic/${system.theme}.png', (kw, key)
            assert present[key]['color'] == 'ffffff', (kw, key)
            assert missing[key] == old[key], (kw, key)
        for key in old.keys() - targets:
            if key in [('text', 'system-name'), ('text', 'canvas-name')]:
                # Canvas intentionally hides the ordinary system-name overlay.
                if old[key].get('visible') == 'false':
                    assert present[key] == old[key]
                else:
                    assert present[key]['visible'] == VISIBLE
            else:
                assert present[key] == old[key], (kw, key)
                assert missing[key] == old[key], (kw, key)


@pytest.mark.parametrize('logos', ['default', 'custom'])
def test_non_target_modes_exact_resolved_preservation(logos):
    for ratio, view, art, showcase in itertools.product(RATIOS, ['system','basic','detailed','menu','screen'], ['default','custom-fullscreen'], ['off','on']):
        kw = dict(logos=logos, ratio=ratio, view=view, system_art=art, showcase=showcase)
        assert resolve(**kw) == resolve(baseline=True, **kw)


@pytest.mark.parametrize('normal_exists,comic_exists', list(itertools.product([False,True], repeat=2)))
def test_text_fallback_truth_table(normal_exists, comic_exists):
    for showcase, name in [('off','system-name'), ('on','canvas-name')]:
        expression = resolve(view='system', showcase=showcase, available=comic_exists)['text',name]['visible']
        assert '{system:theme}' in expression, 'Native BOOLEAN needs a binding, not an unevaluated expression'
        expression = expression.replace('" + {system:theme} + "', 'snes')
        expression = re.sub(r'exists\("([^\"]+)"\)', lambda m: str(comic_exists if 'logos-comic/' in m[1] else normal_exists), expression)
        assert eval(expression.replace('!', ' not ').replace('&&', ' and ').strip()) == (not normal_exists and not comic_exists)


def test_pinned_native_filter_and_path_semantics():
    source = Path('/tmp/ra-es-source')
    if not (source/'.git').exists():
        pytest.skip('Pinned native frontend source unavailable')
    def read(path):
        return subprocess.check_output(['git','show',f'{PIN}:{path}'], cwd=source, text=True)
    theme = read('es-core/src/ThemeData.cpp')
    filters = theme.split('bool ThemeData::parseFilterAttributes',1)[1]
    assert 'node.attribute("if")' in filters
    assert 'Utils::MathExpr::evaluate(ifAttribute.c_str(), &mEvaluatorVariables)' in filters
    paths = theme.split('case PATH:',1)[1].split('\n\tdefault:',1)[0]
    assert 'if (ResourceManager::getInstance()->fileExists(path))' in paths
    assert 'element.properties[name] = path;' in paths
    math = read('es-core/src/utils/MathExpr.cpp')
    assert '{ "exists", 1 }' in math

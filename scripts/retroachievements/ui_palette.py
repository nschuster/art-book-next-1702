"""Read-only Art Book palette adapter, not a general ES theme interpreter.

Batocera 42 ES 4adf26b43900d1a33887af6d8af3da2e99e398a5:
Current subset.color-scheme is persisted in es_settings.cfg. GuiMenu.cpp
keeps older per-theme snapshots in themesettings/<ThemeSet>.cfg (CR-separated)
when switching themes; these are fallback only. ThemeColorSet is unrelated.
Unsupported theme expressions or malformed custom palettes fail closed.
"""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

DEFAULT = dict(background=(42, 40, 37), text=(233, 225, 204),
               track=(78, 74, 66), progress=(193, 177, 140), divider=(109, 101, 85))


def _read(path):
    with Path(path).open('rb') as stream:
        data = stream.read(262145)
    if len(data) > 262144 or b'<!DOCTYPE' in data or b'<!ENTITY' in data:
        raise ValueError('unsupported document')
    return data.decode('utf-8-sig')


def _variables(path, selection, values):
    tree = ET.fromstring(_read(path))
    for block in tree.findall('variables'):
        condition = block.get('ifSubset')
        if condition and condition != 'color-scheme:' + selection:
            key, sep, choices = condition.partition(':')
            if key != 'color-scheme' or selection not in choices.split('|'):
                continue
        if block.get('if'):
            raise ValueError('unsupported expression')
        for child in block:
            if child.attrib:
                raise ValueError('unsupported expression')
            values[child.tag] = (child.text or '').strip()


def load_palette(root=Path('/userdata')):
    """Snapshot at window launch; never write ES settings or credential files."""
    try:
        root = Path(root)
        es = root / 'system/configs/emulationstation'
        settings = {node.get('name'): node.get('value', '')
                    for node in ET.fromstring(_read(es/'es_settings.cfg')).iter('string')}
        name = settings.get('ThemeSet', '')
        if not name or name in ('.', '..') or Path(name).name != name or '\\' in name:
            raise ValueError('invalid theme')
        selection = settings.get('subset.color-scheme', '')
        saved = es / 'themesettings' / (name + '.cfg')
        if not selection and saved.is_file():
            for line in _read(saved).splitlines():
                key, sep, value = line.partition('=')
                if key == 'subset.color-scheme' and value:
                    selection = value
        # Same last-found precedence as pinned ThemeData::getThemeSets.
        roots = [root/'themes']
        if root == Path('/userdata'):
            roots.append(Path('/usr/share/emulationstation/themes'))
        roots.append(es/'themes')
        if root == Path('/userdata'):
            roots.append(Path('/etc/emulationstation/themes'))
        theme = next((base/name for base in reversed(roots) if (base/name).is_dir()), None)
        if theme is None:
            raise ValueError('missing theme')
        # Native pugixml accepts unescaped && in unrelated condition attributes;
        # only parse the palette registration, never evaluate theme expressions.
        registration = re.search(r'<subset\s+name="color-scheme"[^>]*>.*?</subset>', _read(theme/'theme.xml'), re.S)
        if registration is None:
            raise ValueError('unsupported theme')
        subset = ET.fromstring(registration.group())
        choices = [node.get('name') for node in subset.findall('include')]
        selection = selection or choices[0]
        if selection not in choices:
            raise ValueError('unknown selection')
        values = {}
        _variables(theme/'colors.xml', selection, values)
        if selection == 'custom':
            _variables(root/'theme-customizations/art-book-next/colors.xml', selection, values)
        def color(key):
            value = values[key]
            for _ in range(8):
                if not value.startswith('${') or not value.endswith('}'):
                    break
                value = values[value[2:-1]]
            if not re.fullmatch(r'[0-9a-fA-F]{6}([0-9a-fA-F]{2})?', value):
                raise ValueError('invalid color')
            rgb = tuple(int(value[i:i+2],16) for i in (0,2,4))
            alpha = int(value[6:8],16) if len(value)==8 else 255
            return tuple(round((c*alpha+b*(255-alpha))/255) for c,b in zip(rgb, background))
        background = (0,0,0)
        background = color('menuBackgroundColor')
        # Help text is paired with the same dark menu surface in Art Book.
        text = color('helpTextColor')
        track = color('menuSelectorColor')
        progress = color('gamelistListTextlistSelectedColor')
        # Light's black list accent belongs on its light sidebar, not its dark
        # menu. Use the palette's menu-readable text when that accent disappears.
        def contrast(a, b):
            def luminance(rgb):
                channels = [v / 255 for v in rgb]
                linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in channels]
                return sum(v*w for v, w in zip(linear, (.2126, .7152, .0722)))
            lo, hi = sorted((luminance(a), luminance(b)))
            return (hi + .05) / (lo + .05)
        if min(contrast(progress, background), contrast(progress, track)) < 3:
            progress = text
        return dict(background=background, text=text, track=track,
                    divider=track, progress=progress)
    except (OSError, ValueError, UnicodeError, ET.ParseError, KeyError, IndexError):
        return DEFAULT.copy()

"""Read-only system/gamelist discovery for the optional Ports hours refresh.

Uses native names rather than theme aliases. Mirrors base-config precedence and
ROM-local gamelist priority; standard ROM-directory names are a fallback only
when no systems configuration exists. No files or credentials are modified.
"""
from pathlib import Path
import re
import xml.etree.ElementTree as ET


def discover(root, stock=Path('/usr/share/emulationstation')):
    root, stock = Path(root), Path(stock)
    user = root / 'system/configs/emulationstation'
    candidates = [user / 'es_systems_custom.cfg', user / 'es_systems.cfg', stock / 'es_systems.cfg']
    if root == Path('/userdata'):
        candidates.append(Path('/etc/emulationstation/es_systems.cfg'))
    base = next((p for p in candidates if p.is_file()), None)
    systems = {}
    if base is None:
        systems = {p.parent.name: p.parent for p in sorted((root / 'roms').glob('*/gamelist.xml'))}
    else:
        files = [base]
        for directory in dict.fromkeys((user, stock)):
            files += sorted(directory.glob('es_systems_*.cfg'))
        try:
            for config in files:
                tree = ET.parse(config).getroot()
                if tree.tag != 'systemList':
                    raise ValueError('invalid systems config')
                for node in tree.findall('system'):
                    name = (node.findtext('name') or '').strip()
                    path = node.find('path')
                    if path is not None:
                        value = (path.text or '').strip()
                        if value:
                            # Native ~ is the userdata/system home, not this process host's home.
                            value = str(root / 'system') + value[1:] if value.startswith('~/') else value
                            if root != Path('/userdata') and value.startswith('/userdata/'):
                                value = str(root / value[len('/userdata/'):])
                            systems[name] = Path(value)
                        else:
                            systems.pop(name, None)
        except ET.ParseError as error:
            raise ValueError('invalid systems config') from error
    mappings = []
    for name, directory in sorted(systems.items()):
        if not re.fullmatch(r'[A-Za-z0-9_-]+', name) or not directory.is_absolute():
            continue
        local = directory / 'gamelist.xml'
        saved = user / 'gamelists' / name / 'gamelist.xml'
        path = local if local.is_file() else saved
        if path.is_file():
            mappings.append(f'{name}={path}')
    return mappings

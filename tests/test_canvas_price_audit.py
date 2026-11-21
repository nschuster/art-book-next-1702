"""Independent source audit: never promote the borrowed PSX price error."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def test_original_playstation_japan_price_corrects_imported_source():
    data = json.loads((ROOT / '_inc/canvas-hardware/specs.json').read_text())
    price = data['systems']['psx']['fields']['Price']
    assert price['value'] == 'JP ¥39,800'
    assert any('videogameconsolelibrary.com' in data['sources'][key]['url'] for key in price['sources'])
    for system in ['psx', 'ps1']:
        root = ET.parse(ROOT / f'_inc/canvas-hardware/specs/{system}.xml').getroot()
        assert root.findtext('variables/canvasPrice') == 'JP ¥39,800'


def test_c64_exact_price_has_independent_museum_corroboration():
    data = json.loads((ROOT / '_inc/canvas-hardware/specs.json').read_text())
    price = data['systems']['c64']['fields']['Price']
    assert price['value'] == 'US $595'
    assert any('computerhistory.org' in data['sources'][key]['url'] for key in price['sources'])

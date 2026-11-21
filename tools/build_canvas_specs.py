"""Generate additive runtime variables from reviewed facts; no source asset rewrites.
Usage: python tools/build_canvas_specs.py. Unknown is deliberate, not a guess.
"""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]


def build(root=ROOT):
    directory=root/'_inc/canvas-hardware'
    facts=json.loads((directory/'specs.json').read_text())
    manifest=json.loads((directory/'manifest.json').read_text())
    output=directory/'specs';output.mkdir(exist_ok=True)
    def write(name, fields):
        theme=ET.Element('theme');variables=ET.SubElement(theme,'variables')
        for key,value in fields.items():ET.SubElement(variables,'canvas'+key).text=value
        ET.indent(theme,space='   ')
        (output/f'{name}.xml').write_bytes(ET.tostring(theme,encoding='utf-8',xml_declaration=True)+b'\n')
    write('default',{key:'Unknown' for key in ['Architecture','CPU','RAM','Price']})
    for name,record in facts['systems'].items():write(name,{k:v['value'] for k,v in record['fields'].items()})
    for alias,target in manifest['aliases'].items():
        (output/f'{alias}.xml').write_bytes((output/f'{target}.xml').read_bytes())


if __name__=='__main__':build()

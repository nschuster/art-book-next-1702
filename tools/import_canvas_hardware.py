"""Development-only importer; selected, visually inspected Canvas hardware icons.
No network or runtime dependency. Crops transparent margins only; source metadata
is retained verbatim in the manifest (release YEAR, not fabricated exact dates).
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PIN = 'bf010295778b2756310edfc3a61fe5e20d31e5b9'
SYSTEMS = 'nes snes gb gba gbc c64 megadrive mastersystem gamegear psx ps2 psp n64 gc wii dreamcast saturn atari2600 amiga amstradcpc zxspectrum nds 3ds pcengine'.split()
ALIASES = {'genesis':'megadrive','gamecube':'gc','ps1':'psx','n3ds':'3ds','amiga500':'amiga','amiga1200':'amiga','snes-msu1':'snes'}
RIGHTS = 'Conflict: root LICENSE states CC0 1.0; README states CC-BY-NC-SA 2.0 and credits third-party artwork. Per-asset authorship/clearance is not established. Do not infer CC0 rights for these images; resolve rights before redistribution.'

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def variables(path, values):
    root = ET.Element('theme'); node = ET.SubElement(root,'variables')
    for key,value in values.items(): ET.SubElement(node,key).text=value
    ET.indent(root,space='   ')
    path.write_bytes(ET.tostring(root,encoding='utf-8',xml_declaration=True)+b'\n')

def import_assets(source, destination):
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==PIN
    destination.mkdir(parents=True,exist_ok=True); (destination/'metadata').mkdir(exist_ok=True)
    manifest={'repository':'https://github.com/Siddy212/canvas-es','revision':PIN,'rights':RIGHTS,
              'credit':'Canvas by Siddy212; README credits fagnerpc and PangolinWrestler among others. Individual icon attribution is not mapped.',
              'transform':'Decode WebP to RGBA PNG, crop only alpha bounding box; preserve all retained RGBA pixels. No recolor, no logo imports.',
              'aliases':ALIASES,'systems':{}}
    for system in SYSTEMS:
        relative=f'_inc/systems/carousel-icons-icons/{system}.webp'; original=source/relative
        im=Image.open(original).convert('RGBA'); crop=im.getbbox(); target=destination/f'{system}.png'; im.crop(crop).save(target)
        metadata_source=f'_inc/systems/metadata/{system}.xml'; xml=ET.parse(source/metadata_source).getroot().find('variables')
        metadata={key:xml.findtext(key) for key in ['systemName','systemManufacturer','systemReleaseYear','systemHardwareType']}
        values={'canvasHardware':'${themePath}/_inc/canvas-hardware/'+system+'.png','canvasManufacturer':metadata['systemManufacturer'] or 'Unknown','canvasYear':metadata['systemReleaseYear'] or 'Unknown','canvasType':metadata['systemHardwareType'] or 'Unknown','canvasMissing':'','canvasHasHardware':'true'}
        variables(destination/f'metadata/{system}.xml',values)
        manifest['systems'][system]={'source':relative,'source_sha256':digest(original),'url':f'https://raw.githubusercontent.com/Siddy212/canvas-es/{PIN}/{relative}',
          'asset':f'_inc/canvas-hardware/{system}.png','sha256':digest(target),'crop':crop,'metadata_source':metadata_source,'metadata_source_sha256':digest(source/metadata_source),'metadata':metadata,
          'depiction':'complete handheld/computer' if metadata['systemHardwareType'] in ['Computer','Portable'] else 'controller (not console chassis)'}
    for alias,target in ALIASES.items(): shutil.copyfile(destination/f'metadata/{target}.xml',destination/f'metadata/{alias}.xml')
    variables(destination/'metadata/default.xml',{'canvasHardware':'${themePath}/_inc/images/space.png','canvasManufacturer':'Unknown','canvasYear':'Unknown','canvasType':'Unknown','canvasMissing':'Artwork unavailable','canvasHasHardware':'false'})
    for name,target in [('LICENSE','SOURCE-LICENSE.txt'),('README.md','SOURCE-README.md')]: shutil.copyfile(source/name,destination/target)
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);args=parser.parse_args()
    import_assets(args.source,ROOT/'_inc/canvas-hardware')

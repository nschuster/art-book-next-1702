#!/usr/bin/env python3
"""Rebuild attributed Retrorama logo derivatives from pinned, hash-checked sources.
Requires Pillow. Does not write previews or change theme configuration.
"""
import argparse,hashlib,io,json,urllib.request
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
def rebuild(output,cache=None):
 manifest=json.loads((ROOT/'_inc/systems/logos-comic/manifest.json').read_text())
 output.mkdir(parents=True,exist_ok=True)
 for entry in manifest['assets']:
  url=manifest['raw_base']+entry['source_path']
  cached=cache/Path(entry['source_path']).name if cache else None
  if cached and cached.exists():data=cached.read_bytes()
  else:
   with urllib.request.urlopen(url,timeout=60) as r:data=r.read()
  if hashlib.sha256(data).hexdigest()!=entry['source_sha256']:raise ValueError('Source hash mismatch: '+entry['source_path'])
  im=Image.open(io.BytesIO(data)).convert('RGBA')
  im=im.crop(im.getchannel('A').getbbox())
  im.thumbnail((1024,512),Image.Resampling.LANCZOS)
  framed=Image.new('RGBA',(im.width+4,im.height+4));framed.alpha_composite(im,(2,2))
  target=output/entry['file'];framed.save(target,optimize=True)
  if hashlib.sha256(target.read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('Rendered hash differs (check Pillow version): '+entry['file'])
 return len(manifest['assets'])
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'_inc/systems/logos-comic');parser.add_argument('--cache',type=Path)
 args=parser.parse_args();print('Verified and rebuilt',rebuild(args.output,args.cache),'comic logos')

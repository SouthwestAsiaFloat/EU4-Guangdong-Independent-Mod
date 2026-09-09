#!/usr/bin/env python3
"""Export original imagegen artwork to native UI sizes, preserving source alpha.
No semantic art edits. Append one estate frame; retain every upstream atlas pixel.
"""
from pathlib import Path
import hashlib,json
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
MOD=ROOT/'guangdong_independent_practice'
GAME=Path.home()/'Library/Application Support/Steam/steamapps/common/Europa Universalis IV'
DEST=MOD/'gfx/interface/gdd_hak_government'
ART=ROOT/'planning/hakka_government_art'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 DEST.mkdir(parents=True,exist_ok=True);ART.mkdir(parents=True,exist_ok=True)
 manifest={'mode':'built-in imagegen; alpha-preserving size and DDS conversion','sprites':{},'estate_atlases':{}}
 for name in ['farmers','burghers','army']:
  p=HERE/'sources'/f'{name}.png';im=Image.open(p).convert('RGBA')
  assert im.getchannel('A').getextrema()==(0,255)
  manifest['sprites'][name]={'source':str(p.relative_to(ROOT)),'sha256':sha(p),'exports':{}}
  for size in [44,48,64,128]:
   result=im.resize((size,size),Image.Resampling.LANCZOS)
   out=DEST/f'{name}_{size}.dds';result.save(out)
   assert Image.open(out).convert('RGBA').tobytes()==result.tobytes()
   manifest['sprites'][name]['exports'][str(size)]={'path':str(out.relative_to(ROOT)),'sha256':sha(out)}
 # Vanilla atlas dimensions are not multiples of 15. Preserve their pixels and
 # append the nearest-width sixteenth cell, without resizing the original cells.
 for filename in ['estates_icons','estates_icons_colour-stroke']:
  src=GAME/f'gfx/interface/{filename}.dds';base=Image.open(src).convert('RGBA')
  cell=round(base.width/15);out=Image.new('RGBA',(base.width+cell,base.height))
  out.paste(base,(0,0))
  icon=Image.open(HERE/'sources/farmers.png').convert('RGBA').resize((cell,base.height),Image.Resampling.LANCZOS)
  out.paste(icon,(base.width,0));path=DEST/f'{filename}_16.dds';out.save(path)
  assert Image.open(path).crop((0,0,base.width,base.height)).tobytes()==base.tobytes()
  manifest['estate_atlases'][filename]={'source':str(src),'source_sha256':sha(src),'source_size':list(base.size),'size':list(out.size),'frames':16,'path':str(path.relative_to(ROOT)),'sha256':sha(path)}
 fontpath=next((p for p in [Path('/System/Library/Fonts/PingFang.ttc'),Path('/System/Library/Fonts/STHeiti Medium.ttc'),Path('/System/Library/Fonts/Supplemental/Arial Unicode.ttf')] if p.exists()),None)
 font=lambda size:ImageFont.truetype(str(fontpath),size) if fontpath else ImageFont.load_default()
 board=Image.new('RGB',(1200,570),(27,30,26));d=ImageDraw.Draw(board)
 d.text((45,25),'客家共和 · 三派徽记',font=font(30),fill=(226,205,151))
 d.text((45,69),'生产素材与缩小预览 · 非游戏截图',font=font(18),fill=(165,173,159))
 for i,(name,label) in enumerate([('farmers','乡社派'),('burghers','工商派'),('army','军府派')]):
  x=45+i*390;im=Image.open(HERE/'sources'/f'{name}.png').convert('RGBA')
  board.paste(im.resize((285,285),Image.Resampling.LANCZOS),(x,115),im.resize((285,285),Image.Resampling.LANCZOS))
  d.text((x+82,413),label,font=font(26),fill=(237,225,192))
  for j,size in enumerate([44,48,64]):
   icon=Image.open(DEST/f'{name}_{size}.dds').convert('RGBA');board.paste(icon,(x+j*92,468),icon)
   d.text((x+j*92,537),str(size)+' px',font=font(13),fill=(173,175,164))
 board.save(ART/'hakka_factions_asset_preview.png')
 (HERE/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 print('Exported 12 icon textures, 2 estate atlases, and preview board')
if __name__=='__main__':main()

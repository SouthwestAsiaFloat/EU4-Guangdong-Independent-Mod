"""Extract approved ImageGen atlas; resize and encode deterministic native DDS frames."""
from pathlib import Path
from collections import deque
import hashlib,json
from PIL import Image,ImageEnhance,ImageDraw,ImageFont
R=Path(__file__).resolve().parents[3]
A=Path(__file__).resolve().parent
O=R/'guangdong_independent_practice/gfx/interface/zhx_wangming'
S=A/'sources/wangming_atlas_v1.png'
im=Image.open(S).convert('RGBA')
# Actual generated sheet regions, inspected visually; preserve painted rims.
regions={'tribute':(12,36,509,526),'migration':(510,36,1014,526),'levy':(1016,36,1518,526),'banner':(40,592,1496,938)}
manifest={'source':str(S.relative_to(R)),'source_sha256':hashlib.sha256(S.read_bytes()).hexdigest(),'assets':{}}
for key,box in regions.items():
 pic=im.crop(box)
 if key!='banner':
  # Only flood the exterior black matte; dark paint inside the medallion is untouched.
  px=pic.load();w,h=pic.size;seen=set();q=deque([(x,0) for x in range(w)]+[(x,h-1) for x in range(w)]+[(0,y) for y in range(h)]+[(w-1,y) for y in range(h)])
  while q:
   x,y=q.popleft()
   if (x,y) in seen or x<0 or y<0 or x>=w or y>=h:continue
   seen.add((x,y))
   if max(px[x,y][:3])>42:continue
   px[x,y]=(0,0,0,0)
   q.extend([(x+1,y),(x-1,y),(x,y+1),(x,y-1)])
  pic=pic.crop(pic.getbbox()).resize((72,72),Image.Resampling.LANCZOS)
  dim=ImageEnhance.Brightness(ImageEnhance.Color(pic).enhance(.25)).enhance(.48)
  out=Image.new('RGBA',(144,72));out.paste(pic,(0,0));out.paste(dim,(72,0))
 else:
  out=pic.resize((344,93),Image.Resampling.LANCZOS)
 out.save(O/f'{key}.dds');out.save(O/f'{key}.png')
 manifest['assets'][key]={'crop':box,'size':out.size,'frames':1 if key=='banner' else 2,'sha256':hashlib.sha256((O/f'{key}.dds').read_bytes()).hexdigest()}
(A/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
# QA composition only, not a replacement screenshot or in-game art asset.
preview=Image.new('RGBA',(384,180),'#1e2830');preview.alpha_composite(Image.open(O/'banner.png'),(18,34))
for key,x in [('tribute',42),('migration',154),('levy',266)]:
 pic=Image.open(O/f'{key}.png').crop((0,0,72,72));preview.alpha_composite(pic,(x,36))
d=ImageDraw.Draw(preview)
f=ImageFont.truetype('/System/Library/Fonts/STHeiti Light.ttc',14)
for text,x in [('征召贡赋',50),('徙民实畿',162),('征调军伍',274)]:
 d.text((x,112),text,font=f,fill='#16130d')
 d.text((x,133),'本届可用',font=f,fill='#8bcc9c')
d.text((161,11),'王命',font=f,fill='#e5d6ab');d.text((125,155),'距下届：25年',font=f,fill='#e5d6ab')
preview.save(R/'planning/wangming/native_size_preview.png')
preview.resize((1152,540),Image.Resampling.NEAREST).save(R/'planning/wangming/native_size_preview_3x.png')
print('Exported 344x93 banner and three 72x72 two-frame buttons.')

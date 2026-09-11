from pathlib import Path
import re,json,sys,hashlib,zipfile
p=Path(sys.argv[1]); data=p.read_bytes()
if data[:2]==b'PK':
 with zipfile.ZipFile(p) as z:data=z.read('gamestate')
def block(raw,key):
 prefix = rb'(?m)^' if key in (b'countries', b'provinces') or key.startswith(b'-') else rb'(?m)^\t'
 m=re.search(prefix+re.escape(key)+rb'=\s*\{',raw)
 if not m:raise ValueError(key)
 a=raw.index(b'{',m.start());depth=0;quoted=False;escape=False
 for i in range(a,len(raw)):
  c=raw[i]
  if quoted:
   if escape:escape=False
   elif c==92:escape=True
   elif c==34:quoted=False
  elif c==34:quoted=True
  elif c==123:depth+=1
  elif c==125:
   depth-=1
   if depth==0:return raw[a+1:i]
 raise ValueError('unterminated')
countries=block(data,b'countries');provinces=block(data,b'provinces')
result={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'countries':{},'provinces':{}}
for tag in ['CZH','KRC']:
 c=block(countries,tag.encode())
 result['countries'][tag]={k:bool(re.search(k.encode()+rb'=',c)) for k in ['gdd_tianxia_picker_open','gdd_tianxia_unlawful_request_pending','gdd_tianxia_unlawful_demand_cooldown']}
 result['countries'][tag]['picker_values']=re.findall(rb'gdd_tianxia_picker_\w+=[^\r\n]+',c)
 result['countries'][tag]['picker_values']=[x.decode('ascii','replace') for x in result['countries'][tag]['picker_values']]
for pid in [703,4672,5113,5114,5115,5116,5206,5207,5212,5213]:
 c=block(provinces,str(-pid).encode())
 result['provinces'][str(pid)]={'owner':re.search(rb'(?m)^\s*owner="([A-Z0-9]+)"',c).group(1).decode(),'pending':b'gdd_tianxia_unlawful_request_pending=' in c}
print(json.dumps(result,indent=2))

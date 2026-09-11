"""Extract narrowly scoped runtime evidence from EU4 text/zip test saves."""
from pathlib import Path
import re, json, sys, hashlib, zipfile
p = Path(sys.argv[1]); raw = p.read_bytes(); data = raw
if raw[:2] == b'PK':
    with zipfile.ZipFile(p) as z: data = z.read('gamestate')
def block(raw, pattern):
    m = re.search(pattern, raw, re.M)
    if not m: return b''
    a = raw.index(b'{', m.start()); depth = 0; quoted = False; escaped = False
    for i in range(a, len(raw)):
        c = raw[i]
        if quoted:
            if escaped: escaped = False
            elif c == 92: escaped = True
            elif c == 34: quoted = False
        elif c == 34: quoted = True
        elif c == 123: depth += 1
        elif c == 125:
            depth -= 1
            if not depth: return raw[a+1:i]
    raise ValueError('Unterminated block')
def text(b): return b.decode('utf8', 'replace')
def flags(raw):
    return dict((text(k), text(v)) for k,v in re.findall(rb'^\t\t\t([a-zA-Z0-9_]+)=([^\r\n]+)', block(raw, rb'^\t\tflags=\{'), re.M))
cs = block(data, rb'^countries=\{'); ps = block(data, rb'^provinces=\{')
out = {'save':str(p), 'sha256':hashlib.sha256(raw).hexdigest(), 'date':text(re.search(rb'^date=([^\r\n]+)', data,re.M)[1]), 'countries':{}, 'provinces':{}}
for tag in ['CZH','MIN','OUE']:
    c = block(cs, rb'^\t'+tag.encode()+rb'=\{'); f = flags(c)
    out['countries'][tag] = {
        'owned_provinces': [int(x) for x in re.findall(rb'\d+',block(c,rb'^\t\towned_provinces=\{'))],
        'relevant_flags': {k:v for k,v in f.items() if k.startswith(('gdd_tianxia_unlawful','gdd_tianxia_picker')) or k in ('zhx_member','zhx_tianzi')},
        'government':text(block(c,rb'^\t\tgovernment=\{')).strip(),
        'refusal_opinion_count':c.count(b'modifier="gdd_opinion_refused_tianxia_unlawful_demand"'),
    }
for pid in [1824,4951,5007]:
    c = block(ps, rb'^-'+str(pid).encode()+rb'=\{')
    out['provinces'][str(pid)] = {'owner':text(re.search(rb'^\t\towner="([^"\r\n]+)"',c,re.M)[1]), 'relevant_flags':{k:v for k,v in flags(c).items() if k.startswith(('gdd_tianxia_unlawful','zhx_tianxia_province'))}, 'refusal_modifiers':[text(x) for x in re.findall(rb'^\t\tmodifier=\{[^{}]*modifier="gdd_tianxia_unlawful_refusal"[^{}]*\}',c,re.M)]}
diplo = block(data,rb'^diplomacy=\{')
out['liberation_cb']=[text(x) for x in re.findall(rb'casus_belli=\{[^{}]*type="gdd_cb_tianxia_liberation"[^{}]*\}',diplo)]
out['opinion_samples'] = {}
for tag in ['YAN','KRC','GDD']:
    c = block(cs, rb'^\t'+tag.encode()+rb'=\{')
    relation = block(c,rb'^\t\t\tMIN=\{')
    out['opinion_samples'][tag+'_toward_MIN'] = [text(x) for x in re.findall(rb'opinion=\{[^{}]*modifier="gdd_opinion_refused_tianxia_unlawful_demand"[^{}]*\}',relation)]
out['total_refusal_opinions'] = data.count(b'modifier="gdd_opinion_refused_tianxia_unlawful_demand"')
print(json.dumps(out,indent=2,ensure_ascii=False))

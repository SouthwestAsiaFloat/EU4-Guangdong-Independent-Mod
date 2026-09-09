from pathlib import Path
import re,json,hashlib,sys

def block(b,start):
    i=b.index(b'{',start);depth=1;q=False;esc=False
    for j in range(i+1,len(b)):
        c=b[j]
        if q:
            if esc:esc=False
            elif c==92:esc=True
            elif c==34:q=False
        elif c==34:q=True
        elif c==123:depth+=1
        elif c==125:
            depth-=1
            if not depth:return b[i+1:j]
    raise ValueError('unbalanced')
def country(b,tag):
    cs=block(b,b.index(b'\ncountries={'))
    m=re.search(rb'^\t'+tag.encode()+rb'=\{',cs,re.M)
    return block(cs,m.start())
def audit(p):
    b=Path(p).read_bytes();cs=block(b,b.index(b'\ncountries={'));out={}
    for m in re.finditer(rb'^\t([A-Z0-9]{3})=\{',cs,re.M):
        t=m[1].decode();c=block(cs,m.start())
        r=re.findall(rb'"(zhx_feudatory_\w+_reform)"',c)
        active=block(c,c.index(b'\n\t\tgovernment={')) if b'\n\t\tgovernment={' in c else b''
        stack=block(active,active.index(b'reforms={')) if b'reforms={' in active else b''
        ref=re.findall(rb'zhx_feudatory_(zi|bo|hou|gong)_reform',stack)
        if ref or t in ('CAG','CAI','CCH','CZH','GON','GUN'):
            flag_block=block(c,c.index(b'\n\t\tflags={')) if b'\n\t\tflags={' in c else b''
            flags=[x.decode() for x in re.findall(rb'^\t{3}(zhx_[\w@]+)=',flag_block,re.M) if b'feudatory' in x or b'council' in x or x==b'zhx_member']
            var_block=block(c,c.index(b'\n\t\tvariables={')) if b'\n\t\tvariables={' in c else b''
            vals={k.decode():v.decode() for k,v in re.findall(rb'^\t{3}(zhx_(?:feudatory|merit|council)[\w]+)=([\d.-]+)',var_block,re.M)}
            out[t]={'reform':list(dict.fromkeys(x.decode() for x in ref)),'flags':flags,'variables':vals,'rank':re.search(rb'government_rank=(\d+)',c)[1].decode()}
    provinces=block(b,b.index(b'\nprovinces={'))
    for m in re.finditer(rb'^-(\d+)=\{',provinces,re.M):
        province=block(provinces,m.start())
        owner=re.search(rb'^\t{2}owner="([A-Z0-9]{3})"',province,re.M)
        if owner and owner[1].decode() in out:
            out[owner[1].decode()].setdefault('owned_provinces',[]).append(int(m[1]))
    from collections import Counter
    return {'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'date':re.search(rb'\ndate=([^\n]+)',b)[1].decode(),'counts':dict(Counter(d['reform'][0] for d in out.values() if d['reform'])),'countries':out}
if __name__=='__main__':
    p=sys.argv[1] if len(sys.argv)>1 else Path('/tmp/codexzi_save_path').read_text()
    o=audit(p);Path('docs/gameplay/runtime_evidence/zi_2026-09-08/'+Path(p).stem+'.json').write_text(json.dumps(o,indent=2));print(json.dumps({'counts':o['counts'],'CAG':o['countries'].get('CAG'),'CZH':o['countries'].get('CZH')},indent=2))

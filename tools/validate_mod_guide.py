#!/usr/bin/env python3
"""Read-only checks of navigation, startup queues, references and content freshness.

The queue fixture executes a narrow script subset; it does not emulate EU4 UI.
"""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import re
from PIL import Image
import build_mod_guide as build
import validate_czc_government as cw
import validate_lingnan_opening_events as queue
from encode_eu4_chinese_localisation import verify_file

ROOT,MOD=build.ROOT,build.MOD

def main():
 data=json.loads(build.MANIFEST.read_text());pages={p['event_id']:p for p in data['pages']}
 pages['zhx_guide.0'] = dict(pages['zhx_guide.1'])
 outputs=build.render()
 for path,blob in outputs.items():assert path.read_bytes()==blob,f'stale generated output: {path}'
 events={cw.one(v,'id'):v for k,_,v in cw.read_tree(MOD/'events/zhx_mod_guide_events.txt') if k=='country_event'}
 assert events.keys()==pages.keys()
 counts={key:0 for key in events}
 for path in (MOD/'events').glob('*.txt'):
  for key in re.findall(r'^\s*id\s*=\s*(zhx_guide\.\d+)\s*$',path.read_bytes().decode('latin1'),re.M):counts[key]+=1
 assert set(counts.values())=={1},'duplicate guide event ids'
 source=(MOD/'localisation_source/027_zhx_mod_guide_readable_utf8.txt').read_text()
 loc=dict(re.findall(r'^\s*(\S+):\d+ "(.*)"$',source,re.M))
 assert len(loc)==len(re.findall(r'^\s*\S+:\d+',source,re.M))
 verify_file(MOD/'localisation_source/027_zhx_mod_guide_readable_utf8.txt',MOD/'localisation/replace/027_zhx_mod_guide_l_english.yml')
 graph={};checks=0
 for eid,event in events.items():
  assert cw.one(event,'is_triggered_only')=='yes'
  if eid != 'zhx_guide.0':
   assert cw.one(event,'trigger')==[('ai','=','no')],f'page restricted: {eid}'
  for key in ('title','desc'):assert cw.one(event,key) in loc
  options=cw.values(event,'option');assert 2<=len(options)<=6,(eid,len(options))
  graph[eid]=[];closed=False
  body=pages[eid]['body']
  assert not re.search(r'[\u2212\uff0d\ufe63]|[\u2012\u2013](?=\d)', body), (eid, 'use ASCII hyphen-minus for numeric signs; native font drops Unicode minus')
  assert len(build.plain_text(body))<=320,(eid,'split overlong body')
  assert build.estimated_display_lines(body)<=data['readability']['max_body_display_lines'],(eid,'too many display lines')
  assert body.startswith('§Y'),(eid,'missing section heading')
  # Reset colour on every line; malformed tags must not colour the rest of a window.
  for line in body.split('\n'):
   active=False;pos=0
   for match in re.finditer(r'§(.)',line):
    code=match[1]
    assert code in 'YBGR!',(eid,'unknown colour',code)
    assert code=='!' or not active,(eid,'nested colour')
    assert code!='!' or active,(eid,'unmatched colour reset')
    active=code!='!';pos=match.end()
   assert not active,(eid,'colour leaked to next line')
   assert '§' not in re.sub(r'§[YBGR!]', '', line),(eid,'invalid colour marker')
   if line and not line.startswith('§Y'):assert line.startswith('• '),(eid,'unstructured rule')
  for k,op,v in cw.walk(event):
   if k in ('set_country_flag','clr_country_flag'):assert v in ('zhx_mod_guide_open','zhx_startup_overview_seen')
  # Run every option from a freshly displayed page and verify it only changes reader flags/queue.
  for opt in options:
   assert cw.one(opt,'name') in loc
   state=queue.fresh('FRA');state['flags'].add('unrelated_gameplay_state')
   queue.apply(cw.one(event,'immediate'),state)
   before=deepcopy(state);queue.apply(opt,state)
   assert state['flags']-{'zhx_mod_guide_open','zhx_startup_overview_seen'}=={'unrelated_gameplay_state'}
   if state['queue']:
    assert len(state['queue'])==1;target,days=state['queue'][0];assert target in events and days==[]
    assert 'zhx_mod_guide_open' in state['flags'];graph[eid].append(target)
   else:
    closed=True;assert 'zhx_mod_guide_open' not in state['flags']
   assert {k:v for k,v in state.items() if k not in ('flags','queue')}=={k:v for k,v in before.items() if k not in ('flags','queue')}
   checks+=1
  assert closed,'no close option: '+eid
 # All pages reachable from root, and root reachable back from every page.
 def visit(start):
  seen=set();pending=[start]
  while pending:
   node=pending.pop()
   if node not in seen:seen.add(node);pending.extend(graph[node])
  return seen
 assert visit('zhx_guide.1')==events.keys()-{'zhx_guide.0'}
 assert visit('zhx_guide.0')==events.keys()
 assert all('zhx_guide.1' in visit(k) for k in events)
 # Continuations preserve original entry ids and provide explicit previous/next links.
 original=[p for p in data['pages'] if p['part']==1]
 assert len(original)==42
 assert {p['event_id'] for p in original}=={f'zhx_guide.{i}' for i in range(1,43)}
 for p in data['pages']:
  siblings=[x for x in data['pages'] if x['source_page']==p['source_page']]
  assert [x['part'] for x in siblings]==list(range(1,p['parts']+1))
  if p['part']>1:assert any(x['target']==siblings[p['part']-2]['key'] for x in p['links'])
  if p['part']<p['parts']:assert any(x['target']==siblings[p['part']]['key'] for x in p['links'])
 # Decision is permanent, all-human, and shares the startup reservation effect.
 decision=cw.one(cw.one(cw.read_tree(MOD/'decisions/zhx_mod_guide_decisions.txt'),'country_decisions'),'zhx_mod_guide')
 assert cw.one(decision,'potential')==[('ai','=','no')]
 assert cw.contains(cw.one(decision,'effect'),'zhx_open_mod_guide','yes')
 for tag in ('CZH','GDD','FRA'):
  state=queue.fresh(tag)
  for _ in range(4):queue.apply(queue.FX['zhx_open_mod_guide'],state)
  assert state['queue']==[('zhx_guide.1',[])]
  state=deepcopy(state) # saved flags and queued event survive the modeled reload
  state['queue'].clear();queue.apply(cw.one(events['zhx_guide.1'],'immediate'),state)
  queue.apply(cw.values(events['zhx_guide.1'],'option')[-1],state)
  queue.apply(queue.FX['zhx_open_mod_guide'],state)
  assert state['queue']==[('zhx_guide.1',[])],'closed guide cannot reopen'
 for flag in ('zhx_opening_background_pending','zhx_mod_guide_open'):
  state=queue.fresh('GDD');state['flags'].add(flag);queue.apply(queue.FX['zhx_open_mod_guide'],state);assert not state['queue']
 state=queue.fresh('FRA');state['ai']=True;queue.apply(queue.FX['zhx_open_mod_guide'],state);assert not state['queue']
 startup=queue.EVENTS['zhx_system.2'];assert cw.one(startup,'hidden')=='yes'
 assert cw.contains(cw.one(startup,'immediate'),'zhx_open_mod_guide','yes')
 # Definition lookup guards against typoed eligibility/sprite identifiers.
 reforms=set();triggers=set()
 for path in (MOD/'common/government_reforms').glob('*.txt'):reforms.update(k for k,_,v in cw.read_tree(path))
 for path in (MOD/'common/scripted_triggers').glob('*.txt'):triggers.update(k for k,_,v in cw.read_tree(path))
 custom=cw.read_tree(MOD/'customizable_localization/zhx_mod_guide_localization.txt')
 funcs={cw.one(v,'name') for k,_,v in custom if k=='defined_text'}
 for value in loc.values():
  for func in re.findall(r'\[Root\.(GetZhxGuide\w+)\]',value):assert func in funcs,func
 for k,op,v in cw.walk(custom):
  if k=='has_reform':assert v in reforms,v
  if k.startswith('zhx_is_'):assert k in triggers,k
  if k=='localisation_key':assert v in loc,v
 sprites=cw.one(cw.read_tree(MOD/'interface/zhx_mod_guide_eventpictures.gfx'),'spriteTypes')
 sprite_map={cw.one(v,'name'):cw.one(v,'texturefile') for _,_,v in sprites}
 assert len(sprite_map)==4
 for event in events.values():assert cw.one(event,'picture') in sprite_map
 for texture in sprite_map.values():
  with Image.open(MOD/texture) as im:assert im.format=='DDS' and im.size==(512,132) and im.getextrema()[-1]==(255,255)
 # This content snapshot intentionally fails after underlying mechanics change.
 # Updating it requires rereading/revising prose, not blindly accepting new hashes.
 evidence=json.loads((ROOT/'planning/mod_guide/rules_sources.json').read_text())
 for rel,digest in evidence['sha256'].items():assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==digest,'Mechanics changed; review guide: '+rel
 academy=json.loads((ROOT/'planning/religion_academies/academy_manifest.json').read_text())
 catalog='\n'.join(p['body'] for p in pages.values() if p['key'].startswith('catalog_'))
 for row in academy['academies']:assert row['name'] in catalog and row['province_name'] in catalog
 print(f'PASS: {len(events)-1} pages + native startup directory, {checks} option transitions, root reachability, close/reopen/AI/pending/reload cases, read-only effects, source freshness, colour resets/line budgets/continuations, Chinese round-trip and four DDS.')
if __name__=='__main__':main()

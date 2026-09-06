#!/usr/bin/env python3
"""HAK script contracts and boundary cases; does not emulate or launch EU4.
Use the bundled Python with Pillow for lossless DDS/atlas validation.
"""
from pathlib import Path
from copy import deepcopy
import json,re,hashlib
from PIL import Image
import validate_czc_government as v
from encode_eu4_chinese_localisation import FILES,verify_file
R=v.ROOT;M=v.MOD
ARMY='gdd_hak_revolutionary_army_reform';CIVIL='gdd_hak_communal_republic_reform'
FACTIONS=['gdd_hak_farmers','gdd_hak_burghers','gdd_hak_army']
PATHS={
'reforms':'common/government_reforms/zzz_gdd_hak_government_reforms.txt',
'factions':'common/factions/gdd_hak_factions.txt',
'estates':'common/estates/101_gdd_hak_peasants.txt',
'burgher_estate':'common/estates/03_burghers.txt',
'estate_preload':'common/estates_preload/gdd_hak_estate_modifiers.txt',
'privileges':'common/estate_privileges/gdd_hak_peasant_privileges.txt',
'effects':'common/scripted_effects/gdd_hak_government_effects.txt',
'triggers':'common/scripted_triggers/gdd_hak_government_triggers.txt',
'events':'events/gdd_hak_government_events.txt',
'on_actions':'common/on_actions/gdd_hak_government_on_actions.txt',
'decisions':'decisions/gdd_hak_government_decisions.txt',
'bindings':'common/custom_gui/gdd_hak_government_gui.txt',
'gui':'interface/countrygovernmentview.gui',
'gfx':'interface/zzz_gdd_hak_government.gfx'}
T={k:v.read_tree(M/p) for k,p in PATHS.items()}
req=v.require;one=v.one;values=v.values;scalar=v.scalar;walk=v.walk

# A deliberately small trigger evaluator exercises boundary predicates from the
# real source AST. It is not a model of native succession, estates or factions.
def check(block,state):
 def item(key,value):
  if key=='OR':return any(item(k,x) for k,_,x in value)
  if key=='AND':return check(value,state)
  if key=='NOT':return not check(value,state)
  if key.startswith('gdd_hak_') and key.endswith('_trigger'):
   return check(one(T['triggers'],key),state)==(value=='yes')
  if key=='tag':return state.get('tag','HAK')==value
  if key=='government':return state.get('government','republic')==value
  if key=='has_reform':return value in state.get('reforms',set())
  if key=='faction_in_power':return state.get('faction')==value
  if key=='has_country_flag':return value in state.get('flags',set())
  if key=='has_estate_privilege':return value in state.get('privileges',set())
  if key=='has_estate':return value in state.get('estates',set())
  if key=='has_faction':return value in state.get('factions',FACTIONS)
  if key in {'is_at_war','ai','always'}:return (True if key=='always' else state.get(key,False))==(value=='yes')
  if key in {'republican_tradition','adm_power','dip_power','mil_power'}:return state.get(key,0)>=float(value)
  raise AssertionError('Unsupported test predicate '+key)
 return all(item(k,x) for k,_,x in block)

def run(block,state,depth=0):
 """Execute only our explicit guarded script effects against a test fixture."""
 req(depth<20,'recursive scripted effects')
 previous=None
 for k,_,x in block:
  if k=='if':
   previous=check(one(x,'limit'),state)
   if previous:run([i for i in x if i[0]!='limit'],state,depth+1)
  elif k=='else':
   if previous is False:run(x,state,depth+1)
   previous=None
  elif k.startswith('gdd_hak_') and k.endswith('_effect'):run(one(T['effects'],k),state,depth+1)
  elif k in {'hidden_effect'}:run(x,state,depth+1)
  elif k in {'add_adm_power','add_dip_power','add_mil_power'}:state[k[4:]]+=float(x)
  elif k=='add_faction_influence':
   name=one(x,'faction');state.setdefault('delta',{}).setdefault(name,0);state['delta'][name]+=float(one(x,'influence'))
  elif k=='set_country_flag':state.setdefault('flags',set()).add(x)
  elif k=='change_government':state['government']=x
  elif k=='add_government_reform':
   if x in {ARMY,CIVIL}:state['reforms'].difference_update({ARMY,CIVIL})
   state['reforms'].add(x)
  elif k=='remove_government_reform':state['reforms'].discard(x)
  elif k=='set_government_rank':state['rank']=int(x)
  elif k=='country_event':state.setdefault('events',[]).append(one(x,'id'))
  elif k=='add_republican_tradition':state['republican_tradition']=max(0,min(100,state['republican_tradition']+float(x)))
  elif k=='change_estate_land_share':state.setdefault('land_changes',[]).append(deepcopy(x))
  elif k=='remove_faction':state.setdefault('removed_factions',[]).append(x)
  elif k=='custom_tooltip':pass
  else:raise AssertionError('Unsupported test effect '+k)


def mechanics():
 # Runtime regression: dynamic estate keys do not exist while factions load.
 req(not any(k.endswith('_loyalty_modifier') for k,_,_ in walk(T['factions'])), 'estate loyalty must not load in factions')
 registrations=values(one(T['estate_preload'],'estate_gdd_hak_peasants'),'modifier_definition')
 for kind,key in [('loyalty','gdd_hak_peasants_loyalty_modifier'),('influence','gdd_hak_peasants_influence_modifier'),('privileges','gdd_hak_peasants_privilege_slots')]:
  matches=[b for b in registrations if values(b,'type')==[kind]]
  req(len(matches)==1,'missing estate modifier registration');scalar(matches[0],'key',key)
 for key in ['loyalty_modifier','influence_modifier']:
  for suffix in ['', '_opposite']:
   req((M/'gfx/interface/ideas_EU4'/('gdd_hak_peasants_'+key+suffix+'.dds')).is_file(),'missing native modifier texture')
 for tree,estate,expected in [('estates','estate_gdd_hak_peasants',[('farmers','10'),('army','-10')]),('burgher_estate','estate_burghers',[('burghers','10')])]:
  conditions=values(one(T[tree],estate),'loyalty_modifier')
  for side,value in expected:
   matches=[b for b in conditions if values(b,'desc')==['gdd_hak_'+side+'_estate_loyalty']]
   req(len(matches)==1,'missing native faction estate loyalty link')
   b=matches[0];scalar(b,'loyalty',value)
   scalar(one(b,'trigger'),'faction_in_power','gdd_hak_'+side)
   scalar(one(b,'trigger'),'gdd_hak_is_republic_trigger','yes')
 for reform in [ARMY,CIVIL]:
  b=one(T['reforms'],reform);req(one(b,'potential')==[('tag','=','HAK')],'HAK-only reforms')
  req([k for k,_,_ in one(b,'factions')]==FACTIONS,'same native factions before/after civil reform')
  for key in ['locked_government_type','cannot_become_dictatorship','disables_estate_nobles']:
   scalar(one(b,'custom_attributes'),key,'yes')
 scalar(one(T['reforms'],ARMY),'has_term_election','no')
 scalar(one(T['reforms'],ARMY),'election_on_death','no')
 scalar(one(one(T['reforms'],ARMY),'custom_attributes'),'generals_become_rulers','yes')
 scalar(one(T['reforms'],CIVIL),'has_term_election','yes')
 scalar(one(T['reforms'],CIVIL),'duration','4')
 req(not v.contains(one(T['reforms'],CIVIL),'generals_become_rulers','yes'),'civil government ends automatic general succession')
 scalar(one(one(T['factions'],'gdd_hak_army'),'modifier'),'republican_tradition','-2')
 for side,power in [('farmers','ADM'),('burghers','DIP'),('army','MIL')]:scalar(one(T['factions'],'gdd_hak_'+side),'monarch_power',power)
 # Both republican regimes, all three factions, strict threshold and wrong tags.
 cases=0
 for reform in [ARMY,CIVIL]:
  for faction in FACTIONS:
   for rt in [0,19,19.999,20,20.001,60,100]:
    st={'reforms':{reform},'faction':faction,'republican_tradition':rt}
    req(check(one(T['triggers'],'gdd_hak_should_crown_trigger'),st)==(faction==FACTIONS[2] and rt<20),'crown truth table')
    cases+=1
    st['flags']={'gdd_hak_crowned'};req(not check(one(T['triggers'],'gdd_hak_should_crown_trigger'),st),'terminal crown guard')
 for war in [False,True]:
  for reform in [ARMY,CIVIL]:
   for faction in FACTIONS:
    for rt in [59.999,60,100]:
     st={'reforms':{reform},'faction':faction,'republican_tradition':rt,'is_at_war':war}
     req(check(one(T['triggers'],'gdd_hak_can_restore_civil_rule_trigger'),st)==(not war and reform==ARMY and faction==FACTIONS[0] and rt>=60),'civil exit truth table');cases+=1
 for tag in ['CZC','GDD','DAI']:
  req(not check(one(T['triggers'],'gdd_hak_is_republic_trigger'),{'tag':tag,'reforms':{ARMY}}),'scope leak')
 for side,power in [('farmers','adm'),('burghers','dip'),('army','mil')]:
  for amount in [0,9,9.999,10,11,50]:
   st={'reforms':{ARMY},'faction':FACTIONS[0],power+'_power':amount,'republican_tradition':50}
   run(one(T['effects'],'gdd_hak_support_'+side+'_effect'),st)
   req(st[power+'_power']==(amount-10 if amount>=10 else amount),'exactly-once payment/insufficient power')
   req(st.get('delta',{}).get('gdd_hak_'+side,0)==(10 if amount>=10 else 0),'no faction move without payment');cases+=1
 # Changes across monthly war/peace and privilege switches, without native drift.
 for war in [False,True]:
  for charter in [False,True]:
   for franchise in [False,True]:
    privileges=set()
    if charter:privileges.add('gdd_hak_militia_covenant')
    if franchise:privileges.add('gdd_hak_village_franchise')
    st={'reforms':{ARMY},'faction':FACTIONS[0],'flags':{'gdd_hak_initialized','gdd_hak_estate_initialized'},'privileges':privileges,'republican_tradition':50,'is_at_war':war}
    run(one(T['effects'],'gdd_hak_monthly_effect'),st)
    req(st.get('delta',{}).get(FACTIONS[2],0)==((.1 if charter else .2) if war else 0),'war/charter growth')
    req(st.get('delta',{}).get(FACTIONS[0],0)==(.1 if franchise else 0),'franchise growth/revocation');cases+=1
 req(not v.contains(one(T['effects'],'gdd_hak_restore_civil_rule_effect'),'remove_government_reform',ARMY),'restore must replace tier directly without estate-disabling gap')
 st={'reforms':{ARMY},'faction':FACTIONS[0],'republican_tradition':60,'privileges':{'gdd_hak_freehold_charter'},'person_id':123}
 run(one(T['effects'],'gdd_hak_restore_civil_rule_effect'),st)
 req(st['reforms']=={CIVIL} and st['person_id']==123 and st['privileges']=={'gdd_hak_freehold_charter'},'civil exit must preserve person and privileges')
 st={'reforms':{CIVIL},'faction':FACTIONS[2],'republican_tradition':19,'privileges':{'gdd_hak_freehold_charter'},'person_id':123}
 run(one(T['effects'],'gdd_hak_proclaim_king_effect'),st)
 req(st['government']=='monarchy' and st['rank']==2 and st['person_id']==123 and st['privileges']=={'gdd_hak_freehold_charter'},'crown conversion and preserved estate promises')
 req(check(one(T['triggers'],'gdd_hak_has_peasant_rights_trigger'),st),'crowned monarchy keeps peasant estate')
 req(st.get('removed_factions')==FACTIONS,'crowned monarchy clears republican factions')
 # Fresh startup is idempotent, including delayed estate activation.
 st={'reforms':{ARMY},'republican_tradition':100}
 run(one(T['effects'],'gdd_hak_initialize_effect'),st);req(st['republican_tradition']==50,'fresh RT')
 before=deepcopy(st);run(one(T['effects'],'gdd_hak_initialize_effect'),st);req(st==before,'repeat initialization')
 st['estates']={'estate_gdd_hak_peasants'};run(one(T['effects'],'gdd_hak_initialize_effect'),st)
 before=deepcopy(st);run(one(T['effects'],'gdd_hak_initialize_effect'),st);req(st==before and len(st['land_changes'])==1,'estate initial land exactly once')
 forbidden={'define_ruler','kill_ruler','define_heir','set_variable','change_variable'}
 req(not any(k in forbidden for k,_,_ in walk(T['effects'])),'no ruler replacement or mirror variables')
 for p in ['gdd_hak_freehold_charter','gdd_hak_village_franchise','gdd_hak_militia_covenant']:
  b=one(T['privileges'],p);scalar(one(b,'is_valid'),'gdd_hak_has_peasant_rights_trigger','yes');scalar(b,'cooldown_years','10')
 scalar(one(T['privileges'],'gdd_hak_freehold_charter'),'land_share','10')
 scalar(one(T['estates'],'estate_gdd_hak_peasants'),'icon','16')
 manifest=json.loads((R/'planning/lingnan_nations/lingnan_nations_manifest.json').read_text())
 # Accommodate the manifest's reviewed countries container, not arbitrary matches.
 req(manifest['countries']['HAK']['reform']==ARMY,'manifest starting reform')
 req('add_government_reform = '+ARMY in (M/'history/countries/HAK - Hakka.txt').read_text(encoding='latin-1'),'history reform')
 levels=one(one(v.read_tree(M/'common/governments/00_governments.txt'),'republic'),'reform_levels')
 tier=one(one(levels,'oligarchy_merchant_class_noble_elite'),'reforms')
 req(all(sum(k==name for k,_,_ in tier)==1 for name in [ARMY,CIVIL]),'both tier-one registrations')
 events={one(b,'id'):b for b in values(T['events'],'country_event')}
 for b in events.values():
  for k in ['title','desc','picture','is_triggered_only']:one(b,k)
  req(bool(values(b,'option')),'event options')
 req(v.contains(one(events['gdd_hak_government.20'],'immediate'),'gdd_hak_proclaim_king_effect','yes'),'crown executes before acknowledgment')
 refs={x for b in T.values() for k,_,x in walk(b) if k=='id' and isinstance(x,str) and x.startswith('gdd_hak_government.')}
 req(refs<=events.keys(),'event references')
 print(f'PASS: HAK script contracts and {cases} boundary/payment/pulse cases; native engine behavior is not simulated')


def presentation():
 source='021_gdd_hak_government_readable_utf8.txt';src=M/'localisation_source'/source
 verify_file(src,M/'localisation'/FILES[source]);keys=set(re.findall(r'^ ([^ :]+):',src.read_text(),re.M))
 references=set()
 for tree in T.values():
  for k,_,x in walk(tree):
   if k in {'title','desc','tooltip','custom_tooltip','buttonText','text'} and isinstance(x,str) and x.startswith('gdd_hak_'):references.add(x)
 for b in values(T['events'],'country_event'):
  references.update(one(o,'name') for o in values(b,'option'))
 req(references<=keys,'missing localisation: '+str(references-keys))
 for name in FACTIONS:
  req(all(k in keys for k in [name,name+'_influence',name+'_FACTION_DESC']),'native faction localisation')
 gui={}
 for kind,_,b in walk(T['gui']):
  if isinstance(b,list) and values(b,'name') and one(b,'name').startswith('gdd_hak_'):
   name=one(b,'name');req(name not in gui,'duplicate GUI name');gui[name]=(kind,b);scalar(b,'scripted','yes')
 bindings={one(b,'name'):(k,b) for k,_,b in T['bindings']}
 req(gui.keys()==bindings.keys() and len(gui)==13,'all 13 controls bound')
 root=one([i for i in one(T['gui'],'guiTypes') if isinstance(i[2],list) and values(i[2],'name')==['countrygovernmentview']],'windowType')
 direct={one(b,'name') for _,_,b in root if isinstance(b,list) and values(b,'name')}
 req(gui.keys()<=direct,'direct supported root children')
 req(v.strip_custom(T['gui'])==v.read_tree(v.effective(PATHS['gui'],False)),'preserve native government GUI')
 for name,(kind,b) in bindings.items():
  req(v.contains(one(b,'potential'),'gdd_hak_is_republic_trigger','yes'),'HAK visibility gate')
  if kind=='custom_button' and '_support_' in name:
   side=name.split('_support_')[1].removesuffix('_button');power={'farmers':'adm','burghers':'dip','army':'mil'}[side]
   scalar(one(b,'trigger'),power+'_power','10');scalar(one(b,'effect'),'gdd_hak_support_'+side+'_effect','yes')
 for name,(kind,b) in gui.items():
  pos=one(b,'position');x=int(one(pos,'x'));y=int(one(pos,'y'))
  w,h=(48,48) if kind=='iconType' else ((105,31) if kind=='guiButtonType' else (int(one(b,'maxWidth')),int(one(b,'maxHeight'))))
  req(x>=24 and x+w<=360 and y>=230 and y+h<=362,'control must fit above native culture row')
 sprites={one(b,'name'):b for b in values(one(T['gfx'],'spriteTypes'),'spriteType')}
 for faction in FACTIONS:
  req('GFX_faction_'+faction in sprites and 'GFX_faction_bg_'+faction in sprites,'native faction icon/background')
 for b in sprites.values():
  texture=one(b,'texturefile');p=v.effective(texture)
  im=Image.open(p);req(im.width>0 and im.height>0,'texture dimensions')
 for name,(_,b) in gui.items():
  for k in ['spriteType','quadTextureSprite']:
   for sprite in values(b,k):
    if 'gdd_hak_' in sprite:req(sprite in sprites,'unresolved custom sprite')
 asset=json.loads((R/'tools/assets/hakka_government/manifest.json').read_text())
 for item in asset['sprites'].values():
  req(hashlib.sha256((R/item['source']).read_bytes()).hexdigest()==item['sha256'],'source art hash')
  for size,item2 in item['exports'].items():
   p=R/item2['path'];im=Image.open(p).convert('RGBA')
   req(im.size==(int(size),int(size)) and im.getchannel('A').getextrema()==(0,255),'DDS dimensions and alpha')
   req(hashlib.sha256(p.read_bytes()).hexdigest()==item2['sha256'],'DDS hash')
 for name,item in asset['estate_atlases'].items():
  before=Image.open(item['source']).convert('RGBA');after=Image.open(R/item['path']).convert('RGBA')
  req(after.crop((0,0,*before.size)).tobytes()==before.tobytes(),'original estate pixels must survive atlas extension')
  scalar(sprites['GFX_'+name],'noOfFrames','16')
 req(not any('EDG_' in str(x) or 'anb_' in str(x) for tree in T.values() for _,_,x in walk(tree) if isinstance(x,str)),'no runtime dependency on reference mods')
 print(f'PASS: {len(keys)} encoded Chinese keys, 13 controls, native GUI preservation, 12 DDS icons and 2 extended atlases')

if __name__=='__main__':
 try:mechanics();presentation()
 except (ValueError,AssertionError,KeyError) as e:raise SystemExit('FAIL: '+str(e))

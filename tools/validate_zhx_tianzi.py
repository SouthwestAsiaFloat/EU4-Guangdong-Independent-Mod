#!/usr/bin/env python3
"""Tianzi source contracts and boundary checks; NOT an EU4 engine emulator."""
from pathlib import Path
from itertools import product
import json
import hashlib
import validate_czc_government as cw
from encode_eu4_chinese_localisation import verify_file

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / 'guangdong_independent_practice'
REFORM = 'zhx_tianzi_reform'

def require(ok, why):
    if not ok:
        raise AssertionError(why)

def tree(path):
    return cw.read_tree(MOD / path)

def event(path, id):
    return next(body for kind, _, body in tree(path)
                if kind == 'country_event' and cw.one(body, 'id') == id)

def evaluate(body, state):
    """Evaluate the small Boolean eligibility subset only, rejecting unknown syntax."""
    def item(k,v):
        if k == 'OR': return any(item(a,c) for a,_,c in v)
        if k == 'AND': return evaluate(v,state)
        if k == 'NOT': return not evaluate(v,state)
        if k == 'tag': return state['tag']==v
        if k == 'province_id': return state['province']==int(v)
        if k == 'owner': return evaluate(v,state)
        if k == 'has_reform': return v in state['reforms']
        if k == 'has_global_flag': return v in state['globals']
        if k == 'has_country_flag': return v in state['flags']
        if k == 'check_variable':
            return state['vars'].get(cw.one(v,'which'),0)>=float(cw.one(v,'value'))
        if k in TR:
            result=evaluate(TR[k],state)
            return result if v=='yes' else not result
        raise AssertionError('unsupported test condition '+k)
    return all(item(k,v) for k,_,v in body)

TR = {}
for path in (MOD/'common/scripted_triggers').glob('*.txt'):
    for key,_,body in cw.read_tree(path):
        if isinstance(body,list):TR[key]=body


def main():
    reform=cw.one(tree('common/government_reforms/zzz_zhx_tianzi_reforms.txt'),REFORM)
    for k,v in [('fixed_rank','3'),('allow_normal_conversion','no'),
                ('lock_level_when_selected','yes'),('valid_for_nation_designer','no')]:
        cw.scalar(reform,k,v)
    require(not cw.contains(reform,'has_meritocracy','yes'),'must use legitimacy')
    modifiers=cw.one(reform,'modifiers')
    wanted={'diplomatic_upkeep':2,'improve_relation_modifier':.2,
            'nobles_loyalty_modifier':.1,'nobles_influence_modifier':.05,
            'prestige':.5,'legitimacy':.5,'amount_of_musketeers':6}
    for k,v in wanted.items():require(float(cw.one(modifiers,k))==v,'wrong '+k)
    require(not cw.values(modifiers,'governing_capacity'),'extra governing capacity returned')
    require(not cw.values(modifiers,'allowed_musketeer_fraction'),'cap must not scale with force limit')
    cw.scalar(modifiers,'has_musketeer','yes')
    tiers=cw.one(cw.one(cw.one(cw.one(tree('common/governments/00_governments.txt'),'monarchy'),'reform_levels'),'feudalism_vs_autocracy'),'reforms')
    require(sum(k==REFORM for k,_,_ in tiers)==1,'reform not uniquely registered in tier 1')
    history=tree('history/countries/CZH - Zhou.txt')
    require(cw.one(history,'government')=='monarchy','opening government')
    require(cw.one(history,'add_government_reform')==REFORM,'opening reform')
    require(cw.one(history,'religious_school')=='zhx_ru_school','opening Ru mirror')
    names=[k for k,_,_ in history]
    require(names.index('government')<names.index('add_government_reform'),'history reform is reset by government')
    manifest=json.loads((ROOT/'planning/religion_opening_schools/opening_schools_manifest.json').read_text())
    require('CZH' in manifest['schools']['ru']['tags'],'CZH must retain authoritative Ru opening')
    tax=cw.one(tree('common/province_triggered_modifiers/zhx_wangji_modifiers.txt'),'zhx_wangji_tax')
    cw.scalar(tax,'local_tax_modifier','0.50')
    registrations=[]
    for path in (MOD/'history/provinces').glob('*.txt'):
        if b'add_province_triggered_modifier = zhx_wangji_tax' in path.read_bytes():
            registrations.append(int(path.name.split(' ')[0]))
    require(sorted(registrations)==[688,1836],'tax leaked outside Kaifeng/Luoyang')
    cases=0
    for tag,flag,initialised,has_reform,province in product(
            ['CZH','QIC','GDD'],[False,True],[False,True],[False,True],[688,1836,5046,5053,690]):
        state={'tag':tag,'flags':{'zhx_tianzi'} if flag else set(),
               'globals':{'zhx_system_initialised_v8'} if initialised else set(),
               'reforms':{REFORM} if has_reform else set(),'province':province,'vars':{}}
        authority=flag or (tag=='CZH' and not initialised)
        require(evaluate(cw.one(reform,'potential'),state)==authority,'reform eligibility boundary')
        active=evaluate(cw.one(tax,'potential'),state) and evaluate(cw.one(tax,'trigger'),state)
        require(active==(province in [688,1836] and authority and has_reform),'royal-tax ownership boundary')
        cases+=1
    conditional=cw.values(reform,'conditional')
    for g,c in product([-1,0,1,2,3,4,100],repeat=2):
        state={'vars':{'zhx_wangshi_government_stage':g,'zhx_wangshi_council_stage':c}}
        cap=6+sum(float(cw.one(cw.one(x,'modifiers'),'amount_of_musketeers'))
                  for x in conditional if evaluate(cw.one(x,'allow'),state))
        require(cap==6+2*(max(0,min(g,3))+max(0,min(c,3))) and 6<=cap<=18,'unbounded growth')
        cases+=1
    training=cw.one(tree('common/event_modifiers/zhx_tianzi_modifiers.txt'),'zhx_wangshi_training')
    cw.scalar(training,'is_musketeer_modifier','yes')
    native=cw.one(cw.read_tree(cw.effective('common/static_modifiers/00_static_modifiers.txt')),'musketeer_regiment')
    require(abs(float(cw.one(native,'fire_damage'))+float(cw.one(training,'fire_damage'))-.5)<1e-9,'total fire bonus')
    require(float(cw.one(training,'shock_damage'))==.5,'shock bonus')
    require(float(cw.one(training,'land_maintenance_modifier'))==.2,'maintenance premium')
    require({k for k,_,_ in training}=={'is_musketeer_modifier','fire_damage','shock_damage','land_maintenance_modifier'},'unexpected guard advantages/costs')
    require(cw.contains(cw.one(reform,'removed_effect'),'remove_country_modifier','zhx_wangshi_training'),'training leaks on reform loss')
    # A queued lifecycle cleanup must preserve a now-valid doctrine and only sync its mirror.
    immediate=cw.one(event('events/zhx_doctrine_events.txt','zhx_doctrine.92'),'immediate')
    first=cw.one(immediate,'if')
    require(cw.one(first,'limit')==[('zhx_is_lijiao_country','=','yes'),('zhx_has_any_doctrine_flag','=','yes')],'queued cleanup must recheck valid doctrine')
    require(cw.one(cw.one(first,'country_event'),'id')=='zhx_doctrine.91','valid doctrine should sync mirror')
    require(not cw.contains(first,'zhx_clear_doctrine_system','yes'),'valid school is cleared')
    require(cw.contains(cw.one(immediate,'else'),'zhx_clear_doctrine_system','yes'),'invalid-country cleanup removed')
    for f in ['gdd_celestial_action_triggers.txt','gdd_celestial_test_triggers.txt']:
        base=cw.one(tree('common/scripted_triggers/'+f),'gdd_proxy_decree_base_trigger')
        guard=cw.one(base,'custom_trigger_tooltip')
        require(cw.contains(cw.one(guard,'NOT'),'has_reform',REFORM),'legacy decree trigger bypass')
    decree=cw.one(tree('common/scripted_effects/gdd_celestial_proxy_effects.txt'),'gdd_enact_proxy_decree_effect')
    limit=cw.one(cw.one(decree,'if'),'limit')
    require(cw.contains(cw.one(limit,'NOT'),'has_reform',REFORM),'legacy decree execution bypass')
    for f in ['common/scripted_effects/zhx_tianzi_effects.txt','events/zhx_tianzi_events.txt',
              'common/government_names/00_aaaaa_zhx_tianzi_names.txt','common/on_actions/zhx_tianzi_on_actions.txt']:
        tree(f)
    sprite=cw.one(cw.one(tree('interface/zhx_tianzi_icons.gfx'),'spriteTypes'),'spriteType')
    require(cw.one(sprite,'name')=='government_reform_'+cw.one(reform,'icon'),'icon binding')
    texture=MOD/cw.one(sprite,'texturefile')
    require(texture.is_file(),'missing texture')
    assets=json.loads((ROOT/'tools/assets/tianzi_government/manifest.json').read_text())
    require(hashlib.sha256(texture.read_bytes()).hexdigest()==assets['assets']['mianliu']['texture_sha256'],'texture manifest')
    source=MOD/'localisation_source/025_zhx_tianzi_readable_utf8.txt'
    text=source.read_text(encoding='utf-8-sig')
    require('王师' not in text and '天子禁卫' in text,'stale visible regiment name')
    verify_file(source,MOD/'localisation/replace/025_zhx_tianzi_l_english.yml')
    print(f'PASS: Tianzi reform, two royal capitals, infantry-only training, {cases} eligibility/tax/cap boundaries, Ru startup guard, decree gates, localisation/icon references')
    print('Static source contracts only; combat, UI, recruit queues, finances and save/reload require runtime testing.')

if __name__=='__main__':main()

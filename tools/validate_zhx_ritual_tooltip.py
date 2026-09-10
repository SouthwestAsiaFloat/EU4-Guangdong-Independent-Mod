#!/usr/bin/env python3
"""Source-driven forecast scenarios and tooltip wiring; no engine emulation claim."""
from itertools import product
import re
from validate_czc_government import parse, require
from encode_eu4_chinese_localisation import MOD, FILES, verify_file

ROOT = MOD.parent
FX = dict((k,v) for k,_,v in parse((MOD/'common/scripted_effects/zhx_ritual_tooltip_effects.txt').read_text()))
PARTS = ('base','peace','wars','orthodoxy','stability','prestige','exhaustion','capital')

def data(t): return dict((k,v) for k,_,v in t)

def cond(t, w):
    for k,_,v in t:
        if k=='NOT': ok=not cond(v,w)
        elif k=='check_variable':
            d=data(v);ok=w['vars'].get(d['which'],0)>=float(d['value'])
        elif k=='has_country_modifier': ok=w['school']!='none' and w['term']
        elif k=='zhx_tianxia_has_active_orthodoxy':ok=w['school'] not in ('none','plural')
        elif k=='has_country_flag':ok=v=='zhx_tianxia_orthodoxy_'+w['school']
        elif k=='zhx_tianxia_is_at_peace':ok=w['peace']
        elif k in ('stability','prestige','war_exhaustion'):ok=w[k]>=float(v)
        elif k=='capital_scope':ok=cond(v,w)
        elif k=='controlled_by':
            require(v=='PREV','forecast must compare capital controller with its scoped owner, not GUI ROOT')
            ok=w['capital']
        elif k=='always':ok=v=='yes'
        else: raise AssertionError('unsupported trigger '+k)
        if not ok:return False
    return True

def execute(t,w):
    matched=False
    for k,_,v in t:
        if k in ('if','else_if','else'):
            if k=='if':matched=False
            if not matched and (k=='else' or cond(data(v)['limit'],w)):
                execute([x for x in v if x[0]!='limit'],w);matched=True
        elif k in ('set_variable','change_variable'):
            names=[val for key,_,val in v if key=='which'];d=data(v)
            val=float(d['value']) if 'value' in d else w['vars'][names[1]]
            w['vars'][names[0]]=val+(w['vars'].get(names[0],0) if k=='change_variable' else 0)
        elif k=='zhx_refresh_internal_war_count':w['vars']['zhx_internal_war_count_cache']=w['wars']
        elif k in FX:execute(FX[k],w)
        else:raise AssertionError('forecast mutated gameplay or added an unmodelled effect: '+k)

def expected(w):
    n=w['wars'];school=w['school'] if w['term'] else 'none';peace=w['peace']
    orth=0
    if school=='ru':orth=int(peace)-(n>=1)
    elif school=='fa':orth=1 if n==0 else -2 if n>=3 else 0
    elif school=='mo':orth=2*int(peace)-2*(n>=1)
    elif school=='dao':orth=2*int(peace)-(n>=1)
    elif school in ('bing','zongheng'):orth=(n==0)-(n>=3)
    return dict(base=1,peace=2*int(peace),wars=-3 if n>=6 else -2 if n>=3 else -1 if n else 0,
                orthodoxy=orth,stability=1 if w['stability']>=1 else -2 if w['stability']<0 else 0,
                prestige=1 if w['prestige']>=50 else -1 if w['prestige']< -25 else 0,
                exhaustion=-int(w['war_exhaustion']>=5),capital=-5*int(not w['capital']))

def main():
    count=0
    for school,term,wars,peace,stab,prest,exhaust,capital in product(
        ('none','plural','ru','fa','mo','dao','bing','zongheng'),(False,True),(0,1,2,3,5,6,8),(False,True),(-1,0,1),(-26,-25,49,50),(4.99,5),(False,True)):
        w=dict(school=school,term=term,wars=wars,peace=peace,stability=stab,prestige=prest,war_exhaustion=exhaust,capital=capital,
               vars={'zhx_ritual_authority':37,'zhx_ritual_yearly_total':999})
        execute(FX['zhx_compute_ritual_yearly_forecast'],w)
        oracle=expected(w)
        require(w['vars']['zhx_ritual_authority']==37,'preview changed ritual authority')
        for key,val in oracle.items():require(w['vars']['zhx_ritual_yearly_'+key]==val,'incorrect component '+key+str(w))
        require(w['vars']['zhx_ritual_yearly_total']==sum(oracle.values()),'total differs from annual rules')
        before=w['vars'].copy();execute(FX['zhx_compute_ritual_yearly_forecast'],w)
        require(w['vars']==before,'repeat preview accumulates values')
        count+=1
    system=data(parse((MOD/'common/scripted_effects/zhx_system_effects.txt').read_text()))
    tick=system['zhx_yearly_ritual_authority_tick']
    require(tick[0]==('zhx_compute_ritual_yearly_forecast','=','yes'),'annual tick does not recompute live forecast')
    require(tick[1]==('change_variable','=',[('which','=','zhx_ritual_authority'),('which','=','zhx_ritual_yearly_total')]),'annual tick diverges from forecast')
    require(tick[2][0]=='zhx_clamp_ritual_authority','annual bounded value must still clamp before refreshing')
    roster=(MOD/'common/scripted_effects/zhx_gui_roster_effects.txt').read_text()
    require('zhx_build_gui_roster = {\n    zhx_prepare_ritual_order_tooltip = yes' in roster,'missing open-time refresh')
    require("'    zhx_prepare_ritual_order_tooltip = yes'," in (ROOT/'tools/generate_zhx_tianxia_roster.py').read_text(),'generator would discard open refresh')
    pulse=(MOD/'common/on_actions/zhx_ritual_tooltip_on_actions.txt').read_text();parse(pulse)
    require('ai = no has_country_flag = zhx_tianxia_gui_visible' in pulse and 'tag = CZH' in pulse,'monthly scan not limited to a visible panel')
    locfile='zhx_system_readable_utf8.txt';loc=(MOD/'localisation_source'/locfile).read_text()
    strings=dict(re.findall(r'^ (\w+):0 "(.*)"$',loc,re.M))
    defs=parse((MOD/'customizable_localization/zhx_ritual_tooltip.txt').read_text())
    names={data(v)['name'] for _,_,v in defs}
    for _,_,definition in defs:
        for k,_,v in definition:
            if k=='text':require(data(v)['localisation_key'] in strings,'unresolved dynamic localisation key')
    require(strings['zhx_gui_order_tt']=='[Root.GetZhxRitualOrderTooltip]','old static hover remains')
    for k,text in strings.items():
        if not k.startswith('zhx_ritual_hover_'):continue
        require(not any(x in text for x in ('\u2212','\uff0d','\ufe63')),'unsupported minus glyph')
        for name in re.findall(r'\[(?:CZH|Root)\.(Get\w+)\]',text):require(name in names,'unresolved selector '+name)
    body=strings['zhx_ritual_hover_body']
    require(all(word not in body for word in ('AE','灭侯','非法','每月礼乐')),'hover contains unrelated rules or a fictitious monthly rate')
    require('GetZhxRitualYearlyTotal' in body and 'GetZhxRitualProtectionCost' in body,'missing requested totals/effects')
    verify_file(MOD/'localisation_source'/locfile,MOD/'localisation'/FILES[locfile])
    print(f'PASS: {count} annual scenarios; forecast is pure/idempotent; settlement shares calculation; open/monthly refresh; dynamic strings, signs and encoded localisation. Runtime hover not tested.')

if __name__=='__main__':main()

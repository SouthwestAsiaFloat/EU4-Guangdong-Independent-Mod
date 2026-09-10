#!/usr/bin/env python3
"""Render live tooltip text from actual source AST; this is NOT a game UI test."""
from itertools import product
from decimal import Decimal as D
import re
from validate_zhx_qinwang import Sim, TRIGGERS, ACTIONS, MOD, read_tree, one, values
from build_zhx_qinwang_tooltip import generated, total
from encode_eu4_chinese_localisation import verify_file

files,template=generated()
for rel,content in files.items():assert (MOD/rel).read_text()==content, rel
functions={one(v,'name'):v for k,_,v in read_tree(MOD/'customizable_localization/zhx_qinwang_tooltip.txt') if k=='defined_text'}
loc={}
for name in ('032_zhx_qinwang_readable_utf8.txt','034_zhx_qinwang_tooltip_readable_utf8.txt'):
    text=(MOD/'localisation_source'/name).read_text()
    loc.update(re.findall(r'^ ([\w.]+):\d+ "(.*)"$',text,re.M))
    verify_file(MOD/'localisation_source'/name,MOD/'localisation/replace'/name.replace('_readable_utf8.txt','_l_english.yml'))

def resolve(s,name):
    for body in values(functions[name],'text'):
        if s.check(one(body,'trigger'),s.ctx('P')):return loc[one(body,'localisation_key')]
    raise AssertionError(('no fallback',name))

def render(s):
    return re.sub(r'\[From\.(GetQinwang\w+)\]',lambda match:resolve(s,match[1]),template).replace('\\n','\n')

def oracle(s):
    c=s.countries['P']
    terms=[-20,30*any(w['d']=='H' for w in s.wars),int(c.opinion/5),int((c.trust-50)/2),
           -30 if c.manpower<D('.25') else -15 if c.manpower<D('.5') else 0,
           -30 if c.loans>=5 else -10 if c.loans else 0,
           -1000 if s.atwar('P') or not s.check(TRIGGERS['zhx_qn_single_war'],s.ctx('H')) else 0,
           -1000 if 'E' in c.truce else 0,-1000 if 'E' in c.allies else 0]
    return sum(x for x in terms if x>0), -sum(x for x in terms if x<0)

# Test generated totals, including both signs and truncation near zero.
from validate_czc_government import parse
cases=0
for op,tr,mp,loans,defensive in product((-200,-6,-1,0,4,5,99,100,105,200),(0,49,50,51,100),('0','.25','.5'),(0,4,5),(False,True)):
    s=Sim();s.war('E','H') if defensive else s.war();c=s.countries['P']
    c.opinion=D(op);c.trust=D(tr);c.manpower=D(mp);c.loans=loans
    pos,neg=oracle(s)
    for kind,want in [('positive',pos),('negative',neg),('net',abs(pos-neg))]:
        params=lambda n:parse(f'zhx_qn_sum_{kind} = {{ divisor = 1 modulus = 10000 threshold = {n} }}')
        assert s.check(params(want),s.ctx('P')) and not s.check(params(want+1),s.ctx('P')),(kind,op,tr,mp,loans,defensive,want)
        assert not c.var
    cases+=1
# Exercise every digit, leading zero suppression, exact zero, -1000 and all penalties.
for op,tr,defensive,burden,truce,alliance in product((-200,100,105,200),(0,51,100),(False,True),(False,True),(False,True),(False,True)):
    s=Sim();s.war('E','H') if defensive else s.war();c=s.countries['P']
    c.opinion=D(op);c.trust=D(tr)
    if burden:s.war('H','F')
    if truce:c.truce.add('E')
    if alliance:c.allies.add('E')
    pos,neg=oracle(s);net=pos-neg
    before={k:v.var.copy() for k,v in s.countries.items()}
    rendered=render(s)
    assert f'赞成：§G{pos}§!' in rendered, rendered
    assert f'反对：§R-{neg}§!' in rendered, rendered
    expected=('+' if net>0 else '-' if net<0 else '')+str(abs(net))
    assert f'当前净意愿：§Y{expected}§!' in rendered,rendered
    assert ('他们愿意' in rendered)==(net>0),rendered
    assert '[From.' not in rendered,rendered
    assert {k:v.var for k,v in s.countries.items()}==before,'Hover mutated saved state'
    if net==0:assert '-0§!' not in rendered
    for word,active in [('与敌方战争领袖有停战',truce),('与敌方战争领袖结盟',alliance),('天子多线作战或诸侯已经在战',burden)]:
        assert (word in rendered)==active, rendered
s=Sim();s.war();s.countries['P'].ai=False
assert '玩家控制' in render(s)
assert one(ACTIONS['zhx_qinwang_willingness'],'is_visible')==[('always','=','no')], 'A duplicate score row is still visible'
assert one(ACTIONS['zhx_invite_qinwang'],'require_acceptance')=='no', 'Lost send-time safety'
assert 'GetQinwangResponse' in loc['zhx_invite_qinwang_tooltip']
assert '勤王意愿”的' not in loc['zhx_invite_qinwang_tooltip']
# Compact gate: every failed check must remain a real requirement, not just prose.
for branch in values(one(ACTIONS['zhx_invite_qinwang'],'is_allowed'),'if'):
    condition=one(one(branch,'limit'),'NOT')
    enforced=[x for x in one(branch,'custom_trigger_tooltip') if x[0]!='tooltip']
    assert condition==enforced,'Display gate and execution gate diverged'
print(f'PASS: {cases} positive/negative/net arithmetic cases, 192 rendered scenarios; no saved-state writes; zero formatting; only active reasons; single visible invite; execution gates retained. Runtime rendering/performance NOT tested.')

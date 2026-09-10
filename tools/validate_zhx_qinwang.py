#!/usr/bin/env python3
"""Source-driven Qinwang score/scope/lifecycle simulation, NOT engine validation."""
from dataclasses import dataclass, field, replace
from decimal import Decimal as D, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
from itertools import product
import re
from pathlib import Path
from validate_czc_government import MOD, read_tree, one, values, walk, contains
from encode_eu4_chinese_localisation import verify_file
from build_zhx_qinwang_score import generated

TRIGGERS = {}; EFFECTS = {}
for p in MOD.rglob('*qinwang*.txt'):
    if 'localisation' in str(p): continue
    tree=read_tree(p)
    if 'scripted_triggers' in str(p): TRIGGERS.update({k:v for k,_,v in tree})
    if 'scripted_effects' in str(p): EFFECTS.update({k:v for k,_,v in tree})
for p, expected in generated().items():
    assert (MOD/p).read_text()==expected, 'Generated score drift'
EVENTS={one(v,'id'):v for k,_,v in read_tree(MOD/'events/zhx_qinwang_events.txt') if k=='country_event'}
ON=read_tree(MOD/'common/on_actions/zhx_qinwang_on_actions.txt')
ACTIONS={k:v for k,_,v in read_tree(MOD/'common/new_diplomatic_actions/zhx_qinwang_actions.txt')}

@dataclass
class Country:
    flags:set=field(default_factory=set)
    var:dict=field(default_factory=dict)
    ai:bool=True
    member:bool=True
    subject:bool=False
    alive:bool=True
    opinion:D=D(150)
    trust:D=D(50)
    manpower:D=D(1)
    loans:int=0
    favors:dict=field(default_factory=dict)
    truce:set=field(default_factory=set)
    allies:set=field(default_factory=set)
    merit:int=0

@dataclass
class Context:
    sim:object
    stack:tuple
    root:str
    source:str|None=None
    targets:dict=field(default_factory=dict)
    @property
    def tag(self): return self.stack[-1]
    @property
    def country(self): return self.sim.countries[self.tag]
    def scope(self,tag): return replace(self,stack=self.stack+(tag,))
    def resolve(self,name):
        if name=='THIS': return self.tag
        if name=='ROOT': return self.root
        if name=='FROM': return self.source
        if name.startswith('PREV'): return self.stack[-1-len(name)//4]
        if name.startswith('event_target:'): return self.targets.get(name[13:], self.sim.targets.get(name[13:]))
        if name in self.sim.countries: return name
        return None

class Sim:
    def __init__(self):
        self.countries={k:Country() for k in ('H','P','Q','E','F')}
        self.countries['H'].ai=False
        self.countries['E'].member=False;self.countries['F'].member=False
        self.countries['P'].favors['H']=D(25);self.countries['Q'].favors['H']=D(25)
        self.targets={'zhx_tianzi':'H'};self.flags={'zhx_system_initialised_v14'}
        self.wars=[];self.events=[];self.join_mode='immediate';self.commands=[]
    def ctx(self,tag='H',source=None): return Context(self,(tag,),tag,source)
    def war(self,attacker='H',defender='E'):
        war=dict(a=attacker,d=defender,attackers={attacker},defenders={defender})
        self.wars.append(war);return war
    def atwar(self,tag): return any(tag in w['attackers']|w['defenders'] for w in self.wars)
    def enemies(self,tag):
        out=set()
        for w in self.wars:
            if tag in w['attackers']: out |= w['defenders']
            if tag in w['defenders']: out |= w['attackers']
        return sorted(out)
    def argument(self,body,ctx):
        w=values(body,'which')
        if len(w)>1:
            other=ctx.resolve(w[1])
            return (self.countries[other].var.get(w[0],D(0)) if other else ctx.country.var.get(w[1],D(0)))
        return D(one(body,'value'))
    def check(self,tree,ctx):
        out=[]
        for k,op,b in tree:
            c=ctx.country
            if k in TRIGGERS:
                sub=TRIGGERS[k]
                if isinstance(b,list):
                    def expand(t):
                        return [(key,o,expand(v) if isinstance(v,list) else dict((x,z) for x,_,z in b).get(v[1:-1],v) if isinstance(v,str) and v.startswith('$') else v) for key,o,v in t]
                    sub=expand(sub)
                result=self.check(sub,ctx)
                out.append(result if b!='no' else not result)
            elif k in ('AND','NOT','OR'):
                rs=(self.check([x],ctx) for x in b);out.append(any(rs) if k=='OR' else not any(rs) if k=='NOT' else all(rs))
            elif k=='custom_trigger_tooltip': out.append(self.check([x for x in b if x[0]!='tooltip'],ctx))
            elif k=='if':
                out.append(not self.check(one(b,'limit'),ctx) or self.check([x for x in b if x[0]!='limit'],ctx))
            elif k=='always': out.append(b=='yes')
            elif k=='exists': out.append(c.alive==(b=='yes'))
            elif k=='ai': out.append(c.ai==(b=='yes'))
            elif k=='is_subject': out.append(c.subject==(b=='yes'))
            elif k=='is_at_war': out.append(self.atwar(ctx.tag)==(b=='yes'))
            elif k=='zhx_is_tianxia_member': out.append(c.member==(b=='yes'))
            elif k=='zhx_is_tianzi': out.append((ctx.tag==self.targets['zhx_tianzi'])==(b=='yes'))
            elif k=='has_country_flag': out.append(b in c.flags)
            elif k=='has_global_flag': out.append(b in self.flags)
            elif k=='has_saved_global_event_target': out.append(b in self.targets)
            elif k=='has_saved_event_target': out.append(b in ctx.targets)
            elif k=='tag': out.append(ctx.tag==ctx.resolve(b))
            elif k=='war_with': out.append(ctx.resolve(b) in self.enemies(ctx.tag))
            elif k=='manpower_percentage': out.append(c.manpower>=D(b))
            elif k=='num_of_loans': out.append(c.loans>=int(b))
            elif k in ('truce_with','alliance_with'):
                other=ctx.resolve(b);attr='truce' if k=='truce_with' else 'allies'
                out.append(other in getattr(c,attr) or ctx.tag in getattr(self.countries[other],attr))
            elif k=='owes_favors': out.append(c.favors.get(ctx.resolve(one(b,'who')),D(0))>=D(one(b,'value')))
            elif k in ('check_variable','is_variable_equal'):
                lhs=c.var.get(values(b,'which')[0],D(0));rhs=self.argument(b,ctx)
                out.append(lhs>=rhs if k=='check_variable' else lhs==rhs)
            elif k=='any_country': out.append(any(self.check(b,ctx.scope(tag)) for tag in self.countries))
            elif k=='any_war_enemy_country': out.append(any(self.check(b,ctx.scope(tag)) for tag in self.enemies(ctx.tag)))
            elif k=='is_in_war':
                def match(w):
                    if ctx.tag not in w['attackers']|w['defenders']: return False
                    for key,_,val in b:
                        tag=ctx.resolve(val)
                        if key in ('attacker_leader','defender_leader'):
                            if w['a' if key=='attacker_leader' else 'd']!=tag:return False
                        elif tag not in w[key]: return False
                    return True
                out.append(any(match(w) for w in self.wars))
            elif k=='variable_arithmetic_trigger':
                old=c.var.copy()
                for x in b:
                    if x[0] in ('check_variable','is_variable_equal'): out.append(self.check([x],ctx))
                    elif x[0]!='custom_tooltip':self.run([x],ctx)
                c.var=old
            elif ctx.resolve(k): out.append(self.check(b,ctx.scope(ctx.resolve(k))))
            elif k.startswith('event_target:'): out.append(False)
            else: raise AssertionError(('unsupported trigger',k,b))
        return all(out)
    def run(self,tree,ctx):
        branch=False
        for k,op,b in tree:
            c=ctx.country
            if k in EFFECTS: self.run(EFFECTS[k],ctx)
            elif k=='if':
                branch=self.check(one(b,'limit'),ctx)
                if branch:self.run([x for x in b if x[0]!='limit'],ctx)
            elif k=='else_if':
                if not branch and self.check(one(b,'limit'),ctx):self.run([x for x in b if x[0]!='limit'],ctx);branch=True
            elif k=='else':
                if not branch:self.run(b,ctx)
                branch=True
            elif k in ('hidden_effect','immediate'):self.run(b,ctx)
            elif k=='set_country_flag':c.flags.add(b)
            elif k=='clr_country_flag':c.flags.discard(b)
            elif k=='set_global_flag':self.flags.add(b)
            elif k=='clr_global_flag':self.flags.discard(b)
            elif k=='save_global_event_target_as':self.targets[b]=ctx.tag
            elif k=='clear_global_event_target':self.targets.pop(b,None)
            elif k=='save_event_target_as':ctx.targets[b]=ctx.tag
            elif k in ('set_variable','change_variable','subtract_variable','multiply_variable','divide_variable','round_variable'):
                name=values(b,'which')[0];v=self.argument(b,ctx);old=c.var.get(name,D(0))
                if k=='set_variable':c.var[name]=v
                elif k=='change_variable':c.var[name]=old+v
                elif k=='subtract_variable':c.var[name]=old-v
                elif k=='multiply_variable':c.var[name]=old*v
                elif k=='divide_variable':c.var[name]=old/v
                else:c.var[name]=old.to_integral_value(rounding=ROUND_CEILING if v>0 else ROUND_FLOOR if v<0 else ROUND_HALF_UP)
            elif k=='sqrt_variable':
                name=values(b,'which')[0];c.var[name]=c.var[name].sqrt()
            elif k=='modulo_variable':
                name=values(b,'which')[0];c.var[name]%=self.argument(b,ctx)
            elif k=='export_to_variable':
                dest=one(b,'variable_name');value=one(b,'value');who=ctx.resolve(values(b,'who')[0]) if values(b,'who') else ctx.tag;sc=ctx.scope(who)
                if value=='trigger_value:num_of_cities':v=D(1)
                elif value.startswith('trigger_value:'):raise AssertionError('Unsupported trigger export: '+value)
                else:v=getattr(sc.country,value)
                c.var[dest]=v
            elif k=='every_country':
                for tag in sorted(self.countries):
                    sc=ctx.scope(tag)
                    if self.check(one(b,'limit'),sc):self.run([x for x in b if x[0]!='limit'],sc)
            elif k=='country_event':self.events.append((one(b,'id'),replace(ctx,targets=ctx.targets.copy())))
            elif k in ('join_all_offensive_wars_of','join_all_defensive_wars_of'):
                host=ctx.resolve(b);side='attackers' if k=='join_all_offensive_wars_of' else 'defenders'
                for w in self.wars:
                    if host in w[side]:
                        if self.join_mode=='immediate':w[side].add(ctx.tag)
                        elif self.join_mode=='delayed':self.commands.append((w,side,ctx.tag))
            elif k=='add_favors':
                who=ctx.resolve(one(b,'who'));self.countries[who].favors[ctx.tag]+=D(one(b,'amount'))
            elif k=='zhx_add_active_merit':c.merit+=int(one(b,'amount'))
            elif k=='custom_tooltip':pass
            elif ctx.resolve(k):self.run(b,ctx.scope(ctx.resolve(k)))
            else:raise AssertionError(('unsupported effect',k,b))
    def invoke(self,name,ctx=None):self.run(EFFECTS[name],ctx or self.ctx())
    def response(self,accept=True):
        event,ctx=next(x for x in self.events if x[0]=='zhx_qinwang.10');self.events.remove((event,ctx))
        option=values(EVENTS[event],'option')[0 if accept else 1]
        self.run([x for x in option if x[0]!='name'],ctx)
    def end(self,war):
        self.wars.remove(war);self.run(one(ON,'on_war_ended'),self.ctx(war['a'],war['d']))

# Scores derived from actual generated arithmetic, checked against an independent formula.
s=Sim();s.war();c=s.countries['P'];checks=0
for opinion,trust,mp,loans,defensive in product((-200,-6,-1,0,1,4,5,99,100,101,105,200),(0,49,50,51,53,100),('0','.249','.25','.499','.5','1'),(0,1,4,5),(False,True)):
    c.opinion=D(opinion);c.trust=D(trust);c.manpower=D(mp);c.loans=loans
    s.wars=[];s.war('E','H') if defensive else s.war()
    expected=-20+30*defensive+int(D(opinion)/5)+int((D(trust)-50)/2)-(30 if D(mp)<D('.25') else 15 if D(mp)<D('.5') else 0)-(30 if loans>=5 else 10 if loans else 0)
    assert s.check(TRIGGERS['zhx_qn_ai_positive'],s.ctx('P'))==(expected>0),(opinion,trust,mp,loans,defensive,expected)
    assert not c.var, 'Tooltip calculation must not persist variables'
    # Native add_entry values (the engine truncates toward zero).
    native=0
    ctx=s.ctx('H','P')
    for entry in values(one(ACTIONS['zhx_qinwang_willingness'],'ai_acceptance'),'add_entry'):

        if self_limits:=values(entry,'limit'):
            if not s.check(self_limits[0],ctx):continue
        s.run([x for x in entry if x[0] not in ('name','limit')],ctx);native+=int(ctx.country.var['ai_value'])
    ctx.country.var.clear()
    assert native==expected,('diplomacy/pulse mismatch',native,expected)
    checks+=1

# Independent eligibility/scope tests: enemy allies are NOT extra wars;
# being an ally rather than leader is rejected; a second allied war also blocks.
s=Sim();w=s.war();w['defenders'].add('F')
assert s.check(TRIGGERS['zhx_qn_single_war'],s.ctx())
s.war('F','Q')['defenders'].add('H')
assert not s.check(TRIGGERS['zhx_qn_single_war'],s.ctx())
s=Sim();s.war('Q','E')['attackers'].add('H')
assert not s.check(TRIGGERS['zhx_qn_single_war'],s.ctx())
for conflict in ('truce','allies'):
    s=Sim();s.war();getattr(s.countries['P'],conflict).add('E')
    assert not s.check(TRIGGERS['zhx_qn_ai_positive'],s.ctx('P'))
    getattr(s.countries['P'],conflict).clear();getattr(s.countries['P'],conflict).add('H')
    assert s.check(TRIGGERS['zhx_qn_ai_positive'],s.ctx('P')), 'Alliance with host is not a penalty'

# Dispatch/consent/settlement run the production effect AST, including its scopes.
for defensive in (False,True):
    s=Sim();w=s.war('E','H') if defensive else s.war()
    s.invoke('zhx_qn_dispatch',s.ctx('P'));s.invoke('zhx_qn_dispatch',s.ctx('P'))
    assert s.countries['P'].merit==10 and s.countries['P'].favors['H']==0
    assert 'P' in w['defenders' if defensive else 'attackers']
    # Separate peace retains sent record, even after a second war comes and goes.
    w['defenders' if defensive else 'attackers'].discard('P');s.countries['P'].favors['H']=D(25)
    s.run(one(ON,'on_war_ended'),s.ctx('P','E'))
    second=s.war('H','F');s.invoke('zhx_qn_maintain');s.end(second)
    s.invoke('zhx_qn_dispatch',s.ctx('P'));assert s.countries['P'].merit==10
    s.end(w);assert 'zhx_qn_sent' not in s.countries['P'].flags
    s.war('E','H') if defensive else s.war()
    s.invoke('zhx_qn_dispatch',s.ctx('P'));assert s.countries['P'].merit==20

for change in ('none','refuse','peace','new_same_enemy','multiwar','recipient_war','favors','tianzi'):
    s=Sim();w=s.war();c=s.countries['P'];c.ai=False
    s.invoke('zhx_qn_dispatch',s.ctx('P'));assert c.merit==0 and c.favors['H']==25
    if change=='peace':s.end(w)
    elif change=='new_same_enemy':s.end(w);s.war();s.invoke('zhx_qn_open_campaign')
    elif change=='multiwar':s.war('H','F')
    elif change=='recipient_war':s.war('P','F')
    elif change=='favors':c.favors['H']=D(24)
    elif change=='tianzi':s.targets['zhx_tianzi']='Q'
    s.response(change!='refuse')
    assert c.merit==(10 if change=='none' else 0),change
    assert c.favors['H']==(0 if change=='none' else 24 if change=='favors' else 25),change
    assert 'zhx_qn_pending' not in c.flags
for mode in ('delayed','fail'):
    s=Sim();s.war();s.join_mode=mode;s.invoke('zhx_qn_dispatch',s.ctx('P'))
    assert s.countries['P'].merit==0 and s.countries['P'].favors['H']==25
    for w,side,tag in s.commands:w[side].add(tag)
    eid,ctx=next(x for x in s.events if x[0]=='zhx_qinwang.11')
    s.run(one(EVENTS[eid],'immediate'),ctx);s.run(one(EVENTS[eid],'immediate'),ctx)
    assert s.countries['P'].merit==(10 if mode=='delayed' else 0)
    assert s.countries['P'].favors['H']==(0 if mode=='delayed' else 25)
# Monthly AI host dispatch: human and AI recipients share the same sender/cost direction.
s=Sim();s.war();s.countries['H'].ai=True;s.countries['P'].ai=False
s.invoke('zhx_qn_maintain');s.invoke('zhx_qn_maintain')
assert len([e for e in s.events if e[0]=='zhx_qinwang.10'])==1
assert s.countries['Q'].merit==10
s.response();assert s.countries['P'].merit==10

source=MOD/'localisation_source/032_zhx_qinwang_readable_utf8.txt'
verify_file(source,MOD/'localisation/replace/032_zhx_qinwang_l_english.yml')
loc=source.read_text();keys=set(re.findall(r'^ ([\w.]+):',loc,re.M))
assert len(keys)==len(re.findall(r'^ ([\w.]+):',loc,re.M)), 'duplicate localisation'
assert not any(x in loc for x in ('−','－','﹣')), 'unsupported minus sign'
for p in MOD.rglob('*qinwang*.txt'):
    if 'localisation' in str(p):continue
    for k,_,v in walk(read_tree(p)):
        if k in ('tooltip','custom_tooltip','title','desc','name') and isinstance(v,str) and v.startswith('zhx_q'):
            assert v in keys,(p,v)
assert not any(k=='add_favors' for k,_,v in walk(one(ACTIONS['zhx_invite_qinwang'],'on_accept'))), 'No cost on dispatch'
assert one(ACTIONS['zhx_invite_qinwang'],'require_acceptance')=='no'
assert one(ACTIONS['zhx_qinwang_willingness'],'require_acceptance')=='yes'
assert contains(one(ACTIONS['zhx_qinwang_willingness'],'is_allowed'),'always','no'), 'Assessment must be read-only'
assert not one(ACTIONS['zhx_qinwang_willingness'],'on_accept')
print(f'Qinwang static/source-model validation passed: {checks} score combinations; scope, stale requests, double-war, separate-peace, repeat, AI/human, failed/delayed joins. Engine runtime NOT tested.')

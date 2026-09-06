#!/usr/bin/env python3
"""Source-driven Zhou title/petition contracts. Does not emulate the EU4 engine."""
from dataclasses import dataclass, field
from pathlib import Path
from itertools import product
import copy
import json
import re
import sys

import validate_czc_government as cw
from encode_eu4_chinese_localisation import FILES, verify_file
from apply_zhou_feudatories import render

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / 'guangdong_independent_practice'
P = 'zhx_feudatory_'
REFORMS = [P+d+'_reform' for d in ('bo','hou','gong')]
CATALOG = ROOT / 'planning/zhou_feudatories/opening_dignities.json'
TR = {}
FX = {}
for path in (MOD/'common/scripted_triggers').glob('*.txt'):
    for key, _, body in cw.read_tree(path):
        if isinstance(body,list): TR[key] = body
for path in (MOD/'common/scripted_effects').glob('*.txt'):
    for key, _, body in cw.read_tree(path):
        if isinstance(body,list): FX[key] = body


def require(ok, why):
    if not ok: raise AssertionError(why)


@dataclass
class Country:
    tag: str
    flags: set = field(default_factory=set)
    reforms: set = field(default_factory=set)
    vars: dict = field(default_factory=dict)
    government: str = 'monarchy'
    rank: int = 1
    dev: float = 100
    cities: int = 10
    alive: bool = True
    ai: bool = False
    allies: set = field(default_factory=set)
    rivals: set = field(default_factory=set)
    enemies: set = field(default_factory=set)
    opinions: dict = field(default_factory=dict)
    ruler: str = 'unchanged ruler'
    heir: str = 'unchanged heir'
    estates: tuple = ('nobles', 'burghers', 'church')


class World:
    """Fail-closed evaluator for the narrow script subset under test.

    Native effects such as reform succession, diplomacy delivery, ranks and
    estate recalculation are NOT simulated. Scheduled events are only recorded;
    tests invoke the corresponding real event/effect body at the boundary.
    """
    def __init__(self, dignity='bo'):
        self.c = {t:Country(t) for t in ('GDD','GUI','QIN','XU2','CZH')}
        self.actor = self.c['GDD']; self.host = self.c['CZH']
        self.globals = {'zhx_feudatory_initialised'}
        self.targets = {'zhx_tianzi':self.host}
        self.events = []
        for c in self.c.values(): c.flags.add('zhx_member')
        self.host.flags = {'zhx_tianzi'}
        self.host.rank = 3
        self.actor.reforms = {P+dignity+'_reform'}
        self.actor.dev = 200 if dignity=='hou' else 100
        self.actor.cities = 20 if dignity=='hou' else 10
        self.actor.vars = {'zhx_merit_term':200 if dignity=='hou' else 100, 'zhx_merit':77, 'zhx_merit_lifetime':555}

    def target(self, name, c, prev=None):
        if name == 'PREV': return prev
        if name == 'ROOT': return self.actor
        if name == 'FROM': return self.host
        if name.startswith('event_target:'): return self.targets.get(name.split(':',1)[1])
        return self.c.get(name)

    def cond(self, tree, c, prev=None):
        return all(self.test(k,v,c,prev) for k,_,v in tree)

    def test(self,k,v,c,prev=None):
        if k in ('AND','hidden_trigger','custom_trigger_tooltip'):
            return self.cond([e for e in v if e[0]!='tooltip'],c,prev)
        if k == 'OR': return any(self.test(a,b,c,prev) for a,_,b in v)
        if k == 'NOT': return not any(self.test(a,b,c,prev) for a,_,b in v)
        if k in TR: return self.cond(TR[k],c,prev) == (v=='yes')
        if k.startswith('event_target:') or k in ('ROOT','FROM','PREV') or k in self.c:
            t=self.target(k,c,prev)
            return t is not None and self.cond(v,t,c)
        if k == 'always': return v=='yes'
        if k == 'has_global_flag': return v in self.globals
        if k == 'has_saved_global_event_target': return v in self.targets
        if c is None: return False
        if k == 'has_country_flag': return v in c.flags
        if k == 'has_reform': return v in c.reforms
        if k == 'exists': return c.alive == (v=='yes')
        if k == 'ai': return c.ai == (v=='yes')
        if k == 'government': return c.government==v
        if k == 'government_rank': return c.rank>=int(v)
        if k == 'total_development': return c.dev>=float(v)
        if k == 'num_of_cities': return c.cities>=int(v)
        if k == 'tag':
            t=self.target(v,c,prev)
            return c.tag == (t.tag if t is not None else v)
        if k in ('war_with','alliance_with','is_rival'):
            t=self.target(v,c,prev); tag=t.tag if t else v
            return tag in getattr(c,{'war_with':'enemies','alliance_with':'allies','is_rival':'rivals'}[k])
        if k == 'has_opinion':
            t=self.target(cw.one(v,'who'),c,prev)
            return t is not None and c.opinions.get(t.tag,0)>=float(cw.one(v,'value'))
        if k == 'check_variable':
            names=cw.values(v,'which'); rhs=cw.values(v,'value')
            return c.vars.get(names[0],0)>=(float(rhs[0]) if rhs else c.vars.get(names[1],0))
        if k == 'has_country_modifier': return False
        raise AssertionError('unsupported test trigger '+k)

    def run(self, tree, c, prev=None, depth=0):
        require(depth<90,'recursive effect loop')
        taken=None
        for k,_,v in tree:
            if k=='if':
                taken=self.cond(cw.one(v,'limit'),c,prev)
                if taken:self.run([e for e in v if e[0]!='limit'],c,prev,depth+1)
            elif k=='else_if':
                require(taken is not None,'orphan else_if')
                if not taken:
                    take=self.cond(cw.one(v,'limit'),c,prev)
                    if take:self.run([e for e in v if e[0]!='limit'],c,prev,depth+1);taken=True
            elif k=='else':
                require(taken is not None,'orphan else')
                if not taken:self.run(v,c,prev,depth+1)
                taken=True
            elif k in FX:self.run(FX[k],c,prev,depth+1)
            elif k in ('hidden_effect',):self.run(v,c,prev,depth+1)
            elif k in ('every_country','random_country'):
                limits=cw.values(v,'limit'); body=[e for e in v if e[0]!='limit']
                for t in self.c.values():
                    if not limits or self.cond(limits[0],t,c):
                        self.run(body,t,c,depth+1)
                        if k=='random_country':break
            elif k.startswith('event_target:') or k in ('ROOT','FROM','PREV') or k in self.c:
                t=self.target(k,c,prev)
                if t is not None:self.run(v,t,c,depth+1)
            elif k=='set_country_flag':c.flags.add(v)
            elif k=='clr_country_flag':c.flags.discard(v)
            elif k=='set_global_flag':self.globals.add(v)
            elif k=='clr_global_flag':self.globals.discard(v)
            elif k in ('save_global_event_target_as','save_event_target_as'):self.targets[v]=c
            elif k=='clear_global_event_target':self.targets.pop(v,None)
            elif k=='add_government_reform':
                if v in REFORMS:c.reforms.difference_update(REFORMS)
                c.reforms.add(v)
            elif k=='remove_government_reform':c.reforms.discard(v)
            elif k=='set_government_rank':c.rank=int(v)
            elif k in ('set_variable','change_variable','subtract_variable'):
                names=cw.values(v,'which'); value=cw.values(v,'value')
                rhs=float(value[0]) if value else c.vars.get(names[1],0)
                old=c.vars.get(names[0],0)
                c.vars[names[0]]=rhs if k=='set_variable' else old+rhs if k=='change_variable' else old-rhs
            elif k=='country_event':self.events.append((c.tag,cw.one(v,'id'),cw.values(v,'days')))
            elif k in ('custom_tooltip',):pass
            else:raise AssertionError('unsupported test effect '+k)

    def call(self,key,c=None):self.run(FX[key],c or self.actor)
    def check(self,key,c=None):return self.cond(TR[key],c or self.actor)


def source_contracts():
    catalog=json.loads(CATALOG.read_text())
    require(len(catalog['countries'])==58,'opening roster changed: audit eligibility')
    system=cw.one(cw.read_tree(MOD/'common/scripted_effects/zhx_system_effects.txt'),'zhx_initialise_tianxia_system')
    alltags={v for k,_,v in cw.walk(system) if k=='tag' and isinstance(v,str)}
    covered=set(catalog['countries'])|set(catalog['excluded'])
    require(alltags==covered,'opening member catalog is incomplete')
    for tag,entry in catalog['countries'].items():
        p=MOD/'history/countries'/entry['history'];data=p.read_bytes()
        require(render(data,entry)==data,tag+' history drift')
        tree=cw.read_tree(p)
        require(cw.one(tree,'government')=='monarchy',tag+' must stay monarchy')
        require(cw.values(tree,'add_government_reform')[0]==P+entry['dignity']+'_reform',tag+' wrong opening reform')
        require(next(i for i,(k,_,_) in enumerate(tree) if k=='government') < next(i for i,(k,_,_) in enumerate(tree) if k=='add_government_reform'),tag+' applies its reform before setting the base government')
        require(cw.values(tree,'government_rank')[0]==('2' if entry['dignity']=='gong' else '1'),tag+' wrong rank')
    for tag in catalog['excluded']:
        p=next((MOD/'history/countries').glob(tag+' - *.txt'))
        require(not any(isinstance(v,str) and v in REFORMS for k,_,v in cw.walk(cw.read_tree(p))),tag+' must be excluded')
    reforms=cw.read_tree(MOD/'common/government_reforms/zzz_zhx_feudatory_reforms.txt')
    tier=cw.one(cw.one(cw.one(cw.one(cw.read_tree(MOD/'common/governments/00_governments.txt'),'monarchy'),'reform_levels'),'feudalism_vs_autocracy'),'reforms')
    for d,r in zip(('bo','hou','gong'),REFORMS):
        b=cw.one(reforms,r);mods=dict((k,v) for k,_,v in cw.one(b,'modifiers'))
        require(cw.one(b,'fixed_rank')==('2' if d=='gong' else '1'),'fixed rank contract')
        require(mods==dict(nobles_loyalty_modifier='0.10',legitimacy='0.5',stability_cost_modifier='-0.10',nobles_influence_modifier='0.05',**({'diplomatic_reputation':'1'} if d!='bo' else {})),'reform modifiers')
        require(sum(k==r for k,_,v in tier)==1,'tier must register once')
        if d!='bo':require(cw.contains(cw.one(b,'potential'),'has_country_flag',P+'grant_'+d),'manual promotion bypass')
    startup=cw.read_tree(MOD/'events/gdd_startup_events.txt')
    require(not cw.contains(startup,'add_government_reform','feudalism_reform'),'GDD startup overwrites the history-assigned Zhou dignity')
    fx=cw.read_tree(MOD/'common/scripted_effects/zhx_feudatory_effects.txt')
    require(not any(k=='remove_government_reform' for k,_,v in cw.walk(cw.one(fx,P+'execute_promotion'))),'promotion briefly removes the government before replacing its native tier')
    require(not any(k in {'add_adm_power','add_dip_power','add_mil_power','define_ruler','define_heir','kill_ruler'} for k,_,v in cw.walk(fx)),'unapproved ruler/payment mutation')
    for k,_,v in cw.walk(fx):
        if k in ('change_variable','subtract_variable'):
            require(not any(x in {'zhx_merit','zhx_merit_term','zhx_merit_lifetime'} for x in cw.values(v,'which')),'must not charge merit')
    effect=cw.one(cw.read_tree(MOD/'common/scripted_effects/zhx_merit_store_effects.txt'),'zhx_settle_merit_term')
    require(cw.contains(effect,'zhx_feudatory_begin_new_term','yes'),'missing existing term callback')
    deadline=[b for k,_,b in cw.read_tree(MOD/'events/zhx_system_events.txt') if k=='country_event' and cw.one(b,'id')=='zhx_system.23'][0]
    require(cw.contains(deadline,'zhx_feudatory_resolve_promotion','yes'),'missing shared deadline result dispatch')
    require(cw.contains(deadline,'has_country_flag','zhx_council_kind_promotion'),'missing shared deadline kind')
    action=cw.one(cw.read_tree(MOD/'common/new_diplomatic_actions/zhx_feudatory_actions.txt'),P+'petition')
    require(cw.one(action,'require_acceptance')=='no','submission must snapshot at send time; .10 provides consent')
    require(cw.contains(cw.one(action,'on_accept'),P+'submit_petition','yes'),'diplomacy is not wired')
    source='022_zhx_feudatory_readable_utf8.txt';path=MOD/'localisation_source'/source
    verify_file(path,MOD/'localisation'/FILES[source])
    keys=set(re.findall(r'^ ([\w.]+):',path.read_text(),re.M))
    relevant=list(MOD.glob('common/**/*feudator*.txt'))+list(MOD.glob('events/*feudator*.txt'))+list(MOD.glob('decisions/*feudator*.txt'))+list(MOD.glob('customizable_localization/*feudator*.txt'))
    all_trees=[cw.read_tree(p) for p in relevant]
    events={cw.one(b,'id') for t in all_trees for k,_,b in t if k=='country_event'}
    for tree in all_trees:
        for k,_,v in cw.walk(tree):
            if isinstance(v,str) and v.startswith(P):
                if k in {'name','title','desc','tooltip','custom_tooltip','localisation_key','buttonText','text'} and v not in keys:
                    # names of scripted GUI controls also need matching keys.
                    require(k=='name' and v in (P+'petition',),'missing localization '+v)
                if k=='id':require(v in events,'undefined event '+v)
            if k.startswith(P) and v in ('yes','no'):
                require(k in TR or k in FX,'undefined scripted helper '+k)
    gui=cw.read_tree(MOD/'interface/countrygovernmentview.gui')
    require(cw.strip_custom(gui)==cw.read_tree(cw.effective('interface/countrygovernmentview.gui',False)),'native GUI changed')
    names={cw.one(b,'name'):b for k,_,b in cw.walk(gui) if isinstance(b,list) and cw.values(b,'name') and cw.one(b,'name').startswith(P)}
    bindings=cw.read_tree(MOD/'common/custom_gui/zhx_feudatory_gui.txt')
    require(set(names)=={cw.one(b,'name') for _,_,b in bindings},'GUI bindings mismatch')
    require(len(names)==5,'unexpected custom control count')
    council_buttons={cw.one(b,'name'):b for k,_,b in cw.read_tree(MOD/'common/custom_gui/zhx_tianxia_gui.txt') if k=='custom_button'}
    for label,letter in [('support','a'),('oppose','b'),('abstain','c')]:
        button=council_buttons['zhx_gui_council_vote_'+label+'_button']
        effect=cw.one(button,'effect')
        require(len(effect)==1 and effect[0][0]=='hidden_effect','public vote tooltip exposes internal tally script')
        require(cw.contains(effect[0][2],'zhx_cast_tianxia_council_vote_'+letter,'yes'),'public vote action disconnected')
    for name,b in names.items():
        require(cw.one(b,'scripted')=='yes','control not scripted')
        pos=cw.one(b,'position');x=int(cw.one(pos,'x'));y=int(cw.one(pos,'y'))
        width=int(cw.values(b,'maxWidth')[0]) if cw.values(b,'maxWidth') else 224
        height=int(cw.values(b,'maxHeight')[0]) if cw.values(b,'maxHeight') else 31
        require(x>=24 and x+width<=360 and y>=230 and y+height<=362,'government panel overlap')
    return len(keys)


def scenarios():
    n=0
    for dignity,m,d,p in [('bo',100,100,10),('hou',200,200,20)]:
        for merit,dev,cities in product([0,m-1,m-0.001,m,m+1],[0,d-1,d-0.001,d,d+1],[0,p-1,p,p+1]):
            w=World(dignity);w.actor.vars['zhx_merit_term']=merit;w.actor.dev=dev;w.actor.cities=cities
            expected=merit>=m and dev>=d and cities>=p
            require(w.check(P+'can_submit')==expected,f'threshold {dignity,merit,dev,cities}');n+=1
        for reason in ('used','pending','war','busy','queued','republic','outsider','TSF','tianzi','gong'):
            w=World(dignity)
            if reason=='used':w.actor.flags.add(P+'used_this_term')
            if reason=='pending':w.actor.flags.add(P+'request_pending')
            if reason=='war':w.actor.enemies.add('CZH')
            if reason=='busy':w.host.flags.add('zhx_council_phase_ballot_open')
            if reason=='queued':w.host.flags.add('zhx_council_pending_ritual_breakdown')
            if reason=='republic':w.actor.government='republic'
            if reason=='outsider':w.actor.flags.discard('zhx_member')
            if reason=='TSF':w.actor.tag='TSF'
            if reason=='tianzi':w.actor.flags.add('zhx_tianzi')
            if reason=='gong':w.actor.reforms={REFORMS[2]}
            require(not w.check(P+'can_submit'),'eligibility '+reason);n+=1
        # Two rounds of duplicate sends; a rollover while consent is pending.
        w=World(dignity);before=copy.deepcopy(w.actor)
        w.call(P+'submit_petition');require(P+'request_pending' in w.actor.flags,'submission missing')
        count=len(w.events);w.call(P+'submit_petition');require(len(w.events)==count,'duplicate request')
        w.call(P+'begin_new_term',w.host);w.actor.vars['zhx_merit_term']=0
        require(w.check(P+'request_is_valid'),'rollover invalidates frozen merit')
        require(not w.check(P+'can_submit'),'pending request duplicated after rollover')
        w.call(P+'open_council',w.host)
        require(('CZH','zhx_system.23',['365']) in w.events,'wrong shared deadline')
        require('zhx_council_phase_ballot_open' in w.host.flags,'council not opened')
        for t in ('GDD','GUI','QIN'):
            w.call('zhx_cast_tianxia_council_vote_a',w.c[t])
        w.call('zhx_cast_tianxia_council_vote_b',w.c['XU2'])
        w.call('zhx_cast_tianxia_council_vote_a',w.host)
        require(w.host.vars['zhx_council_vote_a_count']==3,'Tianzi voted or duplicate counted')
        w.call('zhx_cast_tianxia_council_vote_b',w.actor)
        require(w.host.vars['zhx_council_vote_a_count']==2 and w.host.vars['zhx_council_vote_b_count']==2,'revote did not replace')
        w.call('zhx_cast_tianxia_council_vote_a',w.actor)
        w.call('zhx_resolve_tianxia_council',w.host);w.call(P+'resolve_promotion',w.host)
        next_r=REFORMS[1 if dignity=='bo' else 2]
        require(w.actor.reforms=={next_r},'wrong promotion / skipped rank')
        require(w.actor.rank==(1 if dignity=='bo' else 2),'rank not explicitly set')
        require(w.actor.ruler==before.ruler and w.actor.heir==before.heir and w.actor.estates==before.estates,'ruler/estate changed')
        require(w.actor.vars['zhx_merit']==77 and w.actor.vars['zhx_merit_lifetime']==555,'merit charged')
        require(not w.check('zhx_tianxia_council_is_busy'),'council stuck')
        require(P+'applicant' not in w.targets and P+'request_pending' not in w.actor.flags,'stale request')
        n+=12
        for outcome in ('refusal','tie','all_abstain','land_lost','annexed','exit','government_changed'):
            w=World(dignity);w.call(P+'submit_petition')
            if outcome=='refusal':w.call(P+'refuse_petition',w.host)
            else:
                w.call(P+'open_council',w.host)
                w.call('zhx_cast_tianxia_council_vote_a',w.actor)
                if outcome=='tie':w.call('zhx_cast_tianxia_council_vote_b',w.c['GUI'])
                if outcome=='all_abstain':w.call('zhx_cast_tianxia_council_vote_c',w.actor)
                if outcome=='land_lost':w.actor.dev=1
                if outcome=='annexed':w.actor.alive=False
                if outcome=='exit':w.actor.flags.discard('zhx_member')
                if outcome=='government_changed':w.actor.government='republic'
                w.call(P+'maintain_petition',w.host)
                require(w.check('zhx_tianxia_council_is_busy'),'invalid ballot freed before original deadline')
                w.call('zhx_resolve_tianxia_council',w.host);w.call(P+'resolve_promotion',w.host)
            require(w.actor.reforms=={P+dignity+'_reform'},'failed petition promoted')
            require(P+'used_this_term' in w.actor.flags,'failed petition refunded turn')
            require(not w.check('zhx_tianxia_council_is_busy'),'failure left busy lock');n+=1
    # AI selects once from facts; hostile first, friends support, neutral abstain.
    for kind,letter in [('self','a'),('ally','a'),('friend','a'),('rival','b'),('enemy','b'),('dislike','b'),('neutral','c')]:
        w=World();w.call(P+'submit_petition');w.call(P+'open_council',w.host)
        c=w.actor if kind=='self' else w.c['GUI'];c.ai=True
        if kind=='ally':c.allies.add('GDD')
        if kind=='friend':c.opinions['GDD']=50
        if kind=='rival':c.rivals.add('GDD')
        if kind=='enemy':c.enemies.add('GDD')
        if kind=='dislike':c.opinions['GDD']=-1
        w.call(P+'choose_ai_vote',c)
        require('zhx_council_vote_'+letter in c.flags,'AI vote '+kind);n+=1
    # Modifying only the control cache cannot change the native dignity.
    for d,rank in [('bo',1),('hou',1),('gong',2)]:
        w=World(d);w.actor.rank=3;w.call(P+'sync_government');require(w.actor.rank==rank,'rank cap')
        w.actor.flags.discard('zhx_member');w.call(P+'sync_government')
        require(not (w.actor.reforms & set(REFORMS)) and 'feudalism_reform' in w.actor.reforms,'exit keeps fixed rank reform');n+=2
    for crown in ('gdd_czc_crowned','gdd_hak_crowned'):
        w=World();w.actor.flags.add(crown);w.actor.reforms={'autocracy_reform'};w.actor.rank=2
        require(not w.check(P+'is_eligible'),'crowned republic branch overwritten')
        w.call(P+'sync_government');require(w.actor.reforms=={'autocracy_reform'} and w.actor.rank==2,'crown route changed');n+=1
    for opened,lost in product((False,True),('annexed','title_lost')):
        w=World();w.call(P+'submit_petition')
        if opened:w.call(P+'open_council',w.host)
        if lost=='annexed':w.host.alive=False
        else:w.host.flags.discard('zhx_tianzi')
        w.call(P+'recover_lost_host',w.c['GUI'])
        require(P+'applicant' not in w.targets and P+'host' not in w.targets,'lost host leaves targets')
        require(P+'request_pending' not in w.actor.flags and P+'used_this_term' in w.actor.flags,'lost host refunds attempt or leaves pending')
        require(not w.check('zhx_tianxia_council_is_busy'),'lost host leaves busy state');n+=1
    w=World();w.call(P+'submit_petition');require(w.check(P+'event_matches_request'),'current event rejected')
    w.targets[P+'event_applicant']=w.c['GUI'];require(not w.check(P+'event_matches_request'),'stale event mutates another applicant');n+=1
    return n


def main():
    keys=source_contracts();count=scenarios()
    print(f'PASS: 58 opening monarchies; TSF, republics and Tianzi excluded; three fixed-rank reforms; {keys} encoded keys and 5 native-root controls')
    print(f'PASS: {count} source-driven threshold, snapshot, rollover, ballot, refusal, lifecycle and AI cases')
    print('Static contracts only. Native diplomacy, startup, rank locking, title precedence and GUI rendering require a fresh-game runtime pass.')


if __name__=='__main__':
    main()

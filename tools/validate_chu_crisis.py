#!/usr/bin/env python3
"""Execute the production Chu scripts in a narrow, fail-closed state model.

This establishes script contracts, not engine behavior or UI rendering.
"""
from pathlib import Path
import itertools
import re
import validate_zhou_feudatories as base
from encode_eu4_chinese_localisation import verify_file

cw, MOD = base.cw, base.MOD
P = 'zhx_chu_'


class World(base.World):
    def __init__(self, n=6):
        super().__init__()
        self.actor = base.Country('CHC')
        self.c['CHC'] = self.actor
        self.root = self.actor
        self.targets[P+'realm'] = self.actor
        self.actor.flags.update([P+'active', 'zhx_member'])
        self.actor.ruler_flags = {P+'opening_ruler'}
        self.durations = {}
        for i in range(n):
            c = base.Country('S'+str(i), ai=True, subject=True)
            c.flags.add('zhx_member')
            c.overlord = 'CHC'
            c.subject_type = 'vassal'
            c.ld = 0
            self.c[c.tag] = c

    def test(self, k, v, c, prev=None):
        if k == 'is_subject_of':
            t = self.target(v,c,prev)
            return t is not None and getattr(c,'overlord',None) == t.tag
        if k == 'is_subject_of_type': return getattr(c,'subject_type',None)==v
        if k == 'has_ruler_flag': return v in getattr(c,'ruler_flags',set())
        if k == 'liberty_desire': return getattr(c,'ld',0)>=float(v)
        return super().test(k,v,c,prev)

    def run(self, tree, c, prev=None, depth=0):
        # Keep complete if/else chains together while intercepting only the
        # native primitives needed by this feature. Child scopes recurse here.
        i=0
        while i<len(tree):
            k,op,v=tree[i]
            if k=='if':
                j=i+1
                while j<len(tree) and tree[j][0] in ('else_if','else'):j+=1
                super().run(tree[i:j],c,prev,depth)
                i=j;continue
            if k=='every_subject_country':
                limits=cw.values(v,'limit')
                for t in list(self.c.values()):
                    if t.alive and getattr(t,'overlord',None)==c.tag and (not limits or self.cond(limits[0],t,c)):
                        self.run([e for e in v if e[0]!='limit'],t,c,depth+1)
            elif k=='add_country_modifier':
                name=cw.one(v,'name');c.modifiers.add(name)
                self.durations[c.tag,name]=int(cw.one(v,'duration'))
            elif k=='remove_country_modifier':c.modifiers.discard(v)
            elif k=='grant_independence':c.overlord=None;c.subject=False
            elif k=='set_ruler_flag':c.ruler_flags.add(v)
            else:super().run([tree[i]],c,prev,depth)
            i+=1

    def count(self):
        self.call(P+'count_subjects')
        return self.actor.vars[P+'subject_count']


def main():
    checks=0
    def check(ok,msg):
        nonlocal checks
        checks+=1
        assert ok,msg
    paths=list(MOD.glob('common/**/*chu_crisis*.txt'))+list(MOD.glob('events/*chu_crisis*.txt'))
    loc=MOD/'localisation_source/028_zhx_chu_crisis_readable_utf8.txt'
    keys=set(re.findall(r'^ ([\w.]+):',loc.read_text(),re.M))
    events={}
    for p in paths:
        tree=cw.read_tree(p)
        for k,_,v in tree:
            if k=='country_event':events[cw.one(v,'id')]=v
        for k,_,v in cw.walk(tree):
            if k in ('name','title','desc','custom_tooltip') and isinstance(v,str) and v.startswith(P.replace('_','_',1)):
                check(v in keys,'missing localisation '+v)
            if k.startswith(P) and v=='yes':check(k in base.FX or k in base.TR,'unknown helper '+k)
        check(not any(k in {'define_ruler','kill_ruler','add_dip_power','add_adm_power','add_mil_power','change_liberty_desire'} for k,_,_ in cw.walk(tree)), 'unapproved ruler/mana/decaying LD effect')
    verify_file(loc,MOD/'localisation/replace/028_zhx_chu_crisis_l_english.yml')
    check(not re.search('[−﹣－]|[‒–][0-9]',loc.read_text()),'unsafe minus glyph')
    # Runtime regression: recurring delayed events accumulated event scopes and
    # exhausted the macOS engine stack. Native pulses own recurring maintenance.
    for p in [MOD/'events/zhx_chu_crisis_events.txt', MOD/'common/scripted_effects/zhx_chu_crisis_effects.txt']:
        for k,_,v in cw.walk(cw.read_tree(p)):
            if k=='country_event' and isinstance(v,list):
                target=cw.one(v,'id')
                if target in ('zhx_chu.2','zhx_chu.11'):
                    check(cw.one(v,'is_triggered_only')=='yes','maintenance must not reschedule itself')
    for p in paths:
        for k,_,v in cw.walk(cw.read_tree(p)):
            if k=='id' and isinstance(v,str) and v.startswith('zhx_chu.'):
                check(v in events,'missing event '+v)
            if k=='picture':
                check(v in (MOD/'interface/zhx_opening_background_eventpictures.gfx').read_text(),'unknown picture '+v)
    # All numerical modifier fields are asserted against the accepted design.
    mods=cw.read_tree(MOD/'common/event_modifiers/zhx_chu_crisis_modifiers.txt')
    for n,x in [(4,'-0.10'),(5,'-0.20'),(6,'-0.30')]:
        check(dict((k,v) for k,_,v in cw.one(mods,P+'divided_'+str(n)))==dict(global_tax_modifier=x,manpower_recovery_speed=x,global_prov_trade_power_modifier=x),'penalty '+str(n))
    tm=cw.one(cw.read_tree(MOD/'common/triggered_modifiers/zhx_chu_crisis_modifiers.txt'),P+'unquiet_feudatories')
    check(cw.one(tm,'liberty_desire')=='50','LD units')
    check(cw.contains(cw.one(tm,'trigger'),P+'is_counted_subject','yes'),'aftermath must be relation-gated')
    # Every count, including all reversals and counts above the capped tier.
    for n in range(10):
        w=World(n)
        w.call(P+'refresh_penalties')
        expected={P+'divided_'+str(min(n,6))} if n>=4 else set()
        check(w.actor.modifiers==expected,'tier '+str(n))
        w.call(P+'refresh_penalties')
        check(w.actor.modifiers==expected,'idempotent tier')
        w.call(P+'record_departure')
        check((P+'pending' in w.actor.flags)==(n>=4),'departure boundary')
        w.call(P+'record_departure')
        check(w.actor.vars[P+'departure_count']==n,'departure snapshot')
        if n<=3:
            w.call(P+'maintenance')
            check(P+'complete' in w.actor.flags and not w.actor.modifiers,'safe finish')
        else:
            w.host.flags.add('zhx_council_phase_ballot_open')
            w.call(P+'try_open_council')
            check(P+'pending' in w.actor.flags,'busy queue')
            for c in w.c.values():
                if getattr(c,'overlord',None)=='CHC':c.overlord=None
            w.call(P+'maintenance')
            check(P+'pending' in w.actor.flags and not w.actor.modifiers,'drop below three does not cancel')
            w.host.flags.discard('zhx_council_phase_ballot_open')
            w.call(P+'try_open_council')
            check(P+'ballot' in w.actor.flags,'queued zero-subject incident still opens')
            check(('CZH','zhx_system.23',['365']) in w.events,'shared deadline')
    w=World(6)
    for tag in ['S0','S1','S2']:
        w.c[tag].overlord=None;w.call(P+'refresh_penalties')
    check(not w.actor.modifiers,'release to three')
    w.c['S0'].overlord='CHC';w.call(P+'refresh_penalties')
    check(w.actor.modifiers=={P+'divided_4'},'reacquisition restores penalty')
    w.c['S0'].subject_type='march';check(w.count()==4,'march counts')
    w.c['S0'].subject_type='tributary_state';check(w.count()==3,'tributary excluded')
    # Outcomes depend on strict vote balance, never on remaining subject count.
    for n,balance in itertools.product(range(8),range(-3,4)):
        w=World(n);w.actor.flags.add(P+'ballot');w.targets[P+'host']=w.host
        w.host.flags.update(['zhx_council_kind_chu','zhx_council_result_ready','zhx_council_phase_resolving'])
        w.host.vars['zhx_council_a_vs_b']=balance
        w.call(P+'resolve_council',w.host)
        check(P+'complete' in w.actor.flags and P+'active' not in w.actor.flags,'one-shot finish')
        check(w.count()==(0 if balance>0 else n),'independence outcome')
        for c in w.c.values():
            if c.tag.startswith('S'):
                check((P+'dispute_memory' in c.modifiers)==(balance<=0),'aftermath recipients')
                if balance<=0:check(w.durations[c.tag,P+'dispute_memory']==7300,'20 years')
        check('zhx_council_kind_chu' not in w.host.flags,'shared kind cleaned')
        before=list(w.events);w.call(P+'resolve_council',w.host)
        check(before==w.events,'no repeated outcome')
    # AI boundary and precedence, including rival versus alliance conflicts.
    for ld in (0,49,50,100):
        w=World(1);w.host.flags.update(['zhx_council_kind_chu','zhx_council_phase_ballot_open'])
        c=w.c['S0'];c.ld=ld;w.call(P+'choose_ai_vote',c)
        check('zhx_council_vote_'+('a' if ld>=50 else 'b') in c.flags,'LD AI boundary')
    for rival,ally,op in itertools.product((False,True),(False,True),(-1,0,49,50)):
        w=World(0);w.host.flags.update(['zhx_council_kind_chu','zhx_council_phase_ballot_open'])
        c=w.c['QIN'];c.ai=True;c.opinions['CHC']=op
        if rival:c.rivals.add('CHC')
        if ally:c.allies.add('CHC')
        w.call(P+'choose_ai_vote',c)
        vote='a' if rival else 'b' if ally or op>=50 else 'a' if op<0 else 'c'
        check('zhx_council_vote_'+vote in c.flags,'diplomatic AI precedence')
    print(f'PASS: {checks} Chu crisis source/model assertions; engine and rendering require runtime evidence.')


if __name__=='__main__':main()

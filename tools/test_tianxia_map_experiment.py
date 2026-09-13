"""Interpret the generated backup/restore script, NOT engine economics or UI."""
from copy import deepcopy
import unittest
from build_tianxia_map_experiment import build, MOD, FALLEN_PROVINCES, FALLEN_REGIMES
from test_gdd_tianxia_territory import parse


class World:
    def __init__(self):
        outputs,self.goods=build()
        self.effects=parse(outputs[MOD/'common/scripted_effects/zhx_map_experiment.txt'])
        self.triggers=parse(outputs[MOD/'common/scripted_triggers/zhx_map_experiment.txt'])
        self.global_flags=set()
        self.countries=[dict(member=True,modifiers=set()),dict(member=False,modifiers=set())]
        self.provinces=[]
        for good in self.goods+['future_unsupported_good']:
            for owner,zhou in [(0,True),(1,True),(1,False),(None,False)]:
                self.provinces.append(dict(good=good,owner=None if owner is None else self.countries[owner],flags={'zhx_tianxia_province'} if zhou else set()))

    def check(self,body,scope):
        values=[]
        for key,v in body:
            if key=='OR': result=any(self.check([(k,x)],scope) for k,x in v)
            elif key=='AND': result=self.check(v,scope)
            elif key=='NOT': result=not self.check(v,scope)
            elif key=='has_global_flag': result=v in self.global_flags
            elif key=='has_country_flag': result=v in scope.get('flags',set())
            elif key in self.triggers: result=self.check(self.triggers[key],scope)
            elif key=='has_province_flag': result=v in scope['flags']
            elif key=='trade_goods': result=scope['good']==v
            elif key=='any_province': result=any(self.check(v,p) for p in self.provinces)
            elif key=='owner': result=scope['owner'] is not None and self.check(v,scope['owner'])
            elif key=='exists': result=True
            elif key=='zhx_is_tianxia_polity': result=scope['member']
            elif key=='zhx_is_seven_great_feudatory': result=scope['member'] and scope.get('major',False)
            else: raise AssertionError('unknown trigger '+key)
            values.append(result)
        return all(values)

    def execute(self,body,scope):
        previous_if=None
        for key,v in body:
            if key=='limit':continue
            if key=='if':
                previous_if=self.check(dict(v).get('limit',[]),scope)
                if previous_if:self.execute(v,scope)
            elif key=='else':
                assert previous_if is not None
                if not previous_if:self.execute(v,scope)
                previous_if=None
            elif key in ('every_province','every_country'):
                for obj in (self.provinces if key=='every_province' else self.countries):
                    if self.check(dict(v).get('limit',[]),obj):self.execute(v,obj)
            elif key=='zhx_seed_longxi_fallen_homeland':
                # Generic goods fixtures are outside the historical region. Dedicated test below
                # executes the generated initializer with real province IDs and regime tags.
                if any('id' in p for p in self.provinces):self.execute(self.effects[key],scope)
            elif key.isdigit():
                for p in self.provinces:
                    if p.get('id')==int(key):self.execute(v,p)
            elif key in FALLEN_REGIMES:
                for c in self.countries:
                    if c.get('tag')==key:self.execute(v,c)
            elif key=='set_country_flag':scope.setdefault('flags',set()).add(v)
            elif key=='set_global_flag':self.global_flags.add(v)
            elif key=='clr_global_flag':self.global_flags.discard(v)
            elif key=='set_province_flag':scope['flags'].add(v)
            elif key=='clr_province_flag':scope['flags'].discard(v)
            elif key=='change_trade_goods':scope['good']=v
            elif key=='add_country_modifier':scope['modifiers'].add(dict(v)['name'])
            elif key=='remove_country_modifier':scope['modifiers'].discard(v)
            else:raise AssertionError('unknown effect '+key)

    def run(self,name,player=0):self.execute(self.effects['zhx_map_exp_'+name],self.countries[player])


class MapExperimentTests(unittest.TestCase):
    def test_hud_restore_delegates_to_complete_restore_effect(self):
        outputs, _ = build()
        gui = outputs[MOD/'common/custom_gui/zhx_map_experiment.txt']
        # Parse repeated custom_button blocks separately: the backdrop must never restore.
        buttons = gui.split('custom_button = {')[1:]
        restore = next(b for b in buttons if 'name = zhx_map_exp_hud_restore' in b)
        self.assertIn('has_global_flag = zhx_map_exp_active', restore)
        self.assertRegex(restore, r'effect\s*=\s*\{\s*hidden_effect\s*=\s*\{\s*zhx_map_exp_restore\s*=\s*yes\s*\}\s*\}')
        self.assertNotIn('clr_global_flag', restore)
        background = next(b for b in buttons if 'name = zhx_map_exp_hud_background' in b)
        self.assertNotIn('zhx_map_exp_restore =', background)

    def test_all_32_goods_round_trip_including_gold_coal_unknown_and_three_colours(self):
        w=World();before=deepcopy(w.provinces);w.run('open')
        self.assertEqual([p['good'] for p in w.provinces[:4]],['tea','copper','wool',w.goods[0]])
        w.run('restore');self.assertEqual(w.provinces,before)
        self.assertFalse(w.global_flags);self.assertTrue(all(not c['modifiers'] for c in w.countries))

    def test_seven_seats_use_live_identity_and_fallen_takes_priority(self):
        w=World();before=deepcopy(w.provinces)
        w.countries[0]['major']=True
        w.provinces[4]['flags'].add('zhx_map_exp_sample_fallen')
        w.run('open')
        self.assertEqual(w.provinces[0]['good'],'naval_supplies')
        self.assertEqual(w.provinces[4]['good'],'copper')
        self.assertEqual(w.provinces[2]['good'],'wool')
        w.run('restore');w.countries[0]['major']=False
        w.run('open');self.assertEqual(w.provinces[0]['good'],'tea')
        w.run('restore')
        self.assertEqual([p['good'] for p in w.provinces],[p['good'] for p in before])

    def test_longxi_seed_reconquest_and_persistent_ledger(self):
        w=World();w.countries[0]['tag']='WGS';w.countries[1]['member']=True
        w.provinces=[dict(id=pid,good='grain',owner=w.countries[0],flags=set()) for pid in FALLEN_PROVINCES]
        w.run('open')
        self.assertTrue(all(p['good']=='copper' for p in w.provinces))
        w.run('restore')
        self.assertTrue(all(p['good']=='grain' and 'zhx_longxi_fallen_homeland' in p['flags'] for p in w.provinces))
        w.provinces[0]['owner']=w.countries[1]
        w.run('open');self.assertEqual(w.provinces[0]['good'],'tea');w.run('restore')
        w.countries[1]['major']=True
        w.run('open');self.assertEqual(w.provinces[0]['good'],'naval_supplies');w.run('restore')
        w.provinces[0]['owner']=w.countries[0]
        w.run('open');self.assertEqual(w.provinces[0]['good'],'copper');w.run('restore')
        w.provinces[0]['flags'].discard('zhx_tianxia_province')
        w.run('open');self.assertEqual(w.provinces[0]['good'],'wool');w.run('restore')

    def test_double_open_cannot_overwrite_backup(self):
        w=World();before=deepcopy(w.provinces);w.run('open');active=deepcopy(w.provinces)
        w.run('open',player=1);self.assertEqual(w.provinces,active)
        w.run('restore');self.assertEqual(w.provinces,before)

    def test_recovery_after_global_flag_loss_and_switching_country(self):
        w=World();before=deepcopy(w.provinces);w.run('open');active=deepcopy(w.provinces)
        w.global_flags.clear();w.run('open',player=1);self.assertEqual(w.provinces,active)
        w.run('restore',player=1);self.assertEqual(w.provinces,before)

    def test_restore_is_idempotent_and_clears_disposable_fallen_sample(self):
        w=World();before=deepcopy(w.provinces);w.run('open')
        w.provinces[0]['flags'].add('zhx_map_exp_sample_fallen');w.provinces[0]['good']='copper'
        w.run('restore');w.run('restore');self.assertEqual(w.provinces,before)

    def test_unknown_future_goods_and_unowned_provinces_are_never_modified(self):
        w=World();before=deepcopy(w.provinces);w.run('open')
        for i,p in enumerate(before):
            if p['owner'] is None or p['good']=='future_unsupported_good':
                for field in ('good','flags'):self.assertEqual(w.provinces[i][field],p[field])


if __name__=='__main__':unittest.main(verbosity=2)

"""Regression contract for the 2026-09-10 decisions, using authored scripts.

This is a source/scope model, not evidence of EU4 runtime behaviour.
"""
from copy import deepcopy
from decimal import Decimal
import unittest
from test_gdd_tianxia_buttons import ButtonWorld, ADD, LEAVE, TERRITORY, REWARD, entries, MOD
from test_gdd_tianxia_territory import parse

class Integration(unittest.TestCase):
    def test_admission_without_mandate_consumes_first_reward(self):
        w = ButtonWorld()
        w.emperor = None
        w.targets.pop('EmperorOfChina')
        p = w.province(member=False, development=20)
        w.click(ADD)
        self.assertIn(TERRITORY, p.flags)
        self.assertIn(REWARD, p.flags)
        self.assertIn('zhx_ritual_warscore_active', p.flags)
        p.flags.pop(TERRITORY)
        w.emperor = 'CZH'
        w.targets['EmperorOfChina'] = w.countries['CZH']
        w.click(ADD)
        self.assertEqual(w.countries['CZH'].mandate, 50)

    def test_foreign_removal_without_mandate(self):
        w = ButtonWorld()
        w.actor('KRC')
        p = w.province(owner='KRC', flags={TERRITORY: 0, REWARD: 0})
        w.emperor = None
        w.targets.pop('EmperorOfChina')
        self.assertTrue(w.test('gdd_can_remove_province_from_tianxia_for_country_trigger', p, who='ROOT'))
        w.execute(w.effects['gdd_remove_province_from_tianxia_effect'], [w.root,p])
        self.assertNotIn(TERRITORY,p.flags)
        self.assertIn(REWARD,p.flags)

    def test_exit_without_mandate_cancels_pending_and_forfeits_dignity(self):
        w = ButtonWorld()
        w.emperor = None
        w.targets.pop('EmperorOfChina')
        p = w.province()
        w.root.flags.update(zhx_feudatory_remembered_hou=0, zhx_qn_pending=0, zhx_qn_joining=0, zhx_wm_tribute_pending=0)
        w.click(LEAVE)
        w.choose('gdd_tianxia_territory.3')
        self.assertIn('zhx_feudatory_forfeited',w.root.flags)
        self.assertIn('zhx_tianxia_rejoin_bar',w.root.modifiers)
        self.assertNotIn('zhx_feudatory_remembered_hou',w.root.flags)
        self.assertFalse({'zhx_qn_pending','zhx_qn_joining','zhx_wm_tribute_pending'} & set(w.root.flags))
        self.assertNotIn(TERRITORY,p.flags)
        w.execute(w.effects['zhx_register_tianxia_member'],[w.root])
        self.assertNotIn('zhx_member',w.root.flags)
        w.root.modifiers.remove('zhx_tianxia_rejoin_bar')
        w.global_flags.add('zhx_feudatory_initialised')
        w.execute(w.effects['zhx_register_tianxia_member'],[w.root])
        self.assertIn('zhx_member',w.root.flags)
        self.assertIn('zhx_feudatory_zi_reform',w.root.reforms)
        self.assertNotIn(TERRITORY,p.flags)

    def test_member_without_registered_land_retains_politics(self):
        w=ButtonWorld()
        w.province(member=False)
        self.assertTrue(w.test('zhx_is_tianxia_member',w.root))
        self.assertTrue(w.enabled(LEAVE))

    def test_dismantle_ignores_foreign_mandate_capital(self):
        w=ButtonWorld(); w.ready_to_dismantle()
        w.emperor='OTH'; w.targets['EmperorOfChina']=w.countries['OTH']
        w.countries['OTH'].capital=w.province('OTH',controller='OTH')
        w.native_reforms.add('vassalize_tributaries_decision')
        w.global_flags.add('eoc_vassalize_tributaries')
        self.assertTrue(w.test('gdd_can_dismantle_tianxia_trigger',w.root))
        w.countries['CZH'].reforms.add('zhx_tianzi_reform')
        w.countries['CZH'].modifiers.add('zhx_wangshi_training')
        w.global_flags.update({'zhx_qn_active','zhx_wm_tribute_queued'})
        w.countries['YAN'].flags.update(zhx_wm_tribute_pending=0,zhx_qn_joining=0)
        w.choose('gdd_tianxia_territory.4')
        self.assertEqual(w.emperor,'OTH')
        self.assertIn('eoc_vassalize_tributaries',w.global_flags)
        self.assertEqual(w.native_teardowns,[])
        self.assertNotIn('zhx_tianzi_reform',w.countries['CZH'].reforms)
        self.assertNotIn('zhx_wangshi_training',w.countries['CZH'].modifiers)
        self.assertFalse({'zhx_qn_active','zhx_wm_tribute_queued'} & w.global_flags)
        self.assertFalse({'zhx_qn_joining','zhx_wm_tribute_pending'} & set(w.countries['YAN'].flags))
        before=deepcopy([vars(c) for c in w.countries.values()])
        w.execute(w.effects['zhx_initialise_tianxia_system'],[w.root])
        self.assertEqual(before,[vars(c) for c in w.countries.values()])

    def test_authority_follows_tianzi_not_mandate(self):
        w=ButtonWorld(); w.emperor='OTH'; w.targets['EmperorOfChina']=w.countries['OTH']
        w.countries['CZH'].variables['gdd_authority_integer_display']=Decimal(50)
        w.actor('CZH')
        self.assertTrue(w.test('gdd_celestial_action_authorized_trigger',w.root))
        w.actor('OTH')
        self.assertFalse(w.test('gdd_celestial_action_authorized_trigger',w.root))
        w.targets['gdd_principal_vassal']=w.countries['YAN']
        w.countries['CZH'].variables['gdd_authority_integer_display']=Decimal(-50)
        w.actor('YAN')
        self.assertTrue(w.test('gdd_celestial_action_authorized_trigger',w.root))

    def test_peaceful_foreign_annexation_does_not_queue_mandate(self):
        w=ButtonWorld();w.actor('KRC');w.recipient=w.countries['YAN']
        w.execute(w.effects['gdd_apply_external_tianxia_annexation_mandate_loss_effect'],[w.root])
        self.assertNotIn('zhx_external_extinction_mandate_queued',w.countries['CZH'].variables)

    def test_stale_request_cannot_unlock_new_request_elsewhere(self):
        w=ButtonWorld();p=w.province()
        w.root.flags['gdd_tianxia_unlawful_request_pending']=0
        w.targets.update(gdd_tianxia_unlawful_province=p,gdd_tianxia_unlawful_actual_owner=w.root,gdd_tianxia_unlawful_addressee=w.root)
        w.execute(w.effects['gdd_clear_tianxia_unlawful_request_effect'],[w.root])
        self.assertIn('gdd_tianxia_unlawful_request_pending',w.root.flags)
        p.flags['gdd_tianxia_unlawful_request_pending']=0
        w.execute(w.effects['gdd_clear_tianxia_unlawful_request_effect'],[w.root])
        self.assertNotIn('gdd_tianxia_unlawful_request_pending',w.root.flags)

    def test_refusal_opinion_and_reform_cost_contracts(self):
        opinions=parse((MOD/'common/opinion_modifiers/zhx_appeal_opinions.txt').read_text())
        self.assertEqual(dict(opinions['zhx_opinion_refused_valid_appeal']),{'opinion':'-50','min':'-200','yearly_decay':'5'})
        action=dict(next(v for k,v in entries(MOD/'common/new_diplomatic_actions/zhx_diplomacy_actions.txt') if k=='zhx_appeal_to_tianzi_for_relief'))
        for response in ('on_accept','on_decline'):
            self.assertIn(('zhx_appeal_still_valid','yes'),dict(dict(action[response])['if'])['limit'])
        fx=(MOD/'common/scripted_effects/gdd_celestial_mandate_effects.txt').read_text()
        self.assertNotIn('gdd_apply_tianxia_defense_refusal_mandate_loss_effect',fx)
        proxy=parse((MOD/'common/scripted_effects/gdd_celestial_proxy_effects.txt').read_text())
        enact=str(proxy['gdd_enact_proxy_celestial_reform_effect'])
        self.assertIn("('gdd_pay_reform_authority_cost', 'yes')",enact)
        self.assertNotIn('add_mandate',enact)
        self.assertNotIn('add_stability',enact)

if __name__=='__main__':unittest.main(verbosity=2)

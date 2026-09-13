"""Province/player scope and academy-reader regressions, without emulating EU4 UI."""
import json
import unittest
from copy import deepcopy

from test_gdd_tianxia_buttons import ButtonWorld, entries, MOD
from validate_gdd_tianxia_province_layout import children, validate_layout


class ProvincePanelTests(unittest.TestCase):
    def setUp(self):
        self.w = ButtonWorld()
        self.player = self.w.countries['YAN']
        self.p = self.w.province('LUU')
        self.w.root = self.p
        self.w.recipient = self.player
        self.gui = children(entries(MOD/'common/custom_gui/zhx_province_panel.txt'))
        self.readers = children(entries(MOD/'customizable_localization/zhx_province_panel.txt'))
        self.academies = json.loads((MOD.parent/'planning/religion_academies/academy_manifest.json').read_text())['academies']

    def read(self, name, province=None):
        p = province or self.p
        for key, body in self.readers[name].body:
            if key == 'text':
                fields = dict(body)
                if self.w.evaluate(fields['trigger'], [p]):
                    return fields['localisation_key']
        self.fail('reader has no matching fallback: '+name)

    def test_page_switch_belongs_to_viewer_and_does_not_change_province_or_owner(self):
        before_p=deepcopy(self.p)
        owner=deepcopy(self.w.countries['LUU'])
        self.w.execute(self.gui['zhx_province_mod_tab']['effect'],[self.p])
        self.assertIn('zhx_province_mod_page',self.player.flags)
        self.assertEqual(self.p,before_p)
        self.assertEqual(self.w.countries['LUU'],owner)
        self.w.execute(self.gui['zhx_province_buildings_tab']['effect'],[self.p])
        self.assertNotIn('zhx_province_mod_page',self.player.flags)

    def test_page_preference_is_independent_between_players(self):
        self.w.execute(self.gui['zhx_province_mod_tab']['effect'],[self.p])
        self.assertTrue(self.w.evaluate(self.gui['zhx_province_mod_window']['potential'],[self.p]))
        self.w.recipient=self.w.countries['LUU']
        self.assertFalse(self.w.evaluate(self.gui['zhx_province_mod_window']['potential'],[self.p]))

    def test_all_manifest_academies_follow_actual_modifier_after_relocation(self):
        for a in self.academies:
            self.p.modifiers={a['modifier']}
            self.assertEqual(self.read('GetZhxProvinceAcademyName'),f"zhx_province_academy_{a['key']}_name")
            self.assertEqual(self.read('GetZhxProvinceAcademyDetails'),a['modifier']+'_desc')
            other=self.w.province('YAN');other.modifiers=set(self.p.modifiers)
            self.p.modifiers.clear()
            self.assertEqual(self.read('GetZhxProvinceAcademyName'),'zhx_province_academy_none')
            self.assertEqual(self.read('GetZhxProvinceAcademyName',other),f"zhx_province_academy_{a['key']}_name")

    def test_ruins_never_count_as_active_and_multiple_ruins_remain_readable(self):
        self.p.modifiers={f"zhx_academy_ruins_{a['key']}" for a in self.academies}
        self.assertEqual(self.read('GetZhxProvinceAcademyName'),'zhx_province_academy_none')
        for a in self.academies:
            self.assertEqual(self.read('GetZhxProvinceRuins'+a['key'].title()),'zhx_province_ruins_'+a['key'])

    def test_academy_protection_uses_owner_not_viewer(self):
        self.p.modifiers={'zhx_academy_minglun'}
        self.player.flags['zhx_doctrine_ru']=0
        self.assertEqual(self.read('GetZhxProvinceAcademyState'),'zhx_province_academy_unprotected')
        self.w.countries['LUU'].flags['zhx_doctrine_ru']=0
        self.assertEqual(self.read('GetZhxProvinceAcademyState'),'zhx_province_academy_main_protected')
        self.p.modifiers.add('zhx_academy_under_expulsion')
        self.assertEqual(self.read('GetZhxProvinceAcademyState'),'zhx_province_academy_expelling')

    def test_foreign_academy_cannot_be_managed_by_viewer(self):
        self.p.modifiers={'zhx_academy_minglun','zhx_academy_under_expulsion'}
        for name in ['zhx_province_academy_manage','zhx_province_academy_withdraw']:
            self.assertFalse(self.w.evaluate(self.gui[name]['potential'],[self.p]))

    def test_status_refreshes_with_selected_province_without_cached_targets(self):
        self.assertEqual(self.read('GetZhxProvinceTianxiaStatus'),'zhx_province_tianxia_member')
        other=self.w.province('KRC',member=False,trade_company=True)
        self.assertEqual(self.read('GetZhxProvinceTianxiaStatus',other),'zhx_province_tianxia_tc')
        other.trade_company=False;other.hre=True
        self.assertEqual(self.read('GetZhxProvinceTianxiaStatus',other),'zhx_province_tianxia_hre')

    def test_background_has_no_effect(self):
        before=deepcopy(self.p)
        self.w.execute(self.gui['zhx_province_mod_background']['effect'],[self.p])
        self.assertEqual(self.p,before)

    def test_layout_keeps_native_controls_and_disjoint_mod_content(self):
        validate_layout()


if __name__=='__main__':unittest.main(verbosity=2)

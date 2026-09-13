"""Offline checks of shipped directory scripts; not an EU4 runtime emulator.

Reuses the project's strict scope harness. Unknown interfaces fail. These tests
cover ownership races, cache truth, identity and navigation, not GUI rendering.
"""
import json
from pathlib import Path
import re
import unittest

from build_zhx_academy_directory import MANIFEST, MOD, VISIBLE_ROWS, render
from encode_eu4_chinese_localisation import verify_file
from test_gdd_tianxia_buttons import ButtonWorld, entries


class DirectoryWorld(ButtonWorld):
    def __init__(self):
        super().__init__()
        self.buttons = {dict(v)["name"]: dict(v) for k, v in entries(
            MOD / "common/custom_gui/zhx_academy_directory.txt") if k == "custom_button"}
        self.directory_events = {dict(v)["id"]: dict(v) for k, v in entries(
            MOD / "events/zhx_academy_directory.txt") if k == "country_event"}
        for country in self.countries.values():
            country.religion = "confucianism"
            country.primary_culture = "gdd_guangfu"
            country.adm_power = 100
            country.stability = 2
            country.flags["zhx_doctrine_fa"] = 0
        self.provinces = []
        self.actor("CZH")
        self.dispatched = []
        # The shared harness merges local/global targets. Native event goto
        # does not: keep event snapshots separate for this regression.
        self.local_targets = {}

    def evaluate(self, body, stack, params=None):
        for key, value in body:
            if key in ("religion", "primary_culture"):
                ok = getattr(stack[-1], key) == value
            elif key == "adm_power":
                ok = stack[-1].adm_power >= int(value)
            else:
                ok = super().evaluate([(key, value)], stack, params)
            if not ok:
                return False
        return True

    def execute(self, body, stack, params=None):
        # Existing lifecycle is validated separately. Here observe exactly
        # which public action the confirmation actually dispatches.
        for key, value in body:
            if key == "save_event_target_as":
                self.local_targets[value] = stack[-1]
            elif key.startswith("zhx_academy_begin_expulsion_") or key == "zhx_academy_withdraw_current_expulsion":
                self.dispatched.append(key)
            else:
                super().execute([(key, value)], stack, params)

    def click(self, name):
        b = self.buttons[name]
        if self.evaluate(b["potential"], [self.root]) and self.evaluate(b["trigger"], [self.root]):
            self.execute(b["effect"], [self.root])
            return True
        return False

    def effect(self, name):
        self.execute(self.effects[name], [self.root])


class DirectoryBehavior(unittest.TestCase):
    def setUp(self):
        self.w = DirectoryWorld()
        self.site = self.w.province("CZH")
        self.site.modifiers.add("zhx_academy_chongli")
        self.w.effect("zhx_ad_open")

    def gate(self, name):
        return self.w.test(name, self.w.root)

    def test_access_only_lijiao(self):
        self.assertTrue(self.gate("zhx_ad_access"))
        self.w.root.religion = "catholic"
        self.assertFalse(self.w.click("zhx_ad_open_button"))
        self.assertFalse(self.gate("zhx_ad_can_expel_chongli"))

    def test_world_index_reads_migrated_site_and_all_ruins(self):
        new = self.w.province("YAN")
        self.site.modifiers = {"zhx_academy_ruins_chongli"}
        new.modifiers = {"zhx_academy_chongli"}
        old = self.w.province("KRC")
        old.modifiers = {"zhx_academy_ruins_chongli"}
        self.w.effect("zhx_ad_refresh_viewers")
        self.assertIs(self.w.targets["zhx_ad_site_chongli"], new)
        self.assertEqual(self.w.root.variables["zhx_ad_ruins_chongli"], 2)
        self.assertFalse(self.gate("zhx_ad_can_expel_chongli"))

    def test_stale_index_never_counts_as_active_academy(self):
        self.site.modifiers.clear()
        self.assertFalse(self.gate("zhx_ad_live_chongli"))
        self.assertFalse(self.w.click("zhx_ad_row_chongli_0_goto"))
        self.w.effect("zhx_ad_refresh")
        self.assertNotIn("zhx_ad_site_chongli", self.w.targets)

    def test_every_location_event_captures_native_goto_target(self):
        for e in json.loads(MANIFEST.read_text())["academies"]:
            if e["key"] == "chongli":
                continue
            province = self.w.province("YAN")
            province.modifiers.add(e["modifier"])
        self.w.effect("zhx_ad_refresh")
        for event_id, event in self.w.directory_events.items():
            if not 100 <= int(event_id.split(".")[1]) < 200:
                continue
            with self.subTest(event=event_id):
                self.w.local_targets = {}
                self.assertTrue(self.w.evaluate(event["trigger"], [self.w.root]))
                self.w.execute(event["immediate"], [self.w.root])
                # A global-only target would fail here, as in native GetGoToProvince.
                self.assertIn(event["goto"], self.w.local_targets)
                key = event["title"].removeprefix("zhx_ad_goto_").removesuffix("_title")
                self.assertIs(self.w.local_targets[event["goto"]],
                              self.w.targets[f"zhx_ad_site_{key}"])
                self.assertNotIn(event["goto"], self.w.targets)
                self.assertEqual(len(self.w.local_targets), 1)

    def test_open_location_keeps_snapshot_when_world_index_changes(self):
        event = self.w.directory_events["zhx_ad.100"]
        self.w.execute(event["immediate"], [self.w.root])
        first_popup = self.w.local_targets
        self.site.modifiers.clear()
        new = self.w.province("YAN")
        new.modifiers.add("zhx_academy_chongli")
        self.w.actor("YAN")
        self.w.effect("zhx_ad_open")
        self.w.local_targets = {}
        self.w.execute(event["immediate"], [self.w.root])
        self.assertIs(first_popup[event["goto"]], self.site)
        self.assertIs(self.w.local_targets[event["goto"]], new)

    def test_location_event_does_not_snapshot_stale_site(self):
        self.site.modifiers.clear()
        event = self.w.directory_events["zhx_ad.100"]
        self.w.execute(event["immediate"], [self.w.root])
        self.assertNotIn(event["goto"], self.w.local_targets)

    def test_all_scroll_positions_show_six_consecutive_rows(self):
        academies = json.loads(MANIFEST.read_text())["academies"]
        total = len(academies)
        for offset in range(total - VISIBLE_ROWS + 1):
            rows = [name for name, b in self.w.buttons.items()
                    if re.fullmatch(r"zhx_ad_row_[a-z]+_\d+", name)
                    and self.w.evaluate(b["potential"], [self.w.root])]
            expected = {f"zhx_ad_row_{e['key']}_{offset}" for e in academies[offset:offset+VISIBLE_ROWS]}
            self.assertEqual(set(rows), expected)
            if offset < total - VISIBLE_ROWS:
                self.assertTrue(self.w.click("zhx_ad_down"))
        self.assertFalse(self.w.click("zhx_ad_down"))
        for _ in range(total - VISIBLE_ROWS):
            self.assertTrue(self.w.click("zhx_ad_up"))
        self.assertFalse(self.w.click("zhx_ad_up"))

    def test_close_reopen_preserves_selection_and_scroll(self):
        self.w.click("zhx_ad_down")
        self.w.click("zhx_ad_row_baopu_2")  # Invisible; cannot change selection.
        self.w.click("zhx_ad_row_minglun_1")
        self.w.click("zhx_ad_close")
        self.w.effect("zhx_ad_open")
        self.assertEqual(self.w.root.variables["zhx_ad_offset"], 1)
        self.assertEqual(self.w.root.variables["zhx_ad_selected"], 2)

    def test_viewers_keep_independent_selection_and_counts(self):
        self.w.root.variables["zhx_ad_offset"] = 4
        self.w.actor("YAN")
        self.w.effect("zhx_ad_open")
        self.assertEqual(self.w.root.variables["zhx_ad_offset"], 0)
        self.assertEqual(self.w.countries["CZH"].variables["zhx_ad_offset"], 4)

    def test_normalize_out_of_range_state(self):
        self.w.root.variables.update(zhx_ad_offset=100, zhx_ad_selected=-1)
        self.w.effect("zhx_ad_normalize")
        self.assertEqual(self.w.root.variables["zhx_ad_offset"], 6)
        self.assertEqual(self.w.root.variables["zhx_ad_selected"], 1)

    def test_protection_and_cost_gates(self):
        self.assertTrue(self.gate("zhx_ad_can_expel_chongli"))
        for kind, key in [("flags", "zhx_doctrine_ru"),
                          ("modifiers", "zhx_ru_invited_scholar_modifier"),
                          ("flags", "zhx_doctrine_reform_reversal_secondary_ru")]:
            bag = getattr(self.w.root, kind)
            if kind == "flags": bag[key] = 0
            else: bag.add(key)
            self.assertFalse(self.gate("zhx_ad_can_expel_chongli"))
            if kind == "flags": bag.pop(key)
            else: bag.remove(key)
        self.w.root.adm_power = 29
        self.assertFalse(self.gate("zhx_ad_can_expel_chongli"))

    def confirmation_effect(self, event):
        options = [(k, v) for k, v in entries(MOD / "events/zhx_academy_directory.txt")
                   if k == "country_event" and dict(v)["id"] == event][0][1]
        return dict(next(v for k, v in options if k == "option"))["hidden_effect"]

    def test_confirmation_rechecks_ownership_and_freezes_identity(self):
        action = self.confirmation_effect("zhx_ad.200")
        self.w.root.variables["zhx_ad_selected"] = 12
        self.site.owner = "YAN"
        self.w.execute(action, [self.w.root])
        self.assertEqual(self.w.dispatched, [])
        self.site.owner = "CZH"
        self.w.execute(action, [self.w.root])
        self.assertEqual(self.w.dispatched, ["zhx_academy_begin_expulsion_chongli"])

    def test_withdraw_requires_exact_academy_and_pressure(self):
        self.w.root.modifiers.add("zhx_academy_expulsion_campaign")
        self.w.root.flags["zhx_academy_expelling_minglun"] = 0
        self.site.modifiers.add("zhx_academy_under_expulsion")
        self.assertFalse(self.gate("zhx_ad_can_withdraw_chongli"))
        self.w.root.flags["zhx_academy_expelling_chongli"] = 0
        self.assertTrue(self.gate("zhx_ad_can_withdraw_chongli"))
        self.site.owner = "YAN"
        self.assertFalse(self.gate("zhx_ad_can_withdraw_chongli"))


class DirectoryContracts(unittest.TestCase):
    def test_generated_outputs_and_encoding(self):
        for name, text in render().items():
            if name != "directory_gui_fragment":
                self.assertEqual((MOD / name).read_text(), text, name)
        verify_file(MOD / "localisation_source/zhx_academy_directory_readable_utf8.txt",
                    MOD / "localisation/zhx_academy_directory_l_english.yml")

    def test_scripted_objects_bind_once_and_all_sprites_exist(self):
        generated = render()
        gui = generated["directory_gui_fragment"]
        bindings = entries(MOD / "common/custom_gui/zhx_academy_directory.txt")
        bound_names = [dict(v)["name"] for _, v in bindings]
        gui_names = re.findall(r'name = "(zhx_ad_[^"]+)"', gui)
        self.assertEqual(len(bound_names), len(set(bound_names)))
        self.assertEqual(set(gui_names), set(bound_names))
        vanilla = Path.home() / "Library/Application Support/Steam/steamapps/common/Europa Universalis IV"
        if vanilla.exists():
            definitions = "\n".join(p.read_bytes().decode("latin-1") for root in (vanilla, MOD)
                                    for p in (root / "interface").glob("*.gfx"))
            sprites = set(re.findall(r'name\s*=\s*"?([\w]+)', definitions))
            used = set(re.findall(r'(?:spriteType|quadTextureSprite)\s*=\s*"([^"]+)"', gui))
            self.assertFalse(used - sprites, used - sprites)
            for texture in re.findall(r'texturefile = "([^"]+)"', generated["interface/zhx_academy_directory.gfx"]):
                self.assertTrue((MOD / texture).exists() or (vanilla / texture).exists(), texture)

    def test_no_world_scan_in_visibility_or_new_mechanics(self):
        for kind, definition in entries(MOD / "common/custom_gui/zhx_academy_directory.txt"):
            potential = repr(dict(definition)["potential"])
            self.assertNotRegex(potential, r"any_province|every_province|every_country")
        for name in ("common/scripted_effects/zhx_academy_directory.txt", "events/zhx_academy_directory.txt"):
            self.assertNotRegex((MOD / name).read_text(), r"add_(?:adm_power|stability|prestige|permanent_province_modifier)\s*=")


if __name__ == "__main__":
    unittest.main()

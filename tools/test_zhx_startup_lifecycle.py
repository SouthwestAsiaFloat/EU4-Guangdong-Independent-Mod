"""Execute actual Zhou startup/lifecycle scripts; reject duplicate definitions.

The opening fixture overlays installed vanilla/dependency province histories
with this mod. Set EU4_STEAMAPPS for your installation. No game/save writes.
This is an offline scope interpreter, not an EU4 engine simulation.
"""
from copy import deepcopy
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
import re
import unittest

from test_gdd_tianxia_buttons import ButtonWorld, LazyDefinitions, MOD, REWARD, TERRITORY, entries
from validate_czc_government import VANILLA, DEPENDENCIES, read_tree
from validate_gdd_tianxia_territory import named_block

OPENING = (1444, 11, 11)

def at_opening(tree):
    result = [(k, v) for k, op, v in tree if op == "=" and not re.fullmatch(r"\d+\.\d+\.\d+", k)]
    dated = [(tuple(map(int, k.split("."))), v) for k, op, v in tree
             if op == "=" and re.fullmatch(r"\d+\.\d+\.\d+", k)]
    for date, body in sorted(dated):
        if date <= OPENING:
            result.extend((k, v) for k, op, v in body if op == "=")
    return result

@lru_cache(maxsize=1)
def opening_histories():
    assert (VANILLA / "history/provinces").is_dir(), "Set EU4_STEAMAPPS to your Steam steamapps directory"
    files = {}
    for root in (VANILLA, *DEPENDENCIES, MOD):
        for p in sorted((root / "history/provinces").glob("*.txt")):
            match = re.match(r"(\d+)", p.name)
            if match:
                files[int(match[1])] = p
    # Date blocks matter: the current owner can differ from the first owner.
    provinces = [(pid, dict(at_opening(read_tree(p)))) for pid, p in files.items()]
    countries = {}
    for root in (VANILLA, *DEPENDENCIES, MOD):
        for p in sorted((root / "history/countries").glob("*.txt")):
            if re.match(r"[A-Z0-9]{3}\s*-", p.name):
                countries[p.name[:3]] = at_opening(read_tree(p))
    return provinces, countries

class StartupWorld(ButtonWorld):
    def __init__(self, full_history=False):
        super().__init__()
        self.global_flags.clear()
        self.targets = {"EmperorOfChina": self.countries["CZH"]}
        for c in self.countries.values():
            c.flags.clear()
            c.variables.clear()
        if full_history:
            provinces, histories = opening_histories()
            prototype = self.countries["YAN"]
            tags = set(histories) | {p.get("owner") for _, p in provinces if p.get("owner")}
            self.countries = {tag: deepcopy(prototype) for tag in tags}
            for tag, c in self.countries.items():
                c.tag, c.live, c.ai = tag, False, True
                history = histories.get(tag, [])
                c.government = dict(history).get("government", "monarchy")
                c.government_rank = int(dict(history).get("government_rank", 1))
                for key, value in history:
                    if key == "add_government_reform":
                        c.reforms.add(value)
                    elif key == "remove_government_reform":
                        c.reforms.discard(value)
            for pid, data in provinces:
                owner = data.get("owner")
                if not owner:
                    continue
                self.countries[owner].live = True
                p = self.province(owner, member=False,
                                  hre=data.get("hre", "no") == "yes",
                                  development=sum(int(data.get(k, 0)) for k in ("base_tax", "base_production", "base_manpower")))
                p.id = pid
            self.targets = {"EmperorOfChina": self.countries["CZH"]}
        self.actor("CZH")
        self.initializer = next(dict(v) for k, v in entries(MOD / "events/zhx_system_events.txt")
                                if k == "country_event" and dict(v)["id"] == "zhx_system.1")

    def start(self):
        if self.evaluate(self.initializer["trigger"], [self.root]):
            self.execute(self.initializer["immediate"], [self.root])

    def effect(self, name):
        self.execute(self.effects[name], [self.root])

class StartupLifecycle(unittest.TestCase):
    def test_all_effect_and_trigger_names_are_unique(self):
        for folder in ("scripted_effects", "scripted_triggers"):
            LazyDefinitions(MOD / "common" / folder)

    def test_blank_opening_registers_every_member_owned_province(self):
        w = StartupWorld(full_history=True)
        w.start()
        source = (MOD / "common/scripted_triggers/zhx_diplomacy_triggers.txt").read_text(encoding="utf-8-sig")
        historical = named_block(source, "zhx_is_historic_tianxia_tag")
        expected = set(re.findall(r"tag\s*=\s*([A-Z0-9]{3})", historical)) | {"CZH"}
        member_land = [p for p in w.provinces if p.owner in expected]
        self.assertGreater(len(member_land), len(expected))
        self.assertFalse([p.id for p in member_land if p.hre], "opening member history unexpectedly belongs to HRE")
        self.assertFalse([p.id for p in member_land if TERRITORY not in p.flags])
        self.assertTrue(all(REWARD in p.flags for p in member_land))
        self.assertFalse([p.id for p in w.provinces if p.owner not in expected and TERRITORY in p.flags])
        self.assertEqual(w.root.mandate, 50)
        self.assertEqual(w.root.variables["zhx_merit_term_years_remaining"], 25)
        majors = [c for c in w.countries.values() if "zhx_major_feudatory" in c.flags]
        self.assertEqual(len(majors), 7)
        self.assertEqual(w.countries["YAN"].power_projection["zhx_merit_dignity_power_projection"], 20)
        self.assertTrue(all(c.power_projection["zhx_merit_dignity_power_projection"] == 10 for c in majors if c.tag != "YAN"))
        before = deepcopy((w.root.variables, [c.power_projection for c in majors], [p.flags for p in member_land]))
        w.start()
        self.assertEqual(before, (w.root.variables, [c.power_projection for c in majors], [p.flags for p in member_land]))
        print(f"Opening history: {len(member_land)} provinces; {len({p.owner for p in member_land})} Zhou polities; 7 dignities")

    def test_v13_runs_both_territory_and_merit_initialisation(self):
        w = StartupWorld()
        w.countries["YAN"].flags.update(zhx_member=0, zhx_major_feudatory=0)
        w.targets["gdd_principal_vassal"] = w.countries["YAN"]
        p = w.province(member=False, state_cores=set(), controller="KRC")
        w.effect("zhx_migrate_tianxia_system_v12_to_v13")
        self.assertIn(TERRITORY, p.flags)
        self.assertIn(REWARD, p.flags)
        self.assertEqual(w.countries["YAN"].power_projection["zhx_merit_dignity_power_projection"], 20)
        w.effect("zhx_migrate_tianxia_system_v12_to_v13")
        self.assertEqual(w.countries["YAN"].power_projection["zhx_merit_dignity_power_projection"], 20)

    def test_v14_initializes_diplomacy_and_repairs_hre_overlap(self):
        w = StartupWorld()
        p = w.province(hre=True)
        w.root.flags["zhx_diplomacy_illegal_cession_queued"] = 0
        w.effect("zhx_migrate_tianxia_system_v13_to_v14")
        self.assertFalse(p.hre)
        self.assertIn(TERRITORY, p.flags)
        self.assertNotIn("zhx_diplomacy_illegal_cession_queued", w.root.flags)
        self.assertIn("zhx_diplomacy_initialised", w.global_flags)

    def test_legacy_missing_land_is_repaired_without_resetting_merit_or_queues(self):
        w = StartupWorld()
        w.global_flags.update(f"zhx_system_initialised_v{i}" for i in range(3, 16))
        w.countries["YAN"].flags["zhx_member"] = 0
        w.root.variables.update(zhx_merit_term_year=Decimal(7), zhx_merit_term_years_remaining=Decimal(18),
                                zhx_tianxia_extinction_penalty_count=Decimal(2))
        w.countries["YAN"].variables["zhx_merit_term"] = Decimal(81)
        w.root.flags["zhx_diplomacy_illegal_cession_queued"] = 0
        p = w.province(member=False)
        w.effect("zhx_migrate_tianxia_system_v15_to_v16")
        self.assertIn(TERRITORY, p.flags)
        self.assertEqual(w.root.variables["zhx_merit_term_years_remaining"], 18)
        self.assertEqual(w.countries["YAN"].variables["zhx_merit_term"], 81)
        self.assertEqual(w.root.variables["zhx_tianxia_extinction_penalty_count"], 2)
        self.assertIn("zhx_diplomacy_illegal_cession_queued", w.root.flags)

    def test_legacy_admission_ledger_prevents_readmission_of_removed_land(self):
        w = StartupWorld()
        w.countries["YAN"].flags["zhx_member"] = 0
        p = w.province(member=False, flags={REWARD: 0})
        q = w.province(member=False)
        w.effect("zhx_migrate_tianxia_system_v15_to_v16")
        self.assertNotIn(TERRITORY, p.flags)
        self.assertNotIn(TERRITORY, q.flags)

    def test_dismantled_world_cannot_be_bootstrapped_or_migrated(self):
        w = StartupWorld()
        w.global_flags.add("zhx_tianxia_dismantled")
        p = w.province(member=False)
        for effect in ("gdd_bootstrap_tianxia_provinces_effect", "zhx_initialise_merit_store_effect",
                       "zhx_initialise_diplomacy_effect", "zhx_migrate_tianxia_system_v15_to_v16"):
            w.effect(effect)
        w.start()
        self.assertNotIn(TERRITORY, p.flags)
        self.assertEqual(w.global_flags, {"zhx_tianxia_dismantled"})

    def test_external_annexation_charges_current_emperor_after_transfer(self):
        w = ButtonWorld()
        w.emperor = "LUU"
        w.targets["EmperorOfChina"] = w.countries["LUU"]
        w.actor("KRC")
        w.recipient = w.countries["YAN"]
        w.root.enemies.add("YAN")
        w.execute(w.effects["gdd_apply_external_tianxia_annexation_mandate_loss_effect"], [w.root])
        self.assertEqual(w.countries["LUU"].mandate, 50)
        self.assertEqual(w.countries["LUU"].variables["zhx_external_extinction_mandate_queued"], 10)
        self.assertEqual(w.countries["CZH"].mandate, 50)

    def test_dismantling_removes_new_dignity_and_petition_state(self):
        w = ButtonWorld()
        w.ready_to_dismantle()
        c = w.countries["YAN"]
        c.power_projection["zhx_merit_dignity_power_projection"] = Decimal(20)
        c.reforms.update({"zhx_feudatory_gong_reform", "unrelated_upper_reform"})
        c.flags.update(zhx_feudatory_request_pending=0, zhx_feudatory_request_from_hou=0)
        w.targets.update(gdd_principal_vassal=c, zhx_feudatory_applicant=c,
                         zhx_feudatory_host=w.countries["CZH"], zhx_merit_rank_01=c)
        w.choose("gdd_tianxia_territory.4")
        self.assertEqual(c.power_projection["zhx_merit_dignity_power_projection"], 0)
        self.assertEqual(c.reforms, {"feudalism_reform", "unrelated_upper_reform"})
        self.assertNotIn("zhx_feudatory_request_pending", c.flags)
        for name in ("gdd_principal_vassal", "zhx_feudatory_applicant", "zhx_feudatory_host", "zhx_merit_rank_01"):
            self.assertNotIn(name, w.targets)

if __name__ == "__main__":
    unittest.main(verbosity=2)

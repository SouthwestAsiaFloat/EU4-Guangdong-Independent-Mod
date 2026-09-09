"""Offline scope regressions against the actual Tianxia trigger/resolver scripts.

This intentionally small interpreter rejects unsupported commands. It verifies
the scenarios and ROOT/FROM/PREV wiring, not EU4's engine or diplomatic UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import unittest


MOD = Path(__file__).resolve().parents[1] / "guangdong_independent_practice"


def parse(text):
    tokens = iter(re.findall(r'"[^"\\]*(?:\\.[^"\\]*)*"|[={} ]|[^\s={}]+',
                            re.sub(r"#[^\n]*", "", text)))
    tokens = iter(t for t in tokens if t.strip())

    def block(nested=False):
        result = []
        for key in tokens:
            if key == "}":
                assert nested
                return result
            assert next(tokens) == "=", key
            value = next(tokens)
            result.append((key.strip('"'), block(True) if value == "{" else value.strip('"')))
        assert not nested
        return result

    return dict(block())


@dataclass
class Country:
    tag: str
    live: bool = True
    flags: dict = field(default_factory=dict)
    overlord: str | None = None
    enemies: set = field(default_factory=set)


@dataclass
class Province:
    owner: str
    cores: set
    previous_owner: str = "YAN"
    flags: dict = field(default_factory=lambda: {"zhx_tianxia_province": 0})


class Scripts:
    def __init__(self):
        self.triggers = {}
        for name in ("gdd_tianxia_territory_triggers.txt", "zhx_system_triggers.txt"):
            self.triggers.update(parse((MOD / "common/scripted_triggers" / name).read_text(encoding="utf-8-sig")))
        self.effects = parse((MOD / "common/scripted_effects/gdd_tianxia_territory_effects.txt").read_text(encoding="utf-8-sig"))
        self.countries = {tag: Country(tag) for tag in ("CZH", "YAN", "KRC", "KHA", "OIR", "OTH", "LUU", "ZZZ")}
        self.countries["CZH"].flags["zhx_tianzi"] = 0
        self.countries["YAN"].flags["zhx_member"] = 0
        self.provinces = [Province("KRC", {"YAN"}), Province("KHA", {"YAN"})]
        self.global_flags = set()
        self.targets = {"EmperorOfChina": self.countries["CZH"],
                        "gdd_tianxia_unlawful_emperor": self.countries["CZH"]}
        self.root = self.countries["CZH"]
        self.recipient = self.countries["KRC"]
        self.day = 364

    def ref(self, key, stack):
        if key == "ROOT":
            return self.root
        if key == "FROM":
            return self.recipient
        if key == "PREV":
            return stack[-2]
        if key == "THIS":
            return stack[-1]
        if key.startswith("event_target:"):
            return self.targets.get(key.split(":", 1)[1])
        if key == "overlord":
            return self.countries.get(stack[-1].overlord)
        return self.countries.get(key)

    def iterator(self, key, current):
        if key.endswith("core_country"):
            return [c for tag, c in self.countries.items() if tag in current.cores]
        if key.endswith("owned_province"):
            return [p for p in self.provinces if p.owner == current.tag]
        if key.endswith("subject_country"):
            return [c for c in self.countries.values() if c.overlord == current.tag and c.live]
        if key in ("any_country", "every_country"):
            return [c for c in self.countries.values() if c.live]
        raise AssertionError(f"unsupported iterator {key}")

    def test(self, name, scope, **params):
        return self.evaluate(self.triggers[name], [self.root, scope], params)

    def evaluate(self, entries, stack, params=None):
        params = params or {}
        current = stack[-1]

        def entry(key, value):
            key = params.get(key.strip("$"), key) if key.startswith("$") else key
            if isinstance(value, str) and value.startswith("$"):
                value = params[value.strip("$")]
            if key in ("AND", "NOT", "OR"):
                values = (entry(k, v) for k, v in value)
                return any(values) if key == "OR" else not any(values) if key == "NOT" else all(values)
            if key in self.triggers:
                arguments = {k: params.get(v.strip("$"), v) if v.startswith("$") else v for k, v in value} if isinstance(value, list) else {}
                return self.evaluate(self.triggers[key], stack, arguments)
            if key.startswith("any_"):
                return any(self.evaluate(value, stack + [obj], params) for obj in self.iterator(key, current))
            if isinstance(value, list) and key != "had_country_flag":
                obj = self.ref(key, stack)
                if obj is None:
                    if key == "overlord" or key.startswith("event_target:"):
                        return False
                    raise AssertionError(f"unsupported or unavailable scope {key}")
                return self.evaluate(value, stack + [obj], params)
            if key == "has_global_flag":
                return value in self.global_flags
            if key in ("has_country_flag", "has_province_flag"):
                return value in current.flags
            if key == "had_country_flag":
                data = dict(value)
                return data["flag"] in current.flags and self.day - current.flags[data["flag"]] >= int(data["days"])
            if key == "exists":
                return current.live == (value == "yes")
            if key == "tag":
                return current is self.ref(value, stack)
            if key == "is_emperor_of_china":
                return (current.tag == "CZH") == (value == "yes")
            if key == "is_subject":
                return bool(current.overlord) == (value == "yes")
            if key == "is_subject_of":
                return current.overlord == self.ref(value, stack).tag
            if key == "war_with":
                return self.ref(value, stack).tag in current.enemies
            if key == "owned_by":
                return current.owner == self.ref(value, stack).tag
            if key == "is_core":
                return self.ref(value, stack).tag in current.cores
            if key == "previous_owner":
                return current.previous_owner == self.ref(value, stack).tag
            raise AssertionError(f"unsupported trigger {key}")

        return all(entry(key, value) for key, value in entries)

    def execute(self, entries, stack):
        current = stack[-1]
        for key, value in entries:
            if key in self.effects:
                self.execute(self.effects[key], stack)
            elif key == "every_core_country":
                limit = next((v for k, v in value if k == "limit"), [])
                body = [(k, v) for k, v in value if k != "limit"]
                for obj in self.iterator(key, current):
                    if self.evaluate(limit, stack + [obj]):
                        self.execute(body, stack + [obj])
            elif key == "set_country_flag":
                current.flags[value] = self.day
            elif key == "clr_country_flag":
                current.flags.pop(value, None)
            elif key == "save_event_target_as":
                self.targets[value] = current
            elif key.startswith("event_target:"):
                self.execute(value, stack + [self.ref(key, stack)])
            else:
                raise AssertionError(f"unsupported resolver effect {key}")

    def resolve(self, province):
        self.targets["gdd_tianxia_unlawful_province"] = province
        self.execute(self.effects["gdd_select_lawful_tianxia_returnee_effect"], [self.root])
        if "gdd_tianxia_unlawful_returnee_selected" in self.root.flags:
            return self.targets["gdd_tianxia_unlawful_returnee"].tag
        return None


class TerritoryRules(unittest.TestCase):
    def setUp(self):
        self.s = Scripts()

    def allowed(self, tag):
        self.s.recipient = self.s.countries[tag]
        return self.s.test("gdd_can_be_tianxia_unlawful_addressee_trigger", self.s.recipient, emperor="ROOT")

    def test_korchin_cooldown_does_not_block_mongolia(self):
        self.s.countries["KRC"].flags["gdd_tianxia_unlawful_demand_cooldown"] = 0
        self.assertFalse(self.allowed("KRC"))
        self.assertTrue(self.allowed("KHA"))

    def test_mongolia_subject_must_be_addressed_via_oirat(self):
        self.s.countries["KHA"].overlord = "OIR"
        self.assertFalse(self.allowed("KHA"))
        self.assertTrue(self.allowed("OIR"))

    def test_subjects_and_overlord_do_not_share_cooldown(self):
        for tag in ("KHA", "KRC"):
            self.s.countries[tag].overlord = "OIR"
        for tag in ("KRC", "OIR"):
            self.s.countries[tag].flags["gdd_tianxia_unlawful_demand_cooldown"] = 0
        self.assertTrue(self.allowed("OIR"))
        self.s.countries["KHA"].flags["gdd_tianxia_unlawful_demand_cooldown"] = 0
        self.assertFalse(self.allowed("OIR"))

    def test_same_province_becomes_eligible_at_365_days(self):
        self.s.countries["KRC"].flags["gdd_tianxia_unlawful_demand_cooldown"] = 0
        self.s.provinces[0].flags["gdd_tianxia_unlawful_requested_this_owner"] = 0
        self.assertFalse(self.allowed("KRC"))
        self.s.day = 365
        self.assertTrue(self.allowed("KRC"))

    def test_member_and_outsider_cores_both_exempt(self):
        self.s.provinces[0].cores.add("KRC")
        self.assertFalse(self.allowed("KRC"))
        self.s.countries["KRC"].flags["zhx_member"] = 0
        self.assertFalse(self.allowed("KRC"))

    def test_third_party_war_is_allowed_but_emperor_war_is_not(self):
        self.s.countries["KRC"].enemies.add("OTH")
        self.s.root.enemies.add("OTH")
        self.assertTrue(self.allowed("KRC"))
        self.s.countries["KRC"].enemies.add("CZH")
        self.assertFalse(self.allowed("KRC"))

    def test_pending_is_local_to_recipient(self):
        self.s.countries["KRC"].flags["gdd_tianxia_unlawful_request_pending"] = 0
        self.assertFalse(self.allowed("KRC"))
        self.assertTrue(self.allowed("KHA"))

    def test_no_lawful_core_means_no_emperor_fallback(self):
        p = self.s.provinces[0]
        p.cores = {"OTH"}
        self.assertFalse(self.allowed("KRC"))
        self.assertIsNone(self.s.resolve(p))
        p.cores.add("CZH")
        self.assertTrue(self.allowed("KRC"))
        self.assertEqual(self.s.resolve(p), "CZH")

    def test_extinct_previous_owner_preferred_to_living_core(self):
        p = self.s.provinces[0]
        p.cores = {"CZH", "YAN"}
        self.s.countries["YAN"].live = False
        self.s.countries["YAN"].flags.clear()
        self.assertTrue(self.allowed("KRC"))
        self.assertEqual(self.s.resolve(p), "YAN")

    def test_future_member_can_be_restored_but_dead_foreigner_cannot(self):
        p = self.s.provinces[0]
        p.cores = {"ZZZ"}
        self.s.countries["ZZZ"].live = False
        self.assertFalse(self.allowed("KRC"))
        self.s.countries["ZZZ"].flags["gdd_tianxia_historical_polity"] = 0
        self.assertTrue(self.allowed("KRC"))
        self.assertEqual(self.s.resolve(p), "ZZZ")

    def test_living_former_member_is_not_a_lawful_returnee(self):
        self.s.countries["YAN"].flags = {"gdd_tianxia_historical_polity": 0}
        self.assertFalse(self.allowed("KRC"))

    def test_queued_request_is_invalid_after_core_completion(self):
        p = self.s.provinces[0]
        p.flags["gdd_tianxia_unlawful_request_pending"] = 0
        self.s.targets["holder"] = self.s.countries["KRC"]
        name = "gdd_tianxia_unlawful_request_still_valid_trigger"
        self.assertTrue(self.s.test(name, p, owner="event_target:holder"))
        p.cores.add("KRC")
        self.assertFalse(self.s.test(name, p, owner="event_target:holder"))

    def test_resolver_does_not_reuse_last_request_recipient(self):
        self.assertEqual(self.s.resolve(self.s.provinces[0]), "YAN")
        self.s.provinces[1].cores = {"OTH"}
        self.assertIsNone(self.s.resolve(self.s.provinces[1]))

    def test_queued_request_is_invalid_after_transfer_or_loss_of_returnee(self):
        p = self.s.provinces[0]
        p.flags["gdd_tianxia_unlawful_request_pending"] = 0
        self.s.targets["holder"] = self.s.countries["KRC"]
        name = "gdd_tianxia_unlawful_request_still_valid_trigger"
        self.assertTrue(self.s.test(name, p, owner="event_target:holder"))
        p.owner = "KHA"
        self.assertFalse(self.s.test(name, p, owner="event_target:holder"))
        p.owner = "KRC"
        p.cores = {"OTH"}
        self.assertFalse(self.s.test(name, p, owner="event_target:holder"))

    def test_queued_request_is_invalid_after_war_or_loss_of_emperor(self):
        p = self.s.provinces[0]
        p.flags["gdd_tianxia_unlawful_request_pending"] = 0
        self.s.targets["holder"] = self.s.countries["KRC"]
        name = "gdd_tianxia_unlawful_request_still_valid_trigger"
        self.assertTrue(self.s.test(name, p, owner="event_target:holder"))
        self.s.root.enemies.add("KRC")
        self.assertFalse(self.s.test(name, p, owner="event_target:holder"))
        self.s.root.enemies.clear()
        self.s.targets["gdd_tianxia_unlawful_emperor"] = self.s.countries["YAN"]
        self.assertFalse(self.s.test(name, p, owner="event_target:holder"))


if __name__ == "__main__":
    unittest.main(verbosity=2)

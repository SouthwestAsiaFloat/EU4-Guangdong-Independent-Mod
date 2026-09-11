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
    modifiers: set = field(default_factory=set)
    variables: dict = field(default_factory=dict)


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
        self.effects.update(parse((MOD / "common/scripted_effects/gdd_tianxia_picker_effects.txt").read_text()))
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
        self.events = []

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
        if key == "capital_scope":
            return next((p for p in self.provinces if p.owner == stack[-1].tag), None)
        if key == "owner":
            return self.countries[stack[-1].owner]
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
            if key in ("check_variable", "is_variable_equal"):
                which = [v for k, v in value if k == "which"]
                actual = current.variables.get(which[0], 0)
                expected = current.variables.get(which[1], 0) if len(which) == 2 else float(dict(value)["value"])
                return actual >= expected if key == "check_variable" else actual == expected
            if isinstance(value, list) and key != "had_country_flag":
                obj = self.ref(key, stack)
                if obj is None:
                    if key in ("overlord", "capital_scope") or key.startswith("event_target:"):
                        return False
                    raise AssertionError(f"unsupported or unavailable scope {key}")
                return self.evaluate(value, stack + [obj], params)
            if key == "has_global_flag":
                return value in self.global_flags
            if key == "has_country_modifier":
                return value in current.modifiers
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
            elif key == "if":
                limit = next((v for k, v in value if k == "limit"), [])
                if self.evaluate(limit, stack):
                    self.execute([(k, v) for k, v in value if k != "limit"], stack)
            elif key in ("set_variable", "change_variable", "subtract_variable"):
                data = dict(value)
                amount = float(data["value"])
                name = data["which"]
                current.variables[name] = amount if key == "set_variable" else current.variables.get(name, 0) + (amount if key == "change_variable" else -amount)
            elif key.startswith("every_"):
                limit = next((v for k, v in value if k == "limit"), [])
                body = [(k, v) for k, v in value if k != "limit"]
                for obj in self.iterator(key, current):
                    if self.evaluate(limit, stack + [obj]):
                        self.execute(body, stack + [obj])
            elif key == "country_event":
                self.events.append((dict(value)["id"], current, self.targets.copy()))
            elif key == "set_country_flag":
                current.flags[value] = self.day
            elif key == "clr_country_flag":
                current.flags.pop(value, None)
            elif key == "save_event_target_as":
                self.targets[value] = current
            elif key.startswith("event_target:") or key in ("ROOT", "PREV", "FROM", "capital_scope", "owner"):
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
        for tag in ("KRC", "KHA", "OIR"):
            self.s.countries[tag].flags["zhx_member"] = 0
        self.s.targets["gdd_tianxia_unlawful_addressee"] = self.s.countries["KRC"]

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

    def test_foreign_holder_cannot_be_asked(self):
        self.s.countries["KRC"].flags.clear()
        self.assertFalse(self.allowed("KRC"))

    def test_foreign_overlord_blocks_member_subject(self):
        self.s.countries["KHA"].overlord = "OTH"
        self.assertFalse(self.allowed("KHA"))
        self.assertFalse(self.allowed("OTH"))

    def test_tianzi_own_subject_is_direct_addressee(self):
        self.s.countries["KHA"].overlord = "CZH"
        self.assertTrue(self.allowed("KHA"))

    def test_forfeited_or_barred_dead_tag_cannot_be_restored(self):
        c = self.s.countries["YAN"]
        c.live = False
        c.modifiers.add("zhx_tianxia_rejoin_bar")
        self.assertFalse(self.allowed("KRC"))
        c.modifiers.clear()
        c.flags["zhx_feudatory_forfeited"] = 0
        self.assertFalse(self.allowed("KRC"))

    def test_liberation_and_unregistered_land_are_exempt(self):
        p = self.s.provinces[0]
        p.flags["gdd_tianxia_liberated_this_owner"] = 0
        self.assertFalse(self.allowed("KRC"))
        p.flags.clear()
        self.assertFalse(self.allowed("KRC"))

    def test_mandate_transfer_does_not_transfer_jurisdiction(self):
        self.s.targets["EmperorOfChina"] = self.s.countries["OTH"]
        self.assertTrue(self.allowed("KRC"))
        del self.s.targets["EmperorOfChina"]
        self.assertTrue(self.allowed("KRC"))

    def test_request_invalid_after_overlord_becomes_foreign(self):
        self.s.countries["KRC"].overlord = "OTH"
        p = self.s.provinces[0]
        p.flags["gdd_tianxia_unlawful_request_pending"] = 0
        self.assertFalse(self.s.test("gdd_tianxia_unlawful_request_still_valid_trigger", p, owner="KRC"))


class ManualPickerRules(unittest.TestCase):
    def setUp(self):
        self.s = Scripts()
        for tag in ("KRC", "KHA", "OIR"):
            self.s.countries[tag].flags["zhx_member"] = 0
        self.s.provinces = [Province("CZH", {"CZH"})] + [Province("KRC", {"YAN"}) for _ in range(10)]
        self.s.targets["gdd_tianxia_unlawful_addressee"] = self.s.countries["KRC"]
        self.s.root.flags["gdd_tianxia_picker_open"] = 0

    def page(self, offset):
        self.s.root.variables["gdd_tianxia_picker_offset"] = offset
        self.s.execute(self.s.effects["gdd_build_tianxia_unlawful_picker_page_effect"], [self.s.root])
        return [self.s.targets[f"gdd_tianxia_picker_province_{i}"] for i in range(1, 5)]

    def valid(self, province, holder="KRC"):
        return self.s.test("gdd_tianxia_unlawful_selection_valid_trigger", province, holder=holder)

    def test_diplomatic_entry_opens_picker_once_without_sending(self):
        self.s.root.flags.pop("gdd_tianxia_picker_open")
        action = parse((MOD / "common/new_diplomatic_actions/gdd_tianxia_actions.txt").read_text())["gdd_tianxia_demand_unlawful_territory"]
        self.assertEqual(dict(action)["require_acceptance"], "no")
        callback = dict(action)["on_accept"]
        self.s.execute(callback, [self.s.root])
        self.assertEqual(len(self.s.events), 1)
        event, country, targets = self.s.events[0]
        self.assertEqual(event, "gdd_tianxia_territory.20")
        self.assertIs(country, self.s.root)
        self.assertIs(targets["gdd_tianxia_unlawful_addressee"], self.s.recipient)
        self.s.recipient = self.s.countries["KHA"]
        self.s.execute(callback, [self.s.root])
        self.assertEqual(len(self.s.events), 1)
        for c in self.s.countries.values():
            self.assertNotIn("gdd_tianxia_unlawful_request_pending", c.flags)

    def test_navigation_alternates_events_and_advances_real_page_options(self):
        # Preserve repeated country_event roots in the parser, then execute the
        # actual navigation options. This guards self-reentry without claiming
        # to model EU4's popup scheduler.
        source = (MOD / "events/gdd_tianxia_territory_events.txt").read_text()
        serial = iter(range(1000))
        source = re.sub(r"(?m)^country_event =", lambda _: f"event_{next(serial)} =", source)
        events = {dict(body)["id"]: body for body in parse(source).values() if isinstance(body, list)}
        def navigate(event_id, option_name):
            body = events[event_id]
            option = next(v for k, v in body if k == "option" and dict(v)["name"] == option_name)
            self.assertTrue(self.s.evaluate(dict(option)["trigger"], [self.s.root]))
            self.s.execute(dict(option)["hidden_effect"], [self.s.root])
            next_id = self.s.events[-1][0]
            self.assertNotEqual(next_id, event_id, "Page option must not reopen its still-active event")
            self.assertIn(next_id, events)
            immediate = dict(dict(events[next_id])["immediate"])["hidden_effect"]
            self.s.execute(immediate, [self.s.root])
            return next_id

        self.page(0)
        event = "gdd_tianxia_territory.20"
        for offset in (4, 8):
            event = navigate(event, "gdd_tianxia_picker_next")
            self.assertEqual(self.s.root.variables["gdd_tianxia_picker_offset"], offset)
            self.assertIs(self.s.targets["gdd_tianxia_picker_province_1"], self.s.provinces[offset + 1])
        for offset in (4, 0):
            event = navigate(event, "gdd_tianxia_picker_previous")
            self.assertEqual(self.s.root.variables["gdd_tianxia_picker_offset"], offset)
            self.assertIs(self.s.targets["gdd_tianxia_picker_province_1"], self.s.provinces[offset + 1])

    def test_pages_cover_all_provinces_and_clear_stale_slots(self):
        first = self.page(0)
        self.assertEqual([id(p) for p in first], [id(p) for p in self.s.provinces[1:5]])
        self.assertIn("gdd_tianxia_picker_has_next", self.s.root.flags)
        self.assertEqual([id(p) for p in self.page(4)], [id(p) for p in self.s.provinces[5:9]])
        last = self.page(8)
        self.assertEqual([id(p) for p in last[:2]], [id(p) for p in self.s.provinces[9:]])
        self.assertIs(last[2], self.s.provinces[0])
        self.assertFalse(self.valid(last[2], "CZH"))
        self.assertNotIn("gdd_tianxia_picker_has_next", self.s.root.flags)
        self.assertEqual([id(p) for p in self.page(0)], [id(p) for p in first])

    def test_cancel_and_browsing_never_start_demand_cooldown(self):
        self.page(0)
        self.s.execute(self.s.effects["gdd_close_tianxia_unlawful_picker_effect"], [self.s.root])
        self.assertNotIn("gdd_tianxia_picker_open", self.s.root.flags)
        self.assertEqual(self.s.root.variables["gdd_tianxia_picker_offset"], 0)
        for c in self.s.countries.values():
            self.assertNotIn("gdd_tianxia_unlawful_demand_cooldown", c.flags)
            self.assertNotIn("gdd_tianxia_unlawful_request_pending", c.flags)

    def test_selected_owner_is_frozen_and_core_completion_invalidates(self):
        selected = self.page(0)[2]
        self.assertTrue(self.valid(selected))
        selected.owner = "KHA"
        self.assertFalse(self.valid(selected))
        selected.owner = "KRC"
        selected.cores.add("KRC")
        self.assertFalse(self.valid(selected))
        # The other displayed province stays eligible; do not fall back to it.
        self.assertTrue(self.valid(self.s.targets["gdd_tianxia_picker_province_1"]))

    def test_subjects_are_listed_with_their_actual_owner_and_own_cooldown(self):
        self.s.countries["KRC"].overlord = "OIR"
        self.s.countries["KHA"].overlord = "OIR"
        self.s.targets["gdd_tianxia_unlawful_addressee"] = self.s.countries["OIR"]
        self.s.countries["KRC"].flags["gdd_tianxia_unlawful_demand_cooldown"] = 0
        self.s.provinces.append(Province("KHA", {"YAN"}))
        page = self.page(0)
        self.assertIs(page[0], self.s.provinces[-1])
        self.assertEqual(self.s.targets["gdd_tianxia_picker_owner_1"].tag, "KHA")
        self.assertTrue(self.valid(page[0], "KHA"))
        self.s.countries["KHA"].overlord = "OTH"
        self.assertFalse(self.valid(page[0], "KHA"))

    def test_empty_or_dismantled_page_has_no_valid_slots(self):
        self.s.global_flags.add("zhx_tianxia_dismantled")
        self.assertTrue(all(not self.valid(p, "CZH") for p in self.page(0)))
        self.assertNotIn("gdd_tianxia_picker_has_next", self.s.root.flags)

    def test_confirm_rechecks_selected_holder_cooldown(self):
        selected = self.page(0)[0]
        self.s.countries["KRC"].flags["gdd_tianxia_unlawful_demand_cooldown"] = 0
        self.assertFalse(self.valid(selected))
        self.s.day = 365
        self.assertTrue(self.valid(selected))

    def test_tianzi_direct_subject_does_not_include_nested_subjects(self):
        self.s.countries["KRC"].overlord = "CZH"
        self.s.countries["KHA"].overlord = "KRC"
        self.s.provinces = [self.s.provinces[0], self.s.provinces[1], Province("KHA", {"YAN"})]
        page = self.page(0)
        self.assertIs(page[0], self.s.provinces[1])
        self.assertIs(page[1], self.s.provinces[0])


class RefusalTooltipSafety(unittest.TestCase):
    def test_refusal_cb_is_behind_an_execution_only_event(self):
        effects = Scripts().effects
        events = {dict(body)['id']: body for key, body in parse('file = {\n' +
            (MOD / 'events/gdd_tianxia_territory_events.txt').read_text() + '\n}')['file'] if key == 'country_event'}
        # Model the dangerous description reachability, including hidden_effect
        # and BOTH branches. Event scheduling is an execution boundary.
        def reachable(body, seen=frozenset()):
            for key, value in body:
                yield key
                if key == 'country_event':
                    continue
                if isinstance(value, list):
                    yield from reachable(value, seen)
                elif key in effects and key not in seen:
                    yield from reachable(effects[key], seen | {key})
        for eid in (10, 11, 21):
            for key, body in events[f'gdd_tianxia_territory.{eid}']:
                if key == 'option':
                    self.assertNotIn('add_casus_belli', set(reachable(body)))
        dispatch = effects['gdd_dispatch_tianxia_unlawful_demand_effect']
        # A delayed CB event called below nested else was not queued in the
        # real save. Reject those dispatch branches without banning other else.
        def keys(body):
            for key, value in body:
                yield key
                if isinstance(value, list):
                    yield from keys(value)
        self.assertNotIn('else', set(keys(dispatch)))
        branches = str(dispatch)
        self.assertLess(branches.index('gdd_refuse_tianxia_unlawful_demand_effect'),
                        branches.rindex('gdd_accept_tianxia_unlawful_demand_effect'))
        bridge = dict(events['gdd_tianxia_territory.24'])
        self.assertEqual(bridge['hidden'], 'yes')
        self.assertIn('add_casus_belli', set(reachable(bridge['immediate'])))
        self.assertNotIn('add_casus_belli', set(reachable(bridge['option'])))
        self.assertIn("('target', 'ROOT')", str(bridge['immediate']))
        self.assertIn("('months', '60')", str(bridge['immediate']))



if __name__ == "__main__":
    unittest.main(verbosity=2)

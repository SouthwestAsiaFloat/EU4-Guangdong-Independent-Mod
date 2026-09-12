"""White-box tests of the three Tianxia buttons, using the repository scripts.

Runs a deliberately limited scope interpreter, not EU4. Unknown operations fail
instead of becoming no-ops. Engine rendering, save/load, opinion decay and native
Empire-of-China teardown internals still require an in-game test.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import re
import unittest

from test_gdd_tianxia_territory import MOD, Province, Scripts, parse
from validate_gdd_tianxia_territory import named_block


LEAVE = "gdd_leave_tianxia_button"
ADD = "gdd_add_all_tianxia_provinces_button"
DISMANTLE = "gdd_dismantle_tianxia_button"
TERRITORY = "zhx_tianxia_province"
REWARD = "zhx_tianxia_admission_reward_paid"


def entries(path):
    # Wrapping preserves repeated top-level custom_button/country_event keys.
    return parse("file = {\n" + path.read_text(encoding="utf-8-sig") + "\n}")["file"]


class LazyDefinitions(dict):
    def __init__(self, directory):
        super().__init__()
        self.sources = {}
        for path in sorted(directory.glob("*.txt")):
            raw = path.read_bytes()
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                # Some inherited scripts use legacy-encoded comments; script
                # identifiers/operators remain ASCII. No files are rewritten.
                text = raw.decode("latin-1")
            for match in re.finditer(r"(?m)^(\w+)\s*=\s*\{", text):
                if match[1].startswith(("gdd_", "zhx_")):
                    assert match[1] not in self.sources, f"duplicate definition {match[1]} in {path}"
                # Inherited vanilla may repeat helper definitions; mirror its
                # last-definition resolution, while enforcing authored names.
                self.sources[match[1]] = (text, match.start())

    def __contains__(self, key):
        return key in self.sources

    def __getitem__(self, key):
        if not dict.__contains__(self, key):
            text, start = self.sources[key]
            tail = re.sub(r"#[^\n]*", "", text[start:])
            depth = 0
            for match in re.finditer(r'"(?:\\.|[^"\\])*"|[{}]', tail):
                if match[0] == "{":
                    depth += 1
                elif match[0] == "}":
                    depth -= 1
                    if depth == 0:
                        self[key] = parse(tail[:match.end()])[key]
                        break
        return dict.__getitem__(self, key)


class ButtonWorld(Scripts):
    def __init__(self):
        super().__init__()
        self.effects = LazyDefinitions(MOD / "common/scripted_effects")
        self.triggers = LazyDefinitions(MOD / "common/scripted_triggers")
        self.buttons = {dict(v)["name"]: dict(v) for k, v in entries(
            MOD / "common/custom_gui/gdd_tianxia_territory_gui.txt") if k == "custom_button"}
        self.events = {dict(v)["id"]: v for k, v in entries(
            MOD / "events/gdd_tianxia_territory_events.txt") if k == "country_event"}
        self.opinions = dict(entries(MOD / "common/opinion_modifiers/gdd_celestial_reform_opinions.txt"))
        self.opinions.update(entries(MOD / "common/opinion_modifiers/zhx_diplomacy_opinions.txt"))
        self.decisions = dict(dict(entries(MOD / "decisions/zhx_diplomacy_decisions.txt"))["country_decisions"])
        self.emperor = "CZH"
        self.countries["LUU"].flags["zhx_member"] = 0
        for country in self.countries.values():
            country.variables = {}
            country.modifiers = set()
            country.modifier_durations = {}
            country.reforms = set()
            country.prestige = Decimal(0)
            country.stability = Decimal(0)
            country.war_exhaustion = Decimal(0)
            country.power_projection = {}
            country.government = "monarchy"
            country.government_rank = 1
            country.opinions = {}
            country.ai = False
            country.subject_type = None
            country.capital = None
            country.mandate = Decimal(50)
        self.targets["zhx_tianzi"] = self.countries["CZH"]
        self.countries["CZH"].variables["zhx_member_count_cache"] = Decimal(2)
        self.global_flags = {"zhx_system_initialised_v13"}
        self.provinces = []
        self.queued_events = []
        self.calls = set()
        self.native_teardowns = []
        self.native_reforms = set()
        self.actor("YAN")

    def actor(self, tag):
        self.root = self.recipient = self.countries[tag]

    def province(self, owner="YAN", development=10, member=True, **kwargs):
        p = Province(owner, {owner}, flags={TERRITORY: 0} if member else {})
        p.development = Decimal(development)
        p.controller = owner
        p.state_cores = {owner}
        p.hre = p.trade_company = False
        p.variables = {}
        p.modifiers = set()
        for key, value in kwargs.items():
            setattr(p, key, value)
        self.provinces.append(p)
        return p

    def ref(self, key, stack):
        if key == "capital_scope":
            return stack[-1].capital
        if key == "owner":
            return self.countries[stack[-1].owner]
        return super().ref(key, stack)

    def iterator(self, key, current):
        if key in ("every_province", "any_province"):
            return list(self.provinces)
        return super().iterator(key, current)

    def evaluate(self, body, stack, params=None):
        if params:
            body = self.substitute(body, params)
        current = stack[-1]
        for key, value in body:
            if key == "custom_trigger_tooltip":
                ok = self.evaluate([(k,v) for k,v in value if k != "tooltip"], stack)
            elif key in ("hidden_trigger", "AND", "OR", "NOT"):
                checks = (self.evaluate([(k, v)], stack) for k, v in value)
                ok = any(checks) if key == "OR" else not any(checks) if key == "NOT" else all(checks)
            elif key in ("check_variable", "is_variable_equal"):
                name, amount = self.variable_operands(value, stack)
                actual = current.variables.get(name, Decimal(0))
                ok = actual == amount if key == "is_variable_equal" else actual >= amount
            elif key == "has_saved_global_event_target":
                ok = value in self.targets
            elif key in ("is_at_war", "ai", "is_emperor_of_china", "is_part_of_hre", "is_owned_by_trade_company"):
                actual = {"is_at_war": lambda: bool(current.enemies),
                          "ai": lambda: current.ai,
                          "is_emperor_of_china": lambda: current.tag == self.emperor,
                          "is_part_of_hre": lambda: current.hre,
                          "is_owned_by_trade_company": lambda: current.trade_company}[key]()
                ok = actual == (value == "yes")
            elif key == "is_subject_of_type":
                ok = current.subject_type == value and current.overlord is not None
            elif key == "controlled_by":
                ok = current.controller == self.ref(value, stack).tag
            elif key == "is_state_core":
                ok = self.ref(value, stack).tag in current.state_cores
            elif key in ("has_country_modifier", "has_province_modifier"):
                ok = value in current.modifiers
            elif key == "empire_of_china_reform_passed":
                ok = value in self.native_reforms
            elif key == "has_reform":
                ok = value in current.reforms
            elif key == "government":
                ok = current.government == value
            elif key in ("stability", "prestige", "war_exhaustion"):
                ok = getattr(current, key) >= Decimal(value)
            elif key == "government_rank":
                ok = current.government_rank >= int(value)
            elif key == "always":
                ok = value == "yes"
            else:
                ok = super().evaluate([(key, value)], stack)
            if not ok:
                return False
        return True

    @staticmethod
    def substitute(body, params):
        def replace(v):
            if isinstance(v, list):
                return [(replace(k), replace(x)) for k, x in v]
            return re.sub(r"\$(\w+)\$", lambda m: str(params.get(m[1], m[0])), v)
        return replace(body)

    def variable_operands(self, body, stack):
        which = [v for k, v in body if k == "which"]
        d = dict(body)
        source = self.ref(d["who"], stack) if "who" in d else stack[-1]
        amount = Decimal(d["value"]) if "value" in d else source.variables.get(which[1], Decimal(0))
        return which[0], amount

    def execute(self, body, stack, params=None):
        if params:
            body = self.substitute(body, params)
        current = stack[-1]
        branch_taken = False
        for key, value in body:
            if key in ("if", "else_if", "else"):
                if key == "if":
                    branch_taken = False
                condition = dict(value).get("limit", [])
                if not branch_taken and self.evaluate(condition, stack):
                    branch_taken = True
                    self.execute([(k, v) for k, v in value if k != "limit"], stack)
            elif key == "while":
                condition = dict(value)["limit"]
                iterations = 0
                while self.evaluate(condition, stack):
                    iterations += 1
                    assert iterations <= 2000, "non-terminating script loop"
                    self.execute([(k, v) for k, v in value if k != "limit"], stack)
            elif key in ("hidden_effect",):
                self.execute(value, stack)
            elif key in self.effects:
                self.calls.add(key)
                self.execute(self.effects[key], stack, dict(value) if isinstance(value, list) else None)
            elif key.startswith("every_"):
                condition = dict(value).get("limit", [])
                for obj in self.iterator(key, current):
                    if self.evaluate(condition, stack + [obj]):
                        self.execute([(k, v) for k, v in value if k != "limit"], stack + [obj])
            elif key in ("set_variable", "change_variable", "subtract_variable", "multiply_variable", "divide_variable"):
                name, amount = self.variable_operands(value, stack)
                old = current.variables.get(name, Decimal(0))
                current.variables[name] = {"set_variable": lambda: amount,
                    "change_variable": lambda: old + amount, "subtract_variable": lambda: old - amount,
                    "multiply_variable": lambda: old * amount, "divide_variable": lambda: old / amount}[key]()
            elif key == "export_to_variable":
                d = dict(value)
                source = self.ref(d["who"], stack) if "who" in d else current
                if d["value"] == "development":
                    amount = source.development
                elif d["value"] == "total_development":
                    amount = sum((p.development for p in self.provinces if p.owner == source.tag), Decimal(0))
                else:
                    raise AssertionError(f"unsupported export {d}")
                current.variables[d["which"]] = amount
            elif key in ("set_country_flag", "set_province_flag"):
                current.flags[value] = self.day
            elif key in ("clr_country_flag", "clr_province_flag"):
                current.flags.pop(value, None)
            elif key == "set_global_flag":
                self.global_flags.add(value)
            elif key == "clr_global_flag":
                self.global_flags.discard(value)
            elif key in ("remove_country_modifier", "remove_province_modifier"):
                current.modifiers.discard(value)
                if hasattr(current, "modifier_durations"):
                    current.modifier_durations.pop(value, None)
            elif key in ("add_country_modifier", "add_province_modifier"):
                d = dict(value)
                current.modifiers.add(d["name"])
                if hasattr(current, "modifier_durations"):
                    current.modifier_durations[d["name"]] = int(d["duration"])
            elif key == "add_prestige":
                current.prestige = max(Decimal(-100), min(Decimal(100), current.prestige + Decimal(value)))
            elif key == "add_power_projection":
                d = dict(value)
                current.power_projection[d["type"]] = current.power_projection.get(d["type"], Decimal(0)) + Decimal(d["amount"])
            elif key == "remove_power_projection":
                current.power_projection[dict(value)["type"]] = Decimal(0)
            elif key == "remove_government_reform":
                current.reforms.discard(value)
            elif key == "add_government_reform":
                first_tier = {"feudalism_reform", "zhx_tianzi_reform", "zhx_feudatory_zi_reform", "zhx_feudatory_bo_reform", "zhx_feudatory_hou_reform", "zhx_feudatory_gong_reform"}
                if value in first_tier:
                    current.reforms.difference_update(first_tier)
                current.reforms.add(value)
            elif key == "set_government_rank":
                current.government_rank = int(value)
            elif key == "set_in_empire":
                current.hre = value == "yes"
            elif key == "add_mandate":
                assert current.tag == self.emperor, "Mandate was applied to a non-Emperor"
                current.mandate = max(Decimal(0), min(Decimal(100), current.mandate + Decimal(value)))
            elif key == "add_opinion":
                d = dict(value)
                target = self.ref(d["who"], stack)
                definition = dict(self.opinions[d["modifier"]])
                current.opinions[(target.tag, d["modifier"])] = (Decimal(definition["opinion"]), d.get("years"))
            elif key in ("save_global_event_target_as", "save_event_target_as"):
                self.targets[value] = current
            elif key == "clear_global_event_target":
                self.targets.pop(value, None)
            elif key == "grant_independence":
                current.overlord = current.subject_type = None
            elif key == "dismantle_empire_of_china":
                assert current.tag == self.emperor
                self.native_teardowns.append(current.tag)
                self.emperor = None
            elif key == "country_event":
                self.queued_events.append((current.tag, dict(value)["id"]))
            elif key in ("name", "ai_chance", "custom_tooltip"):
                pass  # Presentation/AI choice metadata; no world-state mutation.
            elif isinstance(value, list):
                obj = self.ref(key, stack)
                if obj is not None:
                    self.execute(value, stack + [obj])
                elif not key.startswith("event_target:"):
                    raise AssertionError(f"unsupported scope/effect {key}")
            else:
                raise AssertionError(f"unsupported effect {key}")

    def visible(self, button):
        return self.evaluate(self.buttons[button]["potential"], [self.root])

    def enabled(self, button):
        return self.visible(button) and self.evaluate(self.buttons[button]["trigger"], [self.root])

    def click(self, button):
        assert self.enabled(button), f"disabled button: {button}"
        self.execute(self.buttons[button]["effect"], [self.root])

    def choose(self, event_id, accept=True):
        options = [v for k, v in self.events[event_id] if k == "option"]
        self.execute(options[0 if accept else 1], [self.root])

    def ready_to_dismantle(self):
        self.actor("KRC")
        self.root.enemies.add("CZH")
        self.countries["YAN"].flags["zhx_major_feudatory"] = 0
        for tag in ("CZH", "YAN"):
            self.countries[tag].capital = self.province(tag, controller="KRC")


class TianxiaButtons(unittest.TestCase):
    def setUp(self):
        self.w = ButtonWorld()

    def test_visibility_requires_initialisation_and_tianzi(self):
        for button in (LEAVE, ADD, DISMANTLE):
            with self.subTest(button=button):
                self.assertTrue(self.w.visible(button))
                self.w.global_flags.clear()
                self.assertFalse(self.w.visible(button))
                self.w.global_flags.add("zhx_system_initialised_v13")
                emperor = self.w.targets.pop("zhx_tianzi")
                self.assertTrue(self.w.visible(button))
                self.w.targets["zhx_tianzi"] = emperor

    def test_leave_eligibility(self):
        for tag, expected in (("YAN", True), ("CZH", False), ("KRC", False)):
            with self.subTest(tag=tag):
                self.w.actor(tag)
                self.assertEqual(self.w.enabled(LEAVE), expected)
        self.w.actor("YAN")
        self.w.root.enemies.add("KRC")
        self.assertFalse(self.w.enabled(LEAVE))

    def test_leave_confirmation_and_cancel_change_nothing(self):
        p = self.w.province()
        before = deepcopy((self.w.root.flags, p.flags, self.w.countries["CZH"].mandate))
        self.w.click(LEAVE)
        self.assertEqual(self.w.queued_events, [("YAN", "gdd_tianxia_territory.3")])
        self.w.choose("gdd_tianxia_territory.3", False)
        self.assertEqual(before, (self.w.root.flags, p.flags, self.w.countries["CZH"].mandate))

    def test_leave_cleans_direct_land_and_membership_with_correct_opinion(self):
        mine = self.w.province(development=30)
        occupied = self.w.province(development=10, controller="KRC")
        foreign = self.w.province(owner="KRC", development=80)
        subject = self.w.province(owner="LUU", development=80)
        self.w.countries["LUU"].overlord = "YAN"
        self.w.root.flags["gdd_support_reform_keju"] = 0
        self.w.root.modifiers.add("zhx_reaffirmed_covenant_modifier")
        self.w.click(LEAVE)
        self.w.choose("gdd_tianxia_territory.3")
        self.assertNotIn(TERRITORY, mine.flags)
        self.assertNotIn(TERRITORY, occupied.flags)
        self.assertIn(TERRITORY, foreign.flags)
        self.assertIn(TERRITORY, subject.flags)
        self.assertNotIn("zhx_member", self.w.root.flags)
        self.assertNotIn("gdd_support_reform_keju", self.w.root.flags)
        self.assertEqual(self.w.root.modifiers, {"zhx_tianxia_rejoin_bar"})
        self.assertEqual(self.w.root.modifier_durations["zhx_tianxia_rejoin_bar"], 7300)
        self.assertEqual(self.w.root.prestige, -25)
        emperor = self.w.countries["CZH"]
        self.assertEqual(emperor.mandate, Decimal(50))
        self.assertEqual(emperor.variables["zhx_member_count_cache"], 1)
        self.assertEqual(emperor.opinions[("YAN", "gdd_opinion_left_tianxia")], (Decimal(-100), "50"))
        self.assertFalse(self.w.root.opinions)

    def test_leave_never_charges_mandate_and_cannot_repeat(self):
        self.w.province(development=180)
        self.w.province(development=70)
        self.w.choose("gdd_tianxia_territory.3")
        self.assertEqual(self.w.countries["CZH"].mandate, Decimal(50))
        self.assertFalse(self.w.enabled(LEAVE))
        self.w.choose("gdd_tianxia_territory.3")
        self.assertEqual(self.w.countries["CZH"].mandate, Decimal(50))

    def test_leave_no_tianxia_land_has_no_mandate_charge(self):
        self.w.province(member=False)
        self.w.choose("gdd_tianxia_territory.3")
        self.assertEqual(self.w.countries["CZH"].mandate, Decimal(50))
        self.assertNotIn("zhx_member", self.w.root.flags)

    def test_leave_confirm_rechecks_war_membership_and_office(self):
        for change in (lambda w: w.root.enemies.add("KRC"),
                       lambda w: w.root.flags.clear(),
                       lambda w: w.root.flags.update(zhx_tianzi=0)):
            with self.subTest(change=change):
                w = ButtonWorld()
                p = w.province()
                w.click(LEAVE)
                change(w)
                w.choose("gdd_tianxia_territory.3")
                self.assertIn(TERRITORY, p.flags)
        self.assertEqual(w.countries["CZH"].mandate, Decimal(50))

    def test_decision_and_button_have_identical_exit_effects(self):
        worlds = [ButtonWorld(), ButtonWorld()]
        for w in worlds:
            w.province(development=32)
            w.root.modifiers.add("zhx_tianxia_covenant_breaker")
        worlds[0].choose("gdd_tianxia_territory.3")
        decision = dict(worlds[1].decisions["zhx_leave_tianxia"])
        self.assertTrue(worlds[1].evaluate(decision["allow"], [worlds[1].root]))
        worlds[1].execute(decision["effect"], [worlds[1].root])
        for tag in worlds[0].countries:
            self.assertEqual(vars(worlds[0].countries[tag]), vars(worlds[1].countries[tag]))
        self.assertEqual(vars(worlds[0].provinces[0]), vars(worlds[1].provinces[0]))
        self.assertIn("zhx_tianxia_covenant_breaker", worlds[1].root.modifiers)

    def test_exit_opinions_do_not_stack_on_emperor(self):
        self.w.choose("gdd_tianxia_territory.3")
        self.assertEqual(self.w.countries["CZH"].opinions,
                         {("YAN", "gdd_opinion_left_tianxia"): (Decimal(-100), "50")})
        self.assertEqual(self.w.countries["LUU"].opinions,
                         {("YAN", "zhx_opinion_left_tianxia_member"): (Decimal(-25), "10")})
        self.assertFalse(self.w.root.opinions)

    def test_exit_opinion_follows_political_tianzi_not_carrier(self):
        self.w.countries["CZH"].flags.pop("zhx_tianzi")
        self.w.countries["LUU"].flags["zhx_tianzi"] = 0
        self.w.targets["zhx_tianzi"] = self.w.countries["LUU"]
        self.w.choose("gdd_tianxia_territory.3")
        self.assertEqual(self.w.countries["LUU"].opinions,
                         {("YAN", "gdd_opinion_left_tianxia"): (Decimal(-100), "50")})

    def test_decision_effect_rechecks_eligibility_and_cannot_charge_twice(self):
        for situation in ("emperor", "war", "already_left"):
            with self.subTest(situation=situation):
                w = ButtonWorld()
                if situation == "emperor":
                    w.actor("CZH")
                elif situation == "war":
                    w.root.enemies.add("KRC")
                else:
                    w.choose("gdd_tianxia_territory.3")
                before = deepcopy(vars(w.root))
                decision = dict(w.decisions["zhx_leave_tianxia"])
                self.assertFalse(w.evaluate(decision["allow"], [w.root]))
                w.execute(decision["effect"], [w.root])
                self.assertEqual(before, vars(w.root))

    def test_exit_cleans_new_dignity_reform_and_projection(self):
        self.w.root.flags["zhx_major_feudatory"] = 0
        self.w.targets["gdd_principal_vassal"] = self.w.root
        self.w.root.power_projection["zhx_merit_dignity_power_projection"] = Decimal(20)
        self.w.root.reforms.update({"zhx_feudatory_gong_reform", "unrelated_upper_reform"})
        self.w.choose("gdd_tianxia_territory.3")
        self.assertEqual(self.w.root.power_projection["zhx_merit_dignity_power_projection"], 0)
        self.assertEqual(self.w.root.reforms, {"feudalism_reform", "unrelated_upper_reform"})
        self.assertNotIn("gdd_principal_vassal", self.w.targets)

    def test_dynamic_principal_is_excluded_from_six_seats_instead_of_yan(self):
        self.w.root.flags["zhx_major_feudatory"] = 0
        self.w.countries["LUU"].flags["zhx_major_feudatory"] = 0
        self.w.targets["gdd_principal_vassal"] = self.w.countries["LUU"]
        self.w.execute(self.w.effects["gdd_build_eoc_great_feudatory_roster"], [self.w.countries["CZH"]])
        seats = [v.tag for k, v in self.w.targets.items() if k.startswith("gdd_eoc_great_feudatory_roster_")]
        self.assertEqual(seats, ["YAN"])

    def test_annexation_hooks_preserve_mandate_and_queue_ritual_once(self):
        source = (MOD / "common/on_actions/zhx_system_on_actions.txt").read_text(encoding="utf-8-sig")
        hooks = {name: parse(named_block(source, name))[name]
                 for name in ("on_diplomatic_annex", "on_integrate", "on_annexed")}
        for hook in ("on_diplomatic_annex", "on_integrate", "on_annexed"):
            for actor in ("KRC", "LUU"):
                with self.subTest(hook=hook, actor=actor):
                    w = ButtonWorld()
                    w.global_flags.add("zhx_system_initialised_v14")
                    w.actor(actor)
                    w.recipient = w.countries["YAN"]
                    w.root.enemies.add("YAN")
                    w.execute(hooks[hook], [w.root])
                    # A second notification must not charge the same extinction.
                    w.execute(hooks[hook], [w.root])
                    self.assertEqual(w.countries["CZH"].mandate, 50)
                    self.assertEqual(w.countries["CZH"].variables.get("zhx_external_extinction_mandate_queued", 0), 0)
                    self.assertEqual(w.countries["CZH"].variables["zhx_tianxia_extinction_penalty_count"], 1)
                    self.assertNotIn("zhx_member", w.recipient.flags)
                    self.assertIn("zhx_tianxia_membership_dirty", w.countries["CZH"].flags)
                    self.assertNotIn("zhx_build_gui_roster", w.calls)
                    self.assertNotIn("zhx_recount_tianxia_council_ballot", w.calls)
                    if hook == "on_annexed":
                        self.assertEqual(w.root.variables["zhx_diplomacy_member_extinction_count"], 1)

    def test_leave_after_voting_recounts_only_remaining_members(self):
        emperor = self.w.countries["CZH"]
        emperor.flags.update(zhx_council_phase_ballot_open=0, zhx_council_kind_ritual_breakdown=0)
        self.w.root.flags["zhx_council_vote_a"] = 0
        self.w.choose("gdd_tianxia_territory.3")
        self.assertNotIn("zhx_council_vote_a", self.w.root.flags)
        self.assertEqual(emperor.variables["zhx_council_vote_a_count"], 0)
        self.assertEqual(emperor.variables["zhx_council_eligible_country_count"], 1)
        self.assertEqual(emperor.variables["zhx_council_unvoted_country_count"], 1)

    def test_leave_before_voting_recounts_only_remaining_members(self):
        emperor = self.w.countries["CZH"]
        emperor.flags.update(zhx_council_phase_ballot_open=0, zhx_council_kind_ritual_breakdown=0)
        self.w.execute(self.w.effects["zhx_recount_tianxia_council_ballot"], [emperor])
        self.assertEqual(emperor.variables["zhx_council_eligible_country_count"], 2)
        self.w.choose("gdd_tianxia_territory.3")
        self.assertEqual(emperor.variables["zhx_council_eligible_country_count"], 1)

    def test_leave_during_debate_recounts_country_and_ai_totals(self):
        for voted in (True, False):
            with self.subTest(voted=voted):
                w = ButtonWorld()
                emperor = w.countries["CZH"]
                emperor.flags.update(zhx_council_phase_ballot_open=0, zhx_council_kind_debate=0)
                w.root.ai = w.countries["LUU"].ai = True
                if voted:
                    w.root.flags["zhx_council_vote_a"] = 0
                w.execute(w.effects["zhx_recount_tianxia_council_ballot"], [emperor])
                self.assertEqual(emperor.variables["zhx_council_eligible_country_count"], 3)
                self.assertEqual(emperor.variables["zhx_council_eligible_ai_count"], 2)
                w.choose("gdd_tianxia_territory.3")
                self.assertEqual(emperor.variables["zhx_council_eligible_country_count"], 2)
                self.assertEqual(emperor.variables["zhx_council_unvoted_country_count"], 2)
                self.assertEqual(emperor.variables["zhx_council_eligible_ai_count"], 1)
                self.assertEqual(emperor.variables["zhx_council_unvoted_ai_count"], 1)
                self.assertEqual(emperor.variables["zhx_council_vote_a_count"], 0)

    def test_leave_without_open_ballot_preserves_closed_results(self):
        emperor = self.w.countries["CZH"]
        emperor.flags.update(zhx_council_kind_debate=0, zhx_council_result_ready=0)
        emperor.variables["zhx_council_vote_a_count"] = Decimal(7)
        self.w.root.flags["zhx_council_vote_a"] = 0
        self.w.choose("gdd_tianxia_territory.3")
        self.assertNotIn("zhx_recount_tianxia_council_ballot", self.w.calls)
        self.assertIn("zhx_council_result_ready", emperor.flags)
        self.assertEqual(emperor.variables["zhx_council_vote_a_count"], 7)

    def test_leave_refreshes_initialized_rosters_and_reform_vote_totals(self):
        self.w.global_flags.update({"zhx_gui_roster_initialised", "gdd_celestial_reform_voting_initialised"})
        self.w.province(development=30)
        self.w.province(owner="LUU", development=12)
        self.w.root.flags.update(zhx_major_feudatory=0, gdd_support_reform_keju=0)
        self.w.countries["LUU"].flags["gdd_support_reform_keju"] = 0
        self.w.choose("gdd_tianxia_territory.3")
        self.assertNotIn("zhx_major_feudatory", self.w.root.flags)
        emperor = self.w.countries["CZH"]
        self.assertEqual(emperor.variables["gdd_reform_vote_total_dev"], 12)
        self.assertEqual(emperor.variables["gdd_reform_vote_keju_dev"], 12)
        rebuilt = [v.tag for k, v in self.w.targets.items() if "roster_" in k]
        self.assertIn("LUU", rebuilt)
        self.assertNotIn("YAN", rebuilt)

    def test_subject_cannot_leave_from_button_or_stale_confirmation(self):
        self.w.root.overlord, self.w.root.subject_type = "CZH", "gdd_tianxia_vassal"
        self.assertFalse(self.w.enabled(LEAVE))
        self.w.choose("gdd_tianxia_territory.3")
        self.assertIn("zhx_member", self.w.root.flags)
        self.assertEqual(self.w.root.overlord, "CZH")

    def test_characterize_leave_retains_reform_executor_bonus(self):
        # Current reforms are explicitly owned by their executor, not the seat.
        self.w.root.flags["gdd_proxy_reform_keju"] = 0
        self.w.choose("gdd_tianxia_territory.3")
        modifiers = dict(entries(MOD / "common/triggered_modifiers/gdd_celestial_proxy_reforms.txt"))
        bonus = dict(modifiers["gdd_proxy_reform_keju_emperor"])
        self.assertTrue(self.w.evaluate(bonus["potential"], [self.w.root]))
        self.assertTrue(self.w.evaluate(bonus["trigger"], [self.w.root]))

    def test_add_eligibility_requires_member_peace_and_candidate(self):
        self.assertFalse(self.w.enabled(ADD))
        self.w.province(member=False)
        self.assertTrue(self.w.enabled(ADD))
        self.w.root.enemies.add("KRC")
        self.assertFalse(self.w.enabled(ADD))
        self.w.root.enemies.clear()
        self.w.root.flags.clear()
        self.assertFalse(self.w.enabled(ADD))

    def test_add_filters_noncores_occupation_hre_trade_company_and_other_owners(self):
        eligible = self.w.province(member=False)
        excluded = [self.w.province(member=False, state_cores=set()),
                    self.w.province(member=False, controller="KRC"),
                    self.w.province(member=False, hre=True),
                    self.w.province(member=False, trade_company=True),
                    self.w.province(owner="LUU", member=False)]
        self.w.countries["LUU"].overlord = "YAN"
        self.w.click(ADD)
        self.assertIn(TERRITORY, eligible.flags)
        for p in excluded:
            self.assertNotIn(TERRITORY, p.flags)
        self.assertEqual(self.w.countries["CZH"].mandate, Decimal(50))
        self.assertFalse(self.w.queued_events)

    def test_add_large_and_small_provinces_never_awards_mandate(self):
        self.w.province(member=False, development=300)
        self.w.province(member=False, development=80)
        self.w.click(ADD)
        self.assertEqual(self.w.countries["CZH"].mandate, Decimal(50))
        self.assertEqual(self.w.root.variables.get("gdd_tianxia_province_mandate_amount", 0), 0)

    def test_add_repeat_and_remove_readd_cannot_farm_reward(self):
        p = self.w.province(member=False, development=20)
        self.w.click(ADD)
        self.assertIn(REWARD, p.flags)
        self.assertFalse(self.w.enabled(ADD))
        p.flags.pop(TERRITORY)
        self.w.click(ADD)
        self.assertIn(TERRITORY, p.flags)
        self.assertEqual(self.w.countries["CZH"].mandate, Decimal(50))

    def test_emperor_can_add_own_land(self):
        self.w.actor("CZH")
        p = self.w.province(owner="CZH", member=False, development=15)
        self.w.click(ADD)
        self.assertIn(TERRITORY, p.flags)
        self.assertEqual(self.w.root.mandate, Decimal(50))

    def test_dismantle_requires_personal_occupation_of_each_living_office(self):
        self.w.ready_to_dismantle()
        self.assertTrue(self.w.enabled(DISMANTLE))
        for tag in ("CZH", "YAN"):
            with self.subTest(tag=tag):
                self.w.countries[tag].capital.controller = "KHA"
                self.assertFalse(self.w.enabled(DISMANTLE))
                self.w.countries[tag].capital.controller = "KRC"
        self.w.countries["YAN"].live = False
        self.w.countries["YAN"].capital.controller = "KHA"
        self.assertTrue(self.w.enabled(DISMANTLE))

    def test_dismantle_requires_war_and_outside_membership(self):
        self.w.ready_to_dismantle()
        self.w.root.enemies.clear()
        self.assertFalse(self.w.enabled(DISMANTLE))
        self.w.root.enemies.add("CZH")
        self.w.root.flags["zhx_member"] = 0
        self.assertFalse(self.w.enabled(DISMANTLE))

    def test_dismantle_checks_tianzi_separately_from_emperor(self):
        self.w.ready_to_dismantle()
        self.w.targets["zhx_tianzi"] = self.w.countries["LUU"]
        self.w.countries["LUU"].capital = self.w.province(owner="LUU")
        self.assertFalse(self.w.enabled(DISMANTLE))
        self.w.countries["LUU"].capital.controller = "KRC"
        self.assertTrue(self.w.enabled(DISMANTLE))

    def test_dismantle_checks_all_seven_dynamic_seats(self):
        self.w.ready_to_dismantle()
        self.w.countries["QIN"] = deepcopy(self.w.countries["LUU"])
        self.w.countries["QIN"].tag = "QIN"
        seven = ("YAN", "LUU", "KHA", "OIR", "OTH", "ZZZ", "QIN")
        for tag in seven:
            c = self.w.countries[tag]
            c.flags.update(zhx_member=0, zhx_major_feudatory=0)
            c.capital = self.w.province(tag, controller="KRC")
        self.assertTrue(self.w.enabled(DISMANTLE))
        for tag in seven:
            with self.subTest(unoccupied_seat=tag):
                self.w.countries[tag].capital.controller = tag
                self.assertFalse(self.w.enabled(DISMANTLE))
                self.w.countries[tag].capital.controller = "KRC"

    def test_dismantle_cannot_restart_initialisation_or_reuse_rosters(self):
        self.w.ready_to_dismantle()
        self.w.targets.update(zhx_roster_01=self.w.countries["YAN"],
                              gdd_eoc_member_roster_01=self.w.countries["YAN"],
                              gdd_eoc_great_feudatory_roster_01=self.w.countries["YAN"],
                              gdd_principal_vassal=self.w.countries["YAN"])
        self.w.choose("gdd_tianxia_territory.4")
        self.assertFalse([k for k in self.w.targets if "roster_" in k or k == "gdd_principal_vassal"])
        self.w.actor("CZH")
        system_events = [dict(v) for k, v in entries(MOD / "events/zhx_system_events.txt") if k == "country_event"]
        initialiser = next(e for e in system_events if e["id"] == "zhx_system.1")
        self.assertFalse(self.w.evaluate(initialiser["trigger"], [self.w.root]))

    def test_dismantle_cancel_and_changed_capital_are_safe(self):
        self.w.ready_to_dismantle()
        self.w.click(DISMANTLE)
        self.assertEqual(self.w.queued_events[-1], ("KRC", "gdd_tianxia_territory.4"))
        self.w.choose("gdd_tianxia_territory.4", False)
        self.assertFalse(self.w.native_teardowns)
        self.w.countries["YAN"].capital.controller = "YAN"
        self.w.choose("gdd_tianxia_territory.4")
        self.assertNotIn("zhx_tianxia_dismantled", self.w.global_flags)
        self.assertFalse(self.w.native_teardowns)

    def test_dismantle_cleans_political_state_and_only_special_subjects(self):
        self.w.ready_to_dismantle()
        self.w.global_flags.update({"gdd_proxy_reform_keju", "gdd_decentralized_tianxia_interface_enabled",
                                    "eoc_vassalize_tributaries", "gdd_celestial_reform_voting_initialised"})
        special, ordinary = self.w.countries["YAN"], self.w.countries["LUU"]
        special.overlord = ordinary.overlord = "CZH"
        special.subject_type, ordinary.subject_type = "gdd_tianxia_vassal", "vassal"
        special.flags.update(gdd_proxy_reform_keju=0, gdd_support_reform_keju=0,
                             zhx_council_vote_a=0, zhx_school_ru=0)
        special.modifiers.update({"gdd_proxy_decree_expand_bureaucracy", "unrelated_school_modifier"})
        p = self.w.provinces[0]
        p.flags.update(gdd_tianxia_unlawful_request_pending=0, zhx_academy_active=0)
        p.modifiers.add("gdd_tianxia_unlawful_refusal")
        self.w.click(DISMANTLE)
        self.w.choose("gdd_tianxia_territory.4")
        self.assertIn("zhx_tianxia_dismantled", self.w.global_flags)
        self.assertNotIn("empire_of_china_dismantled", self.w.global_flags)
        self.assertNotIn("gdd_proxy_reform_keju", self.w.global_flags)
        self.assertIsNone(special.overlord)
        self.assertEqual(ordinary.overlord, "CZH")
        self.assertEqual(self.w.native_teardowns, [])
        self.assertNotIn("zhx_tianzi", self.w.targets)
        for flag in ("zhx_member", "zhx_major_feudatory", "gdd_proxy_reform_keju", "gdd_support_reform_keju", "zhx_council_vote_a"):
            self.assertNotIn(flag, special.flags)
        self.assertIn("zhx_school_ru", special.flags)
        self.assertEqual(special.modifiers, {"unrelated_school_modifier"})
        self.assertNotIn(TERRITORY, p.flags)
        self.assertIn("zhx_academy_active", p.flags)
        self.assertFalse(p.modifiers)
        for button in (LEAVE, ADD, DISMANTLE):
            self.assertFalse(self.w.visible(button))
        self.w.choose("gdd_tianxia_territory.4")
        self.assertEqual(self.w.native_teardowns, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

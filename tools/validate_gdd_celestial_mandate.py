#!/usr/bin/env python3
"""White-box contract checks for the Zhou/HRE-style Mandate system."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"

PATHS = {
    "defines": MOD / "common/defines/zz_gdd_mandate.lua",
    "static": MOD / "common/static_modifiers/zz_gdd_neutral_mandate.txt",
    "triggers": MOD / "common/scripted_triggers/gdd_celestial_mandate_triggers.txt",
    "effects": MOD / "common/scripted_effects/gdd_celestial_mandate_effects.txt",
    "territory_effects": MOD / "common/scripted_effects/gdd_tianxia_territory_effects.txt",
    "territory_triggers": MOD / "common/scripted_triggers/gdd_tianxia_territory_triggers.txt",
    "territory_gui": MOD / "common/custom_gui/gdd_tianxia_territory_gui.txt",
    "territory_events": MOD / "events/gdd_tianxia_territory_events.txt",
    "authority": MOD / "common/scripted_effects/gdd_celestial_authority_effects.txt",
    "proxy": MOD / "common/scripted_effects/gdd_celestial_proxy_effects.txt",
    "vote_effects": MOD / "common/scripted_effects/gdd_celestial_reform_vote_effects.txt",
    "action_triggers": MOD / "common/scripted_triggers/gdd_celestial_action_triggers.txt",
    "membership": MOD / "common/scripted_effects/zhx_system_effects.txt",
    "roster_effects": MOD / "common/scripted_effects/zhx_gui_roster_effects.txt",
    "modifiers": MOD / "common/triggered_modifiers/gdd_celestial_mandate_modifiers.txt",
    "city_modifiers": MOD / "common/triggered_modifiers/00_triggered_modifiers.txt",
    "decree_modifiers": MOD / "common/event_modifiers/gdd_celestial_proxy_decrees.txt",
    "culture_disaster": MOD / "common/disasters/empire_of_china_culture.txt",
    "events": MOD / "events/gdd_celestial_mandate_events.txt",
    "system_events": MOD / "events/zhx_system_events.txt",
    "on_actions": MOD / "common/on_actions/zhx_system_on_actions.txt",
    "opinions": MOD / "common/opinion_modifiers/gdd_celestial_reform_opinions.txt",
    "loc": MOD / "localisation_source/gdd_l_english_readable_utf8.txt",
    "mandate_loc": MOD / "localisation_source/016_gdd_mandate_description_readable_utf8.txt",
    "terminology_loc": MOD / "localisation_source/017_gdd_wangming_terminology_readable_utf8.txt",
    "ui_loc": MOD / "localisation_source/gdd_celestial_ui_readable_utf8.txt",
    "mandate_tooltip": MOD / "customizable_localization/gdd_celestial_mandate_tooltip.txt",
    "member_tooltips": MOD / "customizable_localization/gdd_celestial_member_tooltips.txt",
    "authority_gui": MOD / "common/custom_gui/gdd_celestial_authority_gui.txt",
    "member_gui": MOD / "common/custom_gui/gdd_celestial_vassal_shields.txt",
    "interface": MOD / "interface/celestialempireview.gui",
    "registry": ROOT / "tools/gdd_celestial_mandate_sources.json",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def balanced(path: Path, text: str) -> None:
    depth = 0
    quoted = escaped = comment = False
    for char in text:
        if comment:
            if char == "\n":
                comment = False
            continue
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == "#":
            comment = True
        elif char == '"':
            quoted = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            require(depth >= 0, f"{path.name}: closing brace without opener")
    require(not quoted, f"{path.name}: unterminated quote")
    require(depth == 0, f"{path.name}: unbalanced braces ({depth})")


def block(text: str, name: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text)
    require(match is not None, f"missing block {name}")
    opening = text.find("{", match.start())
    depth = 0
    quoted = escaped = comment = False
    for index in range(opening, len(text)):
        char = text[index]
        if comment:
            if char == "\n":
                comment = False
            continue
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == "#":
            comment = True
        elif char == '"':
            quoted = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[match.start(): index + 1]
    raise SystemExit(f"FAIL: block {name} has no closing brace")


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"(?m)#.*$", "", text)).strip()


def custom_gui_block(text: str, name: str) -> str:
    match = re.search(
        rf"(?ms)^custom_(?:text_box|icon|button) = \{{\n"
        rf"\s+name = {re.escape(name)}\n.*?^\}}$",
        text,
    )
    require(match is not None, f"missing custom GUI block {name}")
    return match.group(0)


def main() -> None:
    texts = {name: path.read_text(encoding="utf-8-sig") for name, path in PATHS.items()}
    for name, path in PATHS.items():
        if path.suffix in {".txt", ".lua", ".gui"} and name not in {
            "loc", "mandate_loc", "terminology_loc", "ui_loc"
        }:
            balanced(path, texts[name])

    defines = texts["defines"]
    for key in (
        "CELESTIAL_EMPIRE_MANDATE_PER_STABILITY",
        "CELESTIAL_EMPIRE_MANDATE_PER_HUNDRED_TRIBUTARY_DEV",
        "CELESTIAL_EMPIRE_MANDATE_PER_HUNDRED_DEVASTATION",
        "CELESTIAL_EMPIRE_MANDATE_PER_5_LOANS",
    ):
        require(re.search(rf"{key}\s*=\s*0(?:\D|$)", defines) is not None,
                f"{key} is not neutralised")

    static = texts["static"]
    require(compact(block(static, "positive_mandate")) == "positive_mandate = { }",
            "positive Mandate still gives country buffs")
    require(compact(block(static, "negative_mandate")) == "negative_mandate = { }",
            "negative Mandate still gives country penalties")
    for name, preserved in (
        ("corruption", ("all_power_cost = 1.0", "min_autonomy = 50")),
        ("bankruptcy", ("interest = 5", "technology_cost = 0.5")),
    ):
        body = block(static, name)
        require("imperial_mandate" not in body, f"{name} still drains Mandate")
        for token in preserved:
            require(token in body, f"{name} override lost vanilla effect: {token}")

    proxy = texts["proxy"]
    enact = block(proxy, "gdd_enact_proxy_celestial_reform_effect")
    require("add_mandate = -100" in enact, "reform does not consume the Mandate pool")
    require("add_stability" not in enact, "reform still costs stability")
    backlash = block(proxy, "gdd_apply_proxy_reform_revoke_backlash_effect")
    require("gdd_celestial_reform_revoker" not in proxy,
            "obsolete non-persistent revoker event target remains")
    require(backlash.count("who = ROOT") == 6,
            "revocation backlash is not five stacks to executor plus one to members")

    triggers = texts["triggers"]
    peace = block(triggers, "gdd_tianxia_has_internal_peace")
    require(peace.count("zhx_is_tianxia_polity = yes") == 2,
            "internal peace does not require two Zhou belligerents")
    require("war_with = PREV" in peace,
            "internal peace does not test an explicit war between both Zhou scopes")
    require("any_enemy_country" not in peace,
            "internal peace still relies on the broader enemy-country scope")
    require("is_at_war" not in peace,
            "foreign wars incorrectly suspend the internal-peace gain")

    effects = texts["effects"]
    refresh = block(effects, "gdd_refresh_tianxia_mandate_effect")
    require("set_country_flag = gdd_tianxia_mandate_cache_ready" in refresh,
            "seat cache is exposed before its first complete scan")
    require("add_mandate" not in refresh,
            "non-mutating startup cache refresh charges a monthly loss")
    monthly = block(effects, "gdd_monthly_tianxia_mandate_effect")
    require("add_mandate = -0.005" in monthly,
            "foreign occupation is not charged per province each month")
    require("gdd_tianxia_defense_refusal_paid" in monthly,
            "defense refusal can repeat every month")
    require("gdd_shift_authority_toward_feudatories_5_effect = yes" in monthly,
            "internal subject status does not move authority monthly")
    authority_shift = block(texts["authority"],
                            "gdd_shift_authority_toward_feudatories_5_effect")
    for token in ("which = gdd_central_authority_balance", "value = -5",
                  "gdd_clamp_central_authority_balance = yes",
                  "gdd_refresh_authority_balance_effects = yes"):
        require(token in authority_shift, f"authority shift missing {token}")
    annex = block(effects, "gdd_apply_external_tianxia_annexation_mandate_loss_effect")
    require("NOT = { zhx_is_tianxia_polity = yes }" in annex,
            "internal annexation incorrectly pays the external penalty")
    require("CZH = { add_mandate = -10 }" in annex,
            "external full annexation is not exactly -10 Mandate")
    leave = block(effects, "gdd_leave_tianxia_with_mandate_penalty_effect")
    for token in ("gdd_can_leave_tianxia_trigger = yes",
                  "gdd_leave_tianxia_territory_effect = yes",
                  "zhx_remove_tianxia_member = yes"):
        require(token in leave, f"voluntary-exit contract missing {token}")
    territory_leave = block(texts["territory_effects"],
                            "gdd_leave_tianxia_territory_effect")
    for token in ("value = 200", "add_mandate = -0.1", "while =",
                  "modifier = gdd_opinion_left_tianxia"):
        require(token in territory_leave,
                f"voluntary-exit territory contract missing {token}")

    add_province = block(texts["territory_effects"],
                         "gdd_add_province_to_tianxia_effect")
    remove_province = block(texts["territory_effects"],
                            "gdd_remove_province_from_tianxia_effect")
    require("zhx_tianxia_admission_reward_paid" in add_province
            and "value = 200" in add_province
            and "add_mandate = 0.1" in add_province,
            "province admission is not first-ever +0.1/development capped at 20")
    require("clr_province_flag = zhx_tianxia_province" in remove_province
            and "clr_province_flag = zhx_tianxia_admission_reward_paid" not in remove_province
            and "value = 200" in remove_province
            and "add_mandate = -0.1" in remove_province,
            "province removal does not preserve the reward ledger or cap its loss at 20")

    territory_triggers = texts["territory_triggers"]
    add_trigger = block(
        territory_triggers,
        "gdd_can_add_province_to_tianxia_for_country_trigger",
    )
    for token in ("is_part_of_hre = no", "owned_by = $who$",
                  "controlled_by = $who$", "is_state_core = $who$",
                  "zhx_is_tianxia_polity = yes", "is_at_war = no"):
        require(token in add_trigger, f"province-admission trigger missing {token}")
    remove_trigger = block(
        territory_triggers,
        "gdd_can_remove_province_from_tianxia_for_country_trigger",
    )
    for token in ("owned_by = $who$", "controlled_by = $who$",
                  "NOT = { zhx_is_tianxia_polity = yes }", "is_at_war = no"):
        require(token in remove_trigger, f"province-removal trigger missing {token}")
    quarterly = block(texts["territory_effects"],
                      "gdd_quarterly_tianxia_territory_maintenance_effect")
    for token in ("is_rival = event_target:EmperorOfChina",
                  "attitude = attitude_hostile", "value = -50",
                  "set_in_empire = no"):
        require(token in quarterly, f"quarterly territory maintenance missing {token}")
    dismantle = block(texts["territory_effects"], "gdd_dismantle_tianxia_effect")
    for token in ("set_global_flag = zhx_tianxia_dismantled",
                  "gdd_disable_centralized_tianxia_interface_effect = yes",
                  "clr_province_flag = zhx_tianxia_province",
                  "zhx_clear_tianxia_debate_petitions = yes",
                  "gdd_clear_all_reform_support_flags_effect = yes",
                  "dismantle_empire_of_china = yes"):
        require(token in dismantle, f"permanent dismantling cleanup missing {token}")
    dismantle_trigger = block(territory_triggers, "gdd_can_dismantle_tianxia_trigger")
    for token in ("NOT = { zhx_is_tianxia_polity = yes }",
                  "NOT = { is_emperor_of_china = yes }", "is_at_war = yes",
                  "capital_scope = { controlled_by = ROOT }",
                  "zhx_is_seven_great_feudatory = yes"):
        require(token in dismantle_trigger,
                f"HRE-style dismantling trigger missing {token}")

    modifiers = texts["modifiers"]
    peace_modifier = block(modifiers, "gdd_tianxia_internal_peace_mandate")
    require("imperial_mandate = 0.10" in peace_modifier,
            "internal peace is not +0.10 Mandate/month")
    require("has_reform = celestial_empire" in peace_modifier
            and peace_modifier.count("is_emperor_of_china = yes") == 1,
            "internal-peace modifier does not use the vanilla-safe potential/trigger split")
    settled_authority = block(modifiers, "gdd_tianxia_settled_authority_mandate")
    absolute_authority = block(modifiers, "gdd_tianxia_absolute_authority_mandate")
    deadlocked_authority = block(modifiers, "gdd_tianxia_deadlocked_authority_mandate")
    require("imperial_mandate = 0.05" in settled_authority,
            "leaning authority is not +0.05 Mandate/month")
    require("imperial_mandate = 0.10" in absolute_authority,
            "absolute authority is not +0.10 Mandate/month")
    require("imperial_mandate = -0.10" in deadlocked_authority,
            "deadlocked authority is not -0.10 Mandate/month")
    for name, authority_modifier in (
        ("settled", settled_authority),
        ("absolute", absolute_authority),
        ("deadlocked", deadlocked_authority),
    ):
        for token in (
            "has_reform = celestial_empire",
            "is_emperor_of_china = yes",
            "has_global_flag = zhx_system_initialised_v8",
            "which = gdd_authority_integer_display",
        ):
            require(token in authority_modifier,
                    f"{name}-authority modifier lacks {token}")
    for token in ("value = -99", "value = -25", "value = 26", "value = 100"):
        require(token in settled_authority,
                f"leaning-authority open intervals lack {token}")
    for token in ("value = -99", "value = 100"):
        require(token in absolute_authority,
                f"absolute-authority endpoints lack {token}")
    for token in ("value = -25", "value = 26"):
        require(token in deadlocked_authority,
                f"deadlocked-authority interval lacks {token}")

    action_triggers = texts["action_triggers"]
    ai_support = block(action_triggers, "gdd_ai_reform_executor_support_trigger")
    require("ai = no" in ai_support and "has_country_flag = $support_flag$" in ai_support,
            "AI reform-executor consent trigger is incomplete")
    reform_slugs = (
        "keju", "civil_registration", "silver_standard", "kanhe",
        "unified_market", "military_branch", "foreign_ship_designs",
        "inclusive_monarchy", "establish_gaituguiliu", "land_tax",
        "single_whip", "centralizing_government", "reign_in_estates",
        "vassalize_tributaries", "seaban", "military_governors",
        "tributary_embassies", "modernize_banners", "bureaucratic_faction",
        "new_world",
    )
    for slug in reform_slugs:
        enact_trigger = compact(block(action_triggers,
                                      f"gdd_can_enact_proxy_{slug}_trigger"))
        consent = (
            "gdd_ai_reform_executor_support_trigger = { "
            f"support_flag = gdd_support_reform_{slug} }}"
        )
        require(consent in enact_trigger,
                f"AI executor can enact unsupported reform: {slug}")
    external_subject = block(modifiers,
                             "gdd_tianxia_emperor_external_subject_mandate")
    internal_subject = block(modifiers,
                             "gdd_tianxia_emperor_internal_subject_mandate")
    require("imperial_mandate = -1" in external_subject
            and "NOT = { zhx_is_tianxia_polity = yes }" in external_subject,
            "external overlord is not exactly -1 Mandate/month")
    require("imperial_mandate = -0.05" in internal_subject
            and "overlord = { zhx_is_tianxia_polity = yes }" in internal_subject,
            "Zhou overlord is not exactly -0.05 Mandate/month")
    require("is_subject_other_than_tributary_trigger = yes" in external_subject
            and "is_subject_other_than_tributary_trigger = yes" in internal_subject,
            "subject penalties do not exclude tributaries")
    tiers = (
        ("one", "-0.05"), ("two", "-0.10"), ("three", "-0.15"),
        ("four", "-0.20"), ("five", "-0.25"), ("six", "-0.30"),
        ("seven", "-0.35"),
    )
    for name, value in tiers:
        tier = block(modifiers, f"gdd_tianxia_{name}_invalid_great_feudator"
                               + ("y" if name == "one" else "ies"))
        require(f"imperial_mandate = {value}" in tier,
                f"{name}-invalid-seat tier has wrong value")
        require("has_country_flag = gdd_tianxia_mandate_cache_ready" in tier,
                f"{name}-invalid-seat tier can fire before cache readiness")
        require("has_reform = celestial_empire" in tier
                and tier.count("is_emperor_of_china = yes") == 1,
                f"{name}-invalid-seat tier does not use the vanilla-safe potential/trigger split")

    roster_effects = texts["roster_effects"]
    roster_build = block(roster_effects, "zhx_build_gui_roster")
    require("gdd_build_eoc_great_feudatory_roster = yes" in roster_build,
            "main GUI roster rebuild does not refresh the six great-feudatory shields")
    great_build = block(roster_effects, "gdd_build_eoc_great_feudatory_roster")
    require("has_country_flag = zhx_major_feudatory" in great_build
            and "NOT = { tag = YAN }" in great_build
            and "set_global_flag = gdd_eoc_great_feudatory_roster_initialised" in great_build,
            "six-seat great-feudatory cache has lost its authoritative membership contract")
    require(roster_effects.count(
        "save_global_event_target_as = gdd_eoc_great_feudatory_roster_"
    ) == 6, "six-seat great-feudatory cache does not allocate exactly six shields")

    events = texts["events"]
    require("gdd_refresh_tianxia_mandate_effect = yes" in events,
            "maintenance event does not call the refresh effect")
    on_actions = texts["on_actions"]
    require(block(on_actions, "on_startup").count("gdd_celestial_mandate.1") == 1,
            "Mandate maintenance is not wired once at startup")
    require(block(on_actions, "on_monthly_pulse").count("gdd_celestial_mandate.2") == 1,
            "Mandate maintenance is not wired once monthly")
    require("gdd_refresh_tianxia_mandate_effect = yes"
            in block(on_actions, "on_mandate_of_heaven_gained"),
            "new Emperor does not receive an immediate valid seat cache")
    require("clr_country_flag = gdd_tianxia_mandate_cache_ready"
            in block(on_actions, "on_mandate_of_heaven_lost"),
            "former Emperor retains a stale seat-cache readiness flag")
    require("gdd_refresh_tianxia_mandate_effect = yes"
            in block(texts["system_events"], "country_event"),
            "system initialization does not refresh seats after migrations")
    for hook in ("on_integrate", "on_annexed"):
        hook_body = block(on_actions, hook)
        require(hook_body.count("gdd_apply_external_tianxia_annexation_mandate_loss_effect") == 1,
                f"{hook} lacks the once-only external annexation penalty")

    membership = texts["membership"]
    registration = block(membership, "zhx_register_tianxia_member")
    require("clr_country_flag = gdd_external_annexation_mandate_paid" in registration,
            "a revived member cannot start a fresh annexation lifecycle")

    opinion = block(texts["opinions"], "gdd_opinion_revoked_tianxia_reform")
    for token in ("opinion = -10", "yearly_decay = 2", "min = -100"):
        require(token in opinion, f"revocation opinion missing {token}")

    required_main_loc = [
        "gdd_tianxia_internal_peace_mandate",
        "gdd_tianxia_seven_invalid_great_feudatories",
        "gdd_celestial_mandate.1.t",
        "gdd_tianxia_emperor_external_subject_mandate",
        "gdd_tianxia_emperor_internal_subject_mandate",
    ]
    for key in required_main_loc:
        require(re.search(rf"(?m)^\s*{re.escape(key)}:\d+ ", texts["loc"]) is not None,
                f"missing readable localisation {key}")

    required_mandate_loc = [
        "IMPERIAL_MANDATE_DESC",
        "IMPERIAL_MANDATE_GAIN_DESC",
        "IMPERIAL_MANDATE_LOSS_DESC",
    ]
    for key in required_mandate_loc:
        require(re.search(rf"(?m)^\s*{re.escape(key)}:\d+ ", texts["mandate_loc"]) is not None,
                f"missing readable localisation {key}")

    required_wangming_loc = [
        "flavor_dai.4.t",
        "CELESTIAL_EMPIRE_WAR_NAME",
        "cb_take_mandate",
        "mch_mandate_of_heaven_title",
        "mnd_siam_take_the_mandate_title",
        "mandate_of_heaven_mission_title",
        "TAKE_MANDATE_PO_LIST_TEXT",
    ]
    for key in required_wangming_loc:
        require(re.search(rf"(?m)^\s*{re.escape(key)}:\d+ ", texts["terminology_loc"])
                is not None, f"missing Wangming terminology override {key}")
    for path in (MOD / "localisation_source").glob("*.txt"):
        require("\u5929\u547d" not in path.read_text(encoding="utf-8-sig"),
                f"player-facing localisation reintroduced Tianming: {path.name}")

    # The native Mandate number remains engine-owned, while two invisible
    # scripted text boxes replace only the hard-coded vanilla hover surface.
    interface = texts["interface"]
    authority_gui = texts["authority_gui"]
    require("hint_imperialauthority" not in interface,
            "hard-coded vanilla Mandate hover is still attached")
    for name in ("gdd_eoc_mandate_value_tooltip", "gdd_eoc_mandate_growth_tooltip"):
        require(interface.count(f'name = "{name}"') == 1,
                f"missing or duplicated Mandate hover surface {name}")
        require(authority_gui.count(f"name = {name}") == 1,
                f"missing or duplicated scripted binding {name}")
    require(authority_gui.count("tooltip = GDD_EOC_MANDATE_MONTHLY_TT") == 2,
            "Mandate value and growth do not share the registered dynamic tooltip")
    require("GetGddEocMandateStabilityRow" not in texts["mandate_tooltip"]
            and "GetGddEocMandateStabilityRow" not in texts["ui_loc"],
            "neutralised stability is still presented as a Mandate source")

    # Exact zero has its own hover so the authority-driven monthly resource
    # penalty remains visible across the complete -25..25 deadlock interval.
    for name in ("gdd_eoc_authority_value_zero", "gdd_eoc_authority_bar_zero"):
        body = custom_gui_block(authority_gui, name)
        require("is_variable_equal" in body and "value = 0" in body,
                f"{name} is not restricted to exact zero")
        require("tooltip = GDD_EOC_CURRENT_BALANCE_EFFECTS_TT" in body,
                f"{name} lacks the zero-authority Mandate explanation")
    for name in ("gdd_eoc_authority_value_p000", "gdd_eoc_authority_bar_p000"):
        body = custom_gui_block(authority_gui, name)
        require("value = 0.001" in body and "value = 10" in body,
                f"{name} does not cover only positive sub-10 authority")
        require("tooltip = GDD_EOC_CURRENT_CENTRAL_EFFECTS_TT" in body,
                f"{name} lacks the central-authority explanation")

    # The registry is the contract between real sources and presentation.
    registry = json.loads(texts["registry"])
    all_ids: list[str] = []
    main_tooltip_line = next(
        line for line in texts["ui_loc"].splitlines()
        if line.lstrip().startswith("GDD_EOC_MANDATE_MONTHLY_TT:")
    )
    for group in ("continuous", "monthly_scripted", "neutralized_vanilla",
                  "one_time_not_monthly"):
        require(group in registry, f"Mandate source registry lacks {group}")
        for source in registry[group]:
            all_ids.append(source["id"])
            source_path = MOD / source["file"]
            require(source_path.is_file(), f"registered Mandate source file missing: {source_path}")
            source_text = source_path.read_text(encoding="utf-8-sig")
            require(source["token"] in source_text,
                    f"registered Mandate source drifted: {source['id']}")
            accessor = source.get("tooltip_accessor")
            if accessor:
                require(f"name = {accessor}" in texts["mandate_tooltip"],
                        f"registered source lacks accessor: {source['id']}")
                require(f"[EmperorOfChina.{accessor}]" in main_tooltip_line,
                        f"registered source is absent from the Mandate hover: {source['id']}")
    require(len(all_ids) == len(set(all_ids)), "Mandate source registry contains duplicate IDs")

    # Shield hovers are AI-only and derive their two detailed reforms from the
    # same authoritative cached ballots used by the voting system.
    member_tooltips = texts["member_tooltips"]
    vote_effects = texts["vote_effects"]
    top_level_member = block(member_tooltips, "defined_text")
    require("localisation_key = gdd_eoc_member_tooltip_blank" in top_level_member
            and "trigger = { ai = no }" in top_level_member,
            "player-controlled members do not resolve to a blank hover")
    require(texts["ui_loc"].count("GDD_EOC_MEMBER_SHIELD_") == 65,
            "member tooltip localisation does not cover all 65 shield slots")
    require(texts["member_gui"].count("tooltip = GDD_EOC_MEMBER_SHIELD_") == 65,
            "member GUI does not bind all 65 unique shield tooltips")
    rank_calls = re.findall(
        r"gdd_consider_ai_reform_tooltip_rank_effect = \{ "
        r"support_flag = (gdd_support_reform_[a-z_]+) reform_id = (\d+) \}",
        vote_effects,
    )
    require(len(rank_calls) == 20,
            "top-two support ranking does not cover the visible 8/6/6 reforms exactly")
    require({int(reform_id) for _, reform_id in rank_calls} == set(range(1, 21)),
            "top-two support ranking IDs are not the stable visible 1..20 order")
    require(len({flag for flag, _ in rank_calls}) == 20,
            "a visible reform is duplicated or missing from top-two ranking")
    rank_effect = block(vote_effects, "gdd_consider_ai_reform_tooltip_rank_effect")
    require("value = 100" in rank_effect and "value = $reform_id$" in rank_effect,
            "top-two ranking no longer sorts by score then visible order")
    require("support_flag = gdd_support_reform_military_faction reform_id" not in vote_effects,
            "removed military-faction reform leaked into member tooltip ranking")
    require("which = gdd_reform_tooltip_supported_count value = 3" in member_tooltips,
            "the compact other-support summary is not limited to ballots beyond the top two")
    require('gdd_eoc_member_other_supports_block:0 "\\n另支持' in texts["ui_loc"],
            "other supported reforms do not use the approved compact wording")

    # Arithmetic white-box cases independent of Clausewitz evaluation order.
    for valid_seats in range(8):
        expected = -0.05 * (7 - valid_seats)
        actual = 0.0 if valid_seats == 7 else -0.05 * (7 - valid_seats)
        require(abs(actual - expected) < 1e-9,
                f"seat-loss arithmetic failed at {valid_seats} valid seats")
    for development in (1, 50, 199, 200, 500):
        require(-0.1 * min(development, 200) >= -20,
                f"exit loss exceeds cap at {development} development")
    subject_cases = (
        # real subject, exempt subject, Zhou overlord, external, internal
        (False, False, False, False, False),
        (True, True, False, False, False),
        (True, False, False, True, False),
        (True, False, True, False, True),
    )
    for real_subject, exempt, zhou_overlord, expect_external, expect_internal in subject_cases:
        external = real_subject and not exempt and not zhou_overlord
        internal = real_subject and not exempt and zhou_overlord
        require((external, internal) == (expect_external, expect_internal),
                "subject-penalty exclusivity matrix failed")
    for starting in (-100, -98, 0, 98, 100):
        shifted = max(-100, min(100, starting - 5))
        require(-100 <= shifted <= 100 and shifted <= starting,
                f"authority shift/clamp failed from {starting}")
    for authority_value in range(-100, 101):
        deadlocked = -25 <= authority_value <= 25
        leaning = (-99 <= authority_value <= -26) or (26 <= authority_value <= 99)
        absolute = authority_value in (-100, 100)
        require(sum((deadlocked, leaning, absolute)) == 1,
                f"authority Mandate tiers overlap or leave a gap at {authority_value}")
        actual = -0.10 if deadlocked else (0.05 if leaning else 0.10)
        expected = (0.10 if abs(authority_value) == 100 else
                    -0.10 if abs(authority_value) <= 25 else 0.05)
        require(abs(actual - expected) < 1e-9,
                f"authority Mandate arithmetic failed at {authority_value}")
    for is_ai, supports, expected in (
        (False, False, True), (False, True, True),
        (True, False, False), (True, True, True),
    ):
        require((not is_ai or supports) == expected,
                "AI reform-executor consent truth table failed")

    print("PASS: Zhou Mandate white-box contracts")
    print("  stability, tributary, devastation, loan, corruption and bankruptcy Mandate effects: neutral")
    print("  internal peace: +0.10/month; invalid seats: -0.05 each/month")
    print("  authority: -25..25 gives -0.10/month; 26..99 and -99..-26 give +0.05/month; endpoints give +0.10/month")
    print("  AI reform executors must cast their own support ballot")
    print("  Emperor subject: external -1/month; Zhou -0.05/month and authority -5/month")
    print("  seat penalties are gated until the post-migration cache is ready")
    print("  foreign occupation: -0.005/province/month")
    print("  external full annexation and defense refusal: -10 once")
    print("  voluntary exit: -0.1/development, capped at -20")
    print("  reform enactment: requires caller threshold and consumes the Mandate pool")
    print("  revocation opinion: ROOT-scoped, stacks to -100, natural yearly decay")


if __name__ == "__main__":
    main()

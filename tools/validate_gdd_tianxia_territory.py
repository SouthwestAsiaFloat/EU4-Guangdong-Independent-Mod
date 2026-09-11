"""White-box validation for the scripted Zhou Tianxia territory layer."""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"

TRIGGERS = MOD / "common/scripted_triggers/gdd_tianxia_territory_triggers.txt"
EFFECTS = MOD / "common/scripted_effects/gdd_tianxia_territory_effects.txt"
CUSTOM_GUI = MOD / "common/custom_gui/gdd_tianxia_territory_gui.txt"
NATIVE_ACTIONS = MOD / "common/new_diplomatic_actions/gdd_tianxia_actions.txt"
EVENTS = MOD / "events/gdd_tianxia_territory_events.txt"
ON_ACTIONS = MOD / "common/on_actions/zhx_system_on_actions.txt"
SYSTEM_EVENTS = MOD / "events/zhx_system_events.txt"
SYSTEM_EFFECTS = MOD / "common/scripted_effects/zhx_system_effects.txt"
CB_TYPES = MOD / "common/cb_types/gdd_cb_types.txt"
WARGOALS = MOD / "common/wargoal_types/gdd_wargoal_types.txt"
MODIFIERS = MOD / "common/event_modifiers/gdd_tianxia_territory_modifiers.txt"
OPINIONS = MOD / "common/opinion_modifiers/gdd_celestial_reform_opinions.txt"
PROVINCE_GUI = MOD / "interface/provinceview.gui"
TIANXIA_GFX = MOD / "interface/gdd_tianxia_territory.gfx"
DIPLO_GUI = MOD / "interface/countrydiplomacyview.gui"
TOPBAR_GUI = MOD / "interface/topbar.gui"
EOC_GUI = MOD / "interface/celestialempireview.gui"
LOCALISATION = MOD / "localisation_source/gdd_celestial_ui_readable_utf8.txt"
CUSTOM_LOCALISATION = MOD / "customizable_localization/gdd_tianxia_unlawful_tooltips.txt"


def read(path: Path) -> str:
    if not path.is_file():
        raise AssertionError(f"missing file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8-sig")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def pixels(image: Image.Image):
    """Return pixels without relying on Pillow's deprecated getdata alias."""
    if hasattr(image, "get_flattened_data"):
        return image.get_flattened_data()
    return image.getdata()


def strip_comments_and_strings(text: str) -> str:
    result: list[str] = []
    in_string = False
    escaped = False
    index = 0
    while index < len(text):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            result.append(" ")
            index += 1
            continue
        if char == '"':
            in_string = True
            result.append(" ")
            index += 1
            continue
        if char == "#":
            while index < len(text) and text[index] not in "\r\n":
                result.append(" ")
                index += 1
            continue
        result.append(char)
        index += 1
    require(not in_string, "unterminated quoted string")
    return "".join(result)


def require_balanced(path: Path) -> None:
    clean = strip_comments_and_strings(read(path))
    depth = 0
    for index, char in enumerate(clean):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            require(depth >= 0, f"unexpected closing brace in {path.name} at byte {index}")
    require(depth == 0, f"unbalanced braces in {path.name}: final depth {depth}")


def named_block(text: str, name: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text)
    require(match is not None, f"missing block: {name}")
    start = match.start()
    open_brace = text.find("{", match.start(), match.end())
    depth = 0
    in_string = False
    escaped = False
    index = open_brace
    while index < len(text):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char == "#":
            newline = text.find("\n", index)
            index = len(text) if newline < 0 else newline
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
        index += 1
    raise AssertionError(f"unterminated block: {name}")


def custom_gui_block(text: str, name: str) -> str:
    match = re.search(
        rf"(?ms)^custom_(?:button|icon)\s*=\s*\{{\n"
        rf"\s*name\s*=\s*{re.escape(name)}\n.*?^\}}$",
        text,
    )
    require(match is not None, f"missing custom GUI block: {name}")
    return match.group(0)


def main() -> None:
    clausewitz_files = (
        TRIGGERS,
        EFFECTS,
        MOD / "common/scripted_effects/gdd_tianxia_picker_effects.txt",
        CUSTOM_GUI,
        NATIVE_ACTIONS,
        EVENTS,
        ON_ACTIONS,
        SYSTEM_EVENTS,
        SYSTEM_EFFECTS,
        CB_TYPES,
        WARGOALS,
        MODIFIERS,
        OPINIONS,
        PROVINCE_GUI,
        TIANXIA_GFX,
        DIPLO_GUI,
        TOPBAR_GUI,
        EOC_GUI,
        CUSTOM_LOCALISATION,
    )
    for path in clausewitz_files:
        require_balanced(path)

    triggers = read(TRIGGERS)
    effects = read(EFFECTS)
    custom_gui = read(CUSTOM_GUI)
    native_actions = read(NATIVE_ACTIONS)
    events = read(EVENTS)
    on_actions = read(ON_ACTIONS)
    system_events = read(SYSTEM_EVENTS)
    system_effects = read(SYSTEM_EFFECTS)
    cb_types = read(CB_TYPES)
    wargoals = read(WARGOALS)
    modifiers = read(MODIFIERS)
    opinions = read(OPINIONS)
    province_gui = read(PROVINCE_GUI)
    tianxia_gfx = read(TIANXIA_GFX)
    diplo_gui = read(DIPLO_GUI)
    topbar_gui = read(TOPBAR_GUI)
    eoc_gui = read(EOC_GUI)
    loc = read(LOCALISATION)
    custom_loc = read(CUSTOM_LOCALISATION)

    add_trigger = named_block(triggers, "gdd_can_add_province_to_tianxia_for_country_trigger")
    require("is_part_of_hre = no" in add_trigger,
            "Tianxia admission does not exclude HRE provinces")
    require("is_owned_by_trade_company = no" in add_trigger,
            "Tianxia admission does not exclude trade-company provinces")
    remove_trigger = named_block(triggers, "gdd_can_remove_province_from_tianxia_for_country_trigger")
    require("gdd_tianxia_unlawful_request_pending" in remove_trigger,
            "manual removal can bypass a pending unlawful-territory request")
    require("gdd_tianxia_unlawful_refusal" in remove_trigger,
            "a refusal can evade its punishment by immediately removing the province")
    unlawful_trigger = named_block(triggers, "gdd_is_unlawful_tianxia_province_for_country_trigger")
    substantive = named_block(triggers, "gdd_is_substantively_unlawful_tianxia_province_trigger")
    for token in (
        "zhx_tianxia_province", "gdd_tianxia_liberated_this_owner",
        "NOT = { is_core = $who$ }", "gdd_tianxia_province_has_lawful_returnee_trigger = yes",
    ):
        require(token in substantive, f"unlawful-territory definition lost: {token}")
    require("gdd_is_substantively_unlawful_tianxia_province_trigger" in unlawful_trigger,
            "button and resolution no longer share the core/returnee rules")
    require("gdd_tianxia_unlawful_requested_this_owner" not in unlawful_trigger
            and "set_province_flag = gdd_tianxia_unlawful_requested_this_owner" not in effects,
            "same-owner permanent province lock can still block annual requests")
    require("$who$ = { NOT = { zhx_is_tianxia_polity = yes } }" not in substantive,
            "foreign core ownership no longer exempts unlawful-territory demands")
    receiver_trigger = named_block(triggers, "gdd_can_receive_tianxia_unlawful_demand_trigger")
    for token in ("days = 365", "is_subject = yes", "overlord = {", "war_with = $emperor$"):
        require(token in receiver_trigger, f"demand eligibility lost: {token}")
    require("gdd_is_unlawful_tianxia_province_for_country_trigger = { who = PREV }" in receiver_trigger
            and "NOT = { war_with = PREV }" in receiver_trigger,
            "receiver eligibility still binds nested event checks to outer ROOT")

    remove_effect = named_block(effects, "gdd_remove_province_from_tianxia_effect")
    add_effect = named_block(effects, "gdd_add_province_to_tianxia_effect")
    for token in (
        "zhx_tianxia_admission_reward_paid",
        "value = 200",
        "add_mandate = 0.1",
    ):
        require(token in add_effect, f"per-province admission reward drifted: {token}")
    for token in ("value = 200", "add_mandate = -0.1"):
        require(token in remove_effect, f"per-province removal cost drifted: {token}")
    require("add_opinion" not in remove_effect,
            "province removal still applies opinion from an unreliable province scope")
    removal_opinion = named_block(effects, "gdd_apply_tianxia_removal_opinion_effect")
    for token in (
        "save_event_target_as = gdd_tianxia_removal_offender",
        "event_target:EmperorOfChina = {",
        "add_opinion = {",
        "who = event_target:gdd_tianxia_removal_offender",
        "CZH = { exists = yes is_emperor_of_china = yes }",
        "gdd_opinion_removed_tianxia_province",
    ):
        require(token in removal_opinion,
                f"country-scoped removal opinion path is incomplete: {token}")
    require("save_event_target_as = gdd_tianxia_removal_owner" not in events
            and "save_event_target_as = gdd_tianxia_removal_owner" not in effects
            and "reverse_add_opinion" not in removal_opinion,
            "manual removal still depends on a transient owner event target")
    trade_company_hook = named_block(on_actions, "on_added_to_trade_company")
    require("has_province_flag = zhx_tianxia_province" in trade_company_hook
            and "clr_province_flag = zhx_tianxia_province" in trade_company_hook,
            "trade-company bypass can retain simultaneous Tianxia membership")
    require("remove_from_trade_company" not in on_actions
            and "remove_from_trade_company" not in effects,
            "unsupported remove-from-trade-company effect remains in scripts")
    prepare_effect = named_block(effects, "gdd_prepare_tianxia_unlawful_acceptance_effect")
    expected_reason_scores = {
        "gdd_tianxia_unlawful_reason_emperor_subject": 100,
        "gdd_tianxia_unlawful_reason_emperor_much_stronger": 40,
        "gdd_tianxia_unlawful_reason_emperor_stronger": 20,
        "gdd_tianxia_unlawful_reason_recipient_stronger": -40,
        "gdd_tianxia_unlawful_reason_opinion_very_high": 20,
        "gdd_tianxia_unlawful_reason_opinion_high": 10,
        "gdd_tianxia_unlawful_reason_opinion_low": -15,
        "gdd_tianxia_unlawful_reason_opinion_very_low": -25,
        "gdd_tianxia_unlawful_reason_trust_very_high": 20,
        "gdd_tianxia_unlawful_reason_trust_high": 10,
        "gdd_tianxia_unlawful_reason_trust_low": -10,
        "gdd_tianxia_unlawful_reason_allied": 15,
        "gdd_tianxia_unlawful_reason_hostile": -35,
        "gdd_tianxia_unlawful_reason_diprep_very_high": 15,
        "gdd_tianxia_unlawful_reason_diprep_high": 8,
        "gdd_tianxia_unlawful_reason_diprep_low": -10,
    }
    for flag, score in expected_reason_scores.items():
        require(re.search(
            rf"change_variable\s*=\s*\{{\s*"
            rf"which\s*=\s*gdd_tianxia_unlawful_acceptance_score\s*"
            rf"value\s*=\s*{score}\s*\}}\s*set_country_flag\s*=\s*{flag}",
            prepare_effect,
            re.S,
        ) is not None, f"AI acceptance reason/score mapping drifted: {flag}={score}")
    require(re.search(
        r"check_variable\s*=\s*\{\s*"
        r"which\s*=\s*gdd_tianxia_unlawful_acceptance_score\s*value\s*=\s*0\s*\}"
        r"\s*\}\s*set_country_flag\s*=\s*gdd_tianxia_unlawful_ai_will_accept",
        prepare_effect,
        re.S,
    ) is not None, "AI acceptance outcome is no longer deterministic at score >= 0")
    dispatch_effect = named_block(effects, "gdd_dispatch_tianxia_unlawful_demand_effect")
    for token in (
        "gdd_tianxia_unlawful_request_pending",
        "gdd_tianxia_unlawful_demand_cooldown",
        "gdd_tianxia_territory.11",
        "zhx_is_tianzi = yes",
        "gdd_accept_tianxia_unlawful_demand_effect = yes",
    ):
        require(token in dispatch_effect, f"demand dispatch lost: {token}")
    accept_effect = named_block(effects, "gdd_accept_tianxia_unlawful_demand_effect")
    resolver = named_block(effects, "gdd_select_lawful_tianxia_returnee_effect")
    for token in (
        "every_core_country", "previous_owner = PREV",
        "gdd_tianxia_former_legal_owner", "gdd_is_lawful_tianxia_returnee_trigger",
    ):
        require(token in resolver, f"lawful core-country resolution is incomplete: {token}")
    require("random_country" not in resolver and "add_core" not in accept_effect,
            "restitution can pick a random recipient or manufacture an Emperor core")
    require("gdd_select_lawful_tianxia_returnee_effect = yes" in accept_effect
            and "gdd_tianxia_unlawful_returnee_selected" in accept_effect
            and "zhx_register_tianxia_member = yes" in accept_effect,
            "return cannot safely restore an extinct member")
    historical = named_block(triggers, "gdd_is_opening_tianxia_core_tag_trigger")
    opening = named_block(system_effects, "zhx_initialise_tianxia_system")
    require(set(re.findall(r"tag = ([A-Z0-9]{3})", historical))
            == set(re.findall(r"tag = ([A-Z0-9]{3})", opening)) | {"CZH"},
            "restoration catalogue drifted from the opening member catalogue")
    require("zhx_migrate_tianxia_system_v14_to_v15 = yes" in system_events,
            "annual request-lock migration is not scheduled")
    v15 = named_block(system_effects, "zhx_migrate_tianxia_system_v14_to_v15")
    require("clr_province_flag = gdd_tianxia_unlawful_requested_this_owner" in v15
            and "gdd_tianxia_unlawful_demand_cooldown" not in v15,
            "migration must retire province locks without resetting country cooldowns")
    require("remove_claim = event_target:gdd_tianxia_unlawful_actual_owner" in accept_effect,
            "acceptance does not remove the dispossessed holder's claim")
    require("gdd_tianxia_territory.12" not in accept_effect,
            "acceptance still sends the Emperor an unwanted return event")
    refuse_effect = named_block(effects, "gdd_refuse_tianxia_unlawful_demand_effect")
    for token in (
        "duration = 3650",
        "country_event = { id = gdd_tianxia_territory.24 days = 1 }",
    ):
        require(token in refuse_effect, f"refusal consequence missing: {token}")
    refusal_bridge = events[events.index("    id = gdd_tianxia_territory.24"):]
    for token in ("months = 60", "target = ROOT", "who = ROOT", "gdd_opinion_refused_tianxia_unlawful_demand", "gdd_tianxia_territory.13 days = 1"):
        require(token in refusal_bridge, f"refusal bridge consequence missing: {token}")
    require("add_mandate" not in refuse_effect,
            "refusal still changes Mandate despite the approved design")
    quarterly = named_block(effects, "gdd_quarterly_tianxia_territory_maintenance_effect")
    require("country_event = { id = gdd_tianxia_territory.10 }" in quarterly,
            "AI Emperor does not initiate unlawful-territory demands")
    require(quarterly.count("gdd_tianxia_unlawful_demand_considered_this_tick") == 3,
            "same-tick lock no longer prevents a just-demanded province from auto-removal")
    require(quarterly.count("gdd_tianxia_unlawful_ai_demand_sent_this_tick") >= 4,
            "AI Emperor is not globally limited to one demand attempt per quarter")
    require("gdd_apply_tianxia_removal_opinion_effect = yes" in quarterly,
            "automatic nonmember removal bypasses the Emperor opinion penalty")
    require(re.search(
        r"NOT\s*=\s*\{\s*has_opinion\s*=\s*\{\s*"
        r"who\s*=\s*event_target:zhx_tianzi\s*value\s*=\s*-50",
        quarterly,
        re.S,
    ) is not None, "nonmember AI removal is not restricted to opinion below -50")

    for token in (
        "clr_province_flag = gdd_tianxia_unlawful_request_pending",
        "clr_province_flag = gdd_tianxia_unlawful_requested_this_owner",
        "set_province_flag = gdd_tianxia_liberated_this_owner",
        "set_country_flag = gdd_tianxia_former_legal_owner",
        "is_part_of_hre = yes",
        "set_in_empire = no",
    ):
        require(token in on_actions, f"owner-change lifecycle missing: {token}")
    repair_effect = named_block(effects, "gdd_repair_tianxia_hre_exclusivity_effect")
    for token in ("every_province", "zhx_tianxia_province", "is_part_of_hre = yes", "set_in_empire = no"):
        require(token in repair_effect, f"legacy HRE/Tianxia overlap repair lost: {token}")
    require("NOT = { has_global_flag = zhx_system_initialised_v14 }" in system_events
            and "zhx_migrate_tianxia_system_v13_to_v14 = yes" in system_events,
            "v14 legacy-overlap migration is not scheduled")
    v14_migration = named_block(system_effects, "zhx_migrate_tianxia_system_v13_to_v14")
    require("gdd_repair_tianxia_hre_exclusivity_effect = yes" in v14_migration
            and "set_global_flag = zhx_system_initialised_v14" in v14_migration,
            "v14 legacy-overlap migration is incomplete")

    for event_id in (".2", ".10", ".11", ".13"):
        require(f"id = gdd_tianxia_territory{event_id}" in events,
                f"missing territory event {event_id}")
    require("id = gdd_tianxia_territory.12" not in events,
            "successful restitution still reports back to the Emperor")
    require("custom_tooltip = GDD_TIANXIA_PROVINCE_REMOVE_OPTION_TT" in events,
            "manual-removal option has no exact consequence tooltip")
    event2 = re.search(
        r"country_event\s*=\s*\{\s*id\s*=\s*gdd_tianxia_territory\.2(.*?)"
        r"(?=\n\s*country_event\s*=|\Z)",
        events,
        re.S,
    )
    require(event2 is not None, "missing manual Tianxia-province removal event")
    event2_text = event2.group(1)
    for token in (
        "event_target:EmperorOfChina = {",
        "add_opinion = {",
        "who = ROOT",
        "modifier = gdd_opinion_removed_tianxia_province",
        "CZH = { exists = yes is_emperor_of_china = yes }",
        "gdd_remove_province_from_tianxia_effect = yes",
    ):
        require(token in event2_text,
                f"manual removal lacks direct Emperor-to-offender opinion handling: {token}")
    require("gdd_apply_tianxia_removal_opinion_effect" not in event2_text
            and event2_text.find("add_opinion = {")
            < event2_text.find("gdd_remove_province_from_tianxia_effect = yes"),
            "manual removal still uses the failed nested/reverse opinion path")
    for event_id in (2, 10):
        require(re.search(
            rf"id\s*=\s*gdd_tianxia_territory\.{event_id}.*?"
            rf"immediate\s*=\s*\{{\s*hidden_effect\s*=\s*\{{",
            events,
            re.S,
        ) is not None, f"territory event {event_id} exposes internal immediate effects")
    require("custom_tooltip = GDD_TIANXIA_UNLAWFUL_REFUSE_TT" in events,
            "unlawful-territory refusal has no consequence tooltip")
    require("custom_tooltip = GDD_TIANXIA_UNLAWFUL_REFUSAL_CONFIRM_TT" in events,
            "Emperor refusal-return event does not identify the granted casus belli")
    require("NOT = { has_country_flag = gdd_tianxia_unlawful_ai_will_accept }" in events
            and "has_country_flag = gdd_tianxia_unlawful_ai_will_accept" in events,
            "recipient AI options no longer follow the visible deterministic outcome")

    require("local_manpower_modifier = -0.5" in modifiers
            and "local_unrest = 10" in modifiers
            and "local_tax_modifier = -0.33" in modifiers
            and "local_autonomy = 0.1" in modifiers,
            "refusal province modifier no longer mirrors vanilla unlawful territory")
    require("opinion = -100" in named_block(opinions, "gdd_opinion_forced_tianxia_return")
            and "yearly_decay = 2" in named_block(opinions, "gdd_opinion_forced_tianxia_return"),
            "forced-return opinion values drifted")
    removed_opinion = named_block(opinions, "gdd_opinion_removed_tianxia_province")
    for token in ("opinion = -25", "yearly_decay = 1", "min = -100"):
        require(token in removed_opinion, f"removal opinion value drifted: {token}")
    require("months = 0" not in removed_opinion,
            "scripted removal opinion still has a zero-month lifetime")
    require("years = 100" in removal_opinion and "years = 100" in event2_text,
            "manual and automatic removal opinions lack a persistent lifetime")
    refused_opinion = named_block(opinions, "gdd_opinion_refused_tianxia_unlawful_demand")
    for token in ("opinion = -25", "months = 300", "yearly_decay = 1"):
        require(token in refused_opinion, f"refusal opinion value drifted: {token}")
    require("gdd_cb_tianxia_liberation" in cb_types
            and "months = 60" in named_block(cb_types, "gdd_cb_tianxia_liberation"),
            "five-year liberation CB is missing")
    liberation_cb = named_block(cb_types, "gdd_cb_tianxia_liberation")
    for token in (
        "zhx_is_tianzi = yes",
        "NOT = { has_global_flag = zhx_tianxia_dismantled }",
        "has_province_flag = zhx_tianxia_province",
        "has_province_modifier = gdd_tianxia_unlawful_refusal",
        "any_subject_country = {",
    ):
        require(token in liberation_cb,
                f"liberation CB can survive without its Tianxia dispute: {token}")
    liberation_goal = named_block(wargoals, "gdd_tianxia_liberation_wargoal")
    for token in (
        "has_province_flag = zhx_tianxia_province",
        "has_province_modifier = gdd_tianxia_unlawful_refusal",
        "badboy_factor = 1",
        "prestige_factor = 2",
        "peace_cost_factor = 0.75",
        "po_release_vassals",
        "po_release_annexed",
        "po_return_cores",
        "po_demand_provinces",
    ):
        require(token in liberation_goal,
                f"liberation wargoal no longer mirrors vanilla take_province_hre: {token}")
    for non_vanilla_token in (
        "allowed_provinces_are_eligible",
        "po_revoke_cores",
        "po_gold",
        "po_annul_treaties",
        "deny_annex",
    ):
        require(non_vanilla_token not in liberation_goal,
                f"non-vanilla liberation term remains: {non_vanilla_token}")

    for retired_name in (
        "gdd_tianxia_actions_expanded_button",
        "gdd_tianxia_actions_collapsed_button",
        "gdd_tianxia_demand_unlawful_territory_button",
        "gdd_tianxia_unlawful_gui_selection",
    ):
        require(retired_name not in custom_gui
                and retired_name not in diplo_gui
                and retired_name not in events,
                f"retired handcrafted diplomacy control remains: {retired_name}")
    require(custom_gui.count("has_global_flag = zhx_system_initialised_v13") == 6,
            "one or more Tianxia controls can appear before the live system exists")
    dismantle_potential = re.search(
        r"name\s*=\s*gdd_dismantle_tianxia_button\s+potential\s*=\s*\{(.*?)\}\s+"
        r"trigger\s*=",
        custom_gui,
        re.S,
    )
    require(dismantle_potential is not None
            and "event_target:zhx_tianzi" not in dismantle_potential.group(1),
            "dismantle action is hidden instead of disabled when the Tianzi is unavailable")
    native_action = named_block(
        native_actions, "gdd_tianxia_demand_unlawful_territory"
    )
    for token in (
        "category = is_emperor_of_china",
        "alert_index = 22",
        "require_acceptance = no",
        "gdd_can_be_tianxia_unlawful_addressee_trigger",
        "gdd_open_tianxia_unlawful_picker_effect = yes",
        "ai_will_do = { always = no }",
    ):
        require(token in native_action, f"native diplomacy action is incomplete: {token}")
    require("ai = no" in native_action,
            "native action is not restricted to the human Emperor")
    picker_effects = read(MOD / "common/scripted_effects/gdd_tianxia_picker_effects.txt")
    for name in ("gdd_open_tianxia_unlawful_picker_effect", "gdd_build_tianxia_unlawful_picker_page_effect", "gdd_close_tianxia_unlawful_picker_effect"):
        require(name in picker_effects, f"missing province picker effect: {name}")
    require("gdd_select_highest_development" not in picker_effects,
            "manual picker must not replace the selected province automatically")
    require("gdd_close_tianxia_unlawful_picker_effect = yes" in named_block(effects, "gdd_dismantle_tianxia_effect"),
            "dismantling must clear the picker lock")
    for slot in range(1, 5):
        require(f"gdd_tianxia_picker_province_{slot}_option" in events,
                f"missing picker option {slot}")
    require("id = gdd_tianxia_territory.21" in events,
            "manual picker has no confirmation event")
    pages = {}
    for event_id in (20, 22):
        start = events.index(f"    id = gdd_tianxia_territory.{event_id}\n")
        end = events.find("\ncountry_event = {", start)
        pages[event_id] = events[start:end if end >= 0 else len(events)].strip()
        # Strip trailing comments belonging to the next top-level declaration.
        pages[event_id] = pages[event_id][:pages[event_id].rfind("}") + 1]
        require(f"country_event = {{ id = gdd_tianxia_territory.{event_id} }}" not in pages[event_id],
                "picker page synchronously reopens its own active event")
    require(pages[20].replace("id = gdd_tianxia_territory.20\n", "id = gdd_tianxia_territory.22\n", 1)
            .replace("country_event = { id = gdd_tianxia_territory.22 }", "country_event = { id = gdd_tianxia_territory.20 }") == pages[22],
            "alternating picker pages have drifted apart")
    event10 = re.search(
        r"country_event\s*=\s*\{\s*id\s*=\s*gdd_tianxia_territory\.10(.*?)"
        r"(?=\n\s*country_event\s*=|\Z)",
        events,
        re.S,
    )
    require(event10 is not None, "missing unlawful-territory confirmation event")
    event10_trigger = re.search(r"trigger\s*=\s*\{(.*?)\}\s*immediate", event10.group(1), re.S)
    require(event10_trigger is not None
            and "zhx_is_tianzi = yes" in event10_trigger.group(1)
            and "gdd_can_receive_tianxia_unlawful_demand_trigger" not in event10_trigger.group(1),
            "confirmation event can still be silently vetoed by same-click target state")

    for retired_alert_token in (
        "gdd_tianxia_unlawful_territory_alert_button",
        "GFX_gdd_tianxia_unlawful_territory_alert",
        "GDD_TIANXIA_UNLAWFUL_ALERT_TT",
    ):
        require(retired_alert_token not in custom_gui
                and retired_alert_token not in topbar_gui
                and retired_alert_token not in tianxia_gfx
                and retired_alert_token not in loc,
                f"retired scripted alert still overrides native alert layout: {retired_alert_token}")
    require(not (MOD / "interface/alerts.gui").exists(),
            "alerts.gui still shifts every native alert one slot to the right")
    require(not (MOD / "gfx/interface/gdd_tianxia_unlawful_territory_alert.tga").exists(),
            "retired scripted alert artwork is still packaged")

    status_pos = province_gui.find('name = "gdd_tianxia_province_member_status_button"')
    hre_pos = province_gui.find('name ="hre_button"')
    require(hre_pos >= 0 and status_pos > hre_pos,
            "Tianxia status does not overlay the hard-coded HRE slot")
    require(re.search(
        r"guiButtonType\s*=\s*\{\s*name\s*=\s*"
        r'"gdd_tianxia_province_member_status_button".*?'
        r'quadTextureSprite\s*=\s*"GFX_gdd_tianxia_province_status".*?'
        r'position\s*=\s*\{\s*x\s*=\s*20\s+y\s*=\s*328\s*\}',
        province_gui,
        re.S,
    ) is not None, "member emblem is not anchored to the native imperial button slot")
    require(re.search(
        r'name\s*=\s*"trade_company_icon".*?'
        r'position\s*=\s*\{\s*x\s*=\s*32\s+y\s*=\s*328\s*\}.*?'
        r'alwaystransparent\s*=\s*yes',
        province_gui,
        re.S,
    ) is not None and re.search(
        r'name\s*=\s*"trade_company_button".*?'
        r'position\s*=\s*\{\s*x\s*=\s*20\s+y\s*=\s*328\s*\}',
        province_gui,
        re.S,
    ) is not None,
            "native HRE/trade-company controls do not share their original slot")
    require('name = "GFX_gdd_tianxia_province_status"' in tianxia_gfx
            and "noOfFrames = 4" in tianxia_gfx,
            "member emblem is not an inert four-state overlay")
    for control_name in (
        "gdd_tianxia_province_member_status_button",
        "gdd_tianxia_province_remove_button",
    ):
        require("is_part_of_hre = no" in custom_gui_block(custom_gui, control_name),
                f"{control_name} can overlap the hard-coded HRE emblem")
    status_art = Image.open(MOD / "gfx/interface/gdd_tianxia_province_status.tga").convert("RGBA")
    require(status_art.size == (216, 42), "member emblem runtime art is not a four-state strip")
    # Check the union of the actual native icon and button rectangles, including
    # the twelve pixels beyond the original 42px glyph, in every button state.
    for control_name in ("hre_icon", "trade_company_icon", "hre_button", "trade_company_button"):
        block = re.search(r'name\s*=\s*"' + control_name + r'"(.*?)(?=\n\s*\})', province_gui, re.S)
        require(block is not None, f"missing native control: {control_name}")
        pos = re.search(r'position\s*=\s*\{\s*x\s*=\s*(\d+)\s+y\s*=\s*(\d+)', block.group(1))
        require(pos is not None, f"missing native position: {control_name}")
        x, y = map(int, pos.groups())
        for filename in ("gdd_tianxia_province_status.tga", "gdd_tianxia_province_add.tga", "gdd_tianxia_province_remove.tga"):
            strip = Image.open(MOD / "gfx/interface" / filename).convert("RGBA")
            w, h = strip.width // 4, strip.height
            require(20 <= x and 328 <= y and 20 + w >= x + 42 and 328 + h >= y + 42,
                    f"{filename} leaves part of {control_name} uncovered")
            for frame in range(4):
                covered = strip.crop((frame * w + x - 20, y - 328,
                                      frame * w + x - 20 + 42, y - 328 + 42))
                require(covered.getchannel("A").getextrema() == (255, 255),
                        f"{filename} frame {frame} leaks {control_name}")
    status_art = status_art.crop((0, 0, 42, 42))
    status_pixels = list(pixels(status_art))
    require(all(alpha == 255 for _, _, _, alpha in status_pixels),
            "member overlay does not fully hide the hard-coded controls below it")
    require(sum(1 for red, green, blue, alpha in status_pixels
                if alpha > 80 and red > 170 and green > 110 and blue < 150) > 40,
            "member emblem has lost its visible gold Zhou glyph")
    require(sum(1 for red, green, blue, alpha in status_pixels
                if alpha > 80 and green > 120 and green > red * 1.3 and green > blue * 1.3) == 0,
            "static member emblem unexpectedly contains an add marker")
    require(sum(1 for red, green, blue, alpha in status_pixels
                if alpha > 80 and red > 120 and red > green * 1.5 and red > blue * 1.5) == 0,
            "static member emblem unexpectedly contains a remove marker")
    for filename in ("gdd_tianxia_province_add.tga", "gdd_tianxia_province_remove.tga"):
        artwork = Image.open(MOD / "gfx/interface" / filename).convert("RGBA")
        require(artwork.size == (216, 42),
                f"{filename} is not a four-state 54px button strip")
        require(all(alpha == 255 for _, _, _, alpha in pixels(artwork)),
                f"{filename} does not hide the hard-coded imperial controls below it")
    add_frame = Image.open(MOD / "gfx/interface/gdd_tianxia_province_add.tga").convert("RGBA").crop((0, 0, 42, 42))
    remove_frame = Image.open(MOD / "gfx/interface/gdd_tianxia_province_remove.tga").convert("RGBA").crop((0, 0, 42, 42))
    require(sum(1 for red, green, blue, alpha in pixels(add_frame)
                if alpha > 80 and green > 120 and green > red * 1.3 and green > blue * 1.3) > 15,
            "admission emblem has lost its native-style green plus")
    require(sum(1 for red, green, blue, alpha in pixels(remove_frame)
                if alpha > 80 and red > 120 and red > green * 1.5 and red > blue * 1.5) > 10,
            "removal emblem has lost its native-style red minus")

    for name in (
        "gdd_leave_tianxia_button",
        "gdd_add_all_tianxia_provinces_button",
        "gdd_dismantle_tianxia_button",
    ):
        require(name in eoc_gui and name in custom_gui,
                f"EoC Tianxia action button is missing or unbound: {name}")
    require('quadTextureSprite = "GFX_gdd_eoc_button_type_1_220"' in eoc_gui,
            "add-all button does not use the approved 220px native-style sprite")

    required_loc_keys = (
        "gdd_tianxia_demand_unlawful_territory_sovereign",
        "gdd_tianxia_demand_unlawful_territory_not_at_war",
        "gdd_tianxia_demand_unlawful_territory_title",
        "gdd_tianxia_demand_unlawful_territory_desc",
        "gdd_tianxia_demand_unlawful_territory_tooltip",
        "gdd_tianxia_demand_unlawful_territory_dialog",
        "gdd_tianxia_demand_unlawful_territory_alert_tooltip",
        "GDD_TIANXIA_DEMAND_UNLAWFUL_TERRITORY",
        "GDD_TIANXIA_PROVINCE_REMOVE_OPTION_TT",
        "GDD_TIANXIA_UNLAWFUL_ACCEPT_TT",
        "GDD_TIANXIA_UNLAWFUL_REFUSE_TT",
        "GDD_TIANXIA_UNLAWFUL_REFUSAL_CONFIRM_TT",
        "gdd_tianxia_territory.10.t",
        "gdd_tianxia_territory.11.t",
        "gdd_tianxia_territory.13.t",
        "gdd_cb_tianxia_liberation",
        "GDD_TIANXIA_LIBERATION_WAR_NAME",
    )
    for key in required_loc_keys:
        require(re.search(rf"(?m)^\s*{re.escape(key)}:0\s+", loc) is not None,
                f"missing readable localisation: {key}")
    require("周天下地块不能同时属于神圣罗马帝国" not in loc,
            "obsolete HRE/Tianxia coexistence sentence remains in the province status tooltip")
    event_descriptions = re.findall(
        r'(?m)^\s*gdd_tianxia_territory\.\d+\.d:0\s+"(.*)"$', loc
    )
    require(event_descriptions and all(re.search(r"[0-9]", desc) is None
                                       for desc in event_descriptions),
            "a Tianxia territory event narrative still exposes numeric mechanics")
    for method in (
        "GetGddTianxiaUnlawfulOutcome",
        "GetGddTianxiaUnlawfulSubjectReason",
        "GetGddTianxiaUnlawfulStrengthReason",
        "GetGddTianxiaUnlawfulOpinionReason",
        "GetGddTianxiaUnlawfulTrustReason",
        "GetGddTianxiaUnlawfulAllianceReason",
        "GetGddTianxiaUnlawfulHostilityReason",
        "GetGddTianxiaUnlawfulDipRepReason",
    ):
        require(f"name = {method}" in custom_loc,
                f"missing visible AI acceptance reason method: {method}")

    print("PASS: Zhou Tianxia territory white-box validation")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Static contract for the first Zhou diplomacy foundation."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"

PATHS = {
    "cb_types": MOD / "common/cb_types/zhx_diplomacy_cb_types.txt",
    "diplomatic_actions": MOD / "common/new_diplomatic_actions/zhx_diplomacy_actions.txt",
    "triggers": MOD / "common/scripted_triggers/zhx_diplomacy_triggers.txt",
    "effects": MOD / "common/scripted_effects/zhx_diplomacy_effects.txt",
    "events": MOD / "events/zhx_diplomacy_events.txt",
    "on_actions": MOD / "common/on_actions/zhx_diplomacy_on_actions.txt",
    "event_modifiers": MOD / "common/event_modifiers/zhx_diplomacy_modifiers.txt",
    "opinions": MOD / "common/opinion_modifiers/zhx_diplomacy_opinions.txt",
    "decisions": MOD / "decisions/zhx_diplomacy_decisions.txt",
    "system_events": MOD / "events/zhx_system_events.txt",
    "system_on_actions": MOD / "common/on_actions/zhx_system_on_actions.txt",
    "ritual_modifiers": MOD / "common/event_modifiers/zhx_system_modifiers.txt",
    "system_effects": MOD / "common/scripted_effects/zhx_system_effects.txt",
    "loc_source": MOD / "localisation_source/zhx_diplomacy_readable_utf8.txt",
    "loc_encoded": MOD / "localisation/zhx_diplomacy_l_english.yml",
    "encoder": ROOT / "tools/encode_eu4_chinese_localisation.py",
    "docs": ROOT / "docs/gameplay/09_zhou_diplomacy.md",
}


def fail(message: str) -> None:
    raise AssertionError(message)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def masked_clausewitz(text: str) -> str:
    output: list[str] = []
    quote = False
    escaped = False
    comment = False
    for char in text:
        if comment:
            output.append("\n" if char == "\n" else " ")
            if char == "\n":
                comment = False
            continue
        if quote:
            output.append(" ")
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quote = False
            continue
        if char == "#":
            comment = True
            output.append(" ")
        elif char == '"':
            quote = True
            output.append(" ")
        else:
            output.append(char)
    require(not quote, "unterminated quoted string")
    return "".join(output)


def validate_braces(path: Path, text: str) -> None:
    depth = 0
    for char in masked_clausewitz(text):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            require(depth >= 0, f"{path.name}: closing brace without opener")
    require(depth == 0, f"{path.name}: unbalanced braces ({depth})")


def block(text: str, key: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*\{{", text)
    require(match is not None, f"missing block {key}")
    opening = text.find("{", match.start())
    depth = 0
    quote = False
    escaped = False
    comment = False
    for index in range(opening, len(text)):
        char = text[index]
        if comment:
            if char == "\n":
                comment = False
            continue
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quote = False
            continue
        if char == "#":
            comment = True
        elif char == '"':
            quote = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[match.start() : index + 1]
    fail(f"block {key} has no closing brace")


def tags_in(block_text: str) -> set[str]:
    return set(re.findall(r"\btag\s*=\s*([A-Z0-9]{3})\b", block_text))


def event_block(text: str, event_id: str) -> str:
    marker = f"id = {event_id}"
    marker_position = text.find(marker)
    require(marker_position >= 0, f"missing event {event_id}")
    start = text.rfind("country_event = {", 0, marker_position)
    require(start >= 0, f"event {event_id} has no country_event opener")
    opening = text.find("{", start)
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    fail(f"event {event_id} has no closing brace")


def validate() -> None:
    for label, path in PATHS.items():
        require(path.exists(), f"missing {label}: {path.relative_to(ROOT)}")

    texts = {label: path.read_text(encoding="utf-8", errors="strict") for label, path in PATHS.items()}
    for label in (
        "cb_types",
        "diplomatic_actions",
        "triggers",
        "effects",
        "events",
        "on_actions",
        "event_modifiers",
        "opinions",
        "decisions",
        "system_events",
        "system_on_actions",
        "ritual_modifiers",
    ):
        validate_braces(PATHS[label], texts[label])

    effects = texts["effects"]
    for effect in ("zhx_diplomacy_queue_illegal_cession", "zhx_diplomacy_queue_member_extinction"):
        body = block(effects, effect)
        require("country_event" not in body, f"{effect} must not fire an event inside SetOwner/on_annexed")
        require("every_country" not in body, f"{effect} must not scan countries inside SetOwner/on_annexed")
        require("add_aggressive_expansion" not in body, f"{effect} must not apply AE inside SetOwner/on_annexed")
        require("add_casus_belli" not in body, f"{effect} must not grant a CB inside SetOwner/on_annexed")
        require("reverse_add_casus_belli" not in body, f"{effect} must not grant a reverse CB inside SetOwner/on_annexed")
    cession_queue = block(effects, "zhx_diplomacy_queue_illegal_cession")
    require("change_variable" not in cession_queue, "province owner change must remain a boolean-only transaction marker")
    extinction_queue = block(effects, "zhx_diplomacy_queue_member_extinction")
    require("zhx_diplomacy_extinction_ae_queued" in extinction_queue, "annexation must set its independent extinction-AE queue")
    require("zhx_diplomacy_member_extinction_count" in extinction_queue and "value = 1" in extinction_queue, "annexation must count each member extinction")
    settle = block(effects, "zhx_diplomacy_settle_illegal_cession")
    require("duration = 3650" in settle, "covenant breaker must last ten years")
    require("value = -3" in settle, "Tianzi illegal cession must reduce ritual authority by 3")
    require("save_event_target_as = zhx_diplomacy_offender" not in settle, "monthly settlement must not rely on a transient event target")
    require("add_opinion" not in settle and "reverse_add_opinion" not in settle, "raw monthly settlement must not perform cross-country opinion effects")
    require("add_casus_belli" not in settle, "monthly settlement must not grant a dynamic CB")
    require("reverse_add_casus_belli" not in settle, "monthly settlement must not grant a reverse dynamic CB")
    require("add_aggressive_expansion" not in settle, "ordinary province cessions must not add scripted AE")
    require("zhx_diplomacy_member_extinction_count" not in settle, "illegal-cession settlement must not consume the independent extinction queue")
    require("country_event" not in settle, "illegal cession settlement must not create a cession receipt event")
    extinction_ae = block(effects, "zhx_diplomacy_settle_extinction_ae")
    require(
        re.search(r"add_aggressive_expansion\s*=\s*\{[^}]*value\s*=\s*5\b[^}]*apply_calc\s*=\s*no", extinction_ae, re.S)
        is not None,
        "member extinction must retain only its fixed five-point AE surcharge",
    )
    require(extinction_ae.count("add_aggressive_expansion") == 1, "extinction settlement must apply exactly one fixed AE effect")
    require("zhx_diplomacy_member_extinction_count" in extinction_ae and "while =" in extinction_ae, "five-point AE must consume each queued member extinction")
    require("NOT = { is_subject_of = ROOT }" in extinction_ae, "responsibility holder's subjects must not receive AE against their overlord")
    require("clr_country_flag = zhx_diplomacy_extinction_ae_queued" in extinction_ae, "extinction-AE settlement must clear its independent queue")
    ritual_loss = block(effects, "zhx_diplomacy_settle_extinction_ritual_loss")
    require("zhx_tianxia_extinction_penalty_count" in ritual_loss, "extinction ritual loss must consume the global count")
    require("value = -5" in ritual_loss, "every extinguished member must cost five ritual authority")
    require("while =" in ritual_loss and "zhx_refresh_ritual_order = yes" in ritual_loss, "extinction losses must settle and refresh safely")
    require("zhx_diplomacy_refresh_relief_casus_belli" not in effects, "retired relief-CB scan must stay removed")

    cb_types = texts["cb_types"]
    punitive_cb = block(cb_types, "zhx_cb_punish_covenant_breaker")
    for token in (
        "valid_for_subject = no",
        "is_triggered_only = yes",
        "months = 120",
        "war_goal = superiority_insult",
    ):
        require(token in punitive_cb, f"punitive CB missing safe standalone setting: {token}")
    require(punitive_cb.count("war_goal") == 1, "punitive CB must reuse exactly one vanilla wargoal")
    for forbidden in (
        "can_use =",
        "allowed_provinces =",
        "allowed_states =",
        "allowed_subcontinents =",
        "all_provinces =",
        "every_country",
        "zhx_restore_covenant_wargoal",
        "zhx_relieve_member_wargoal",
        "zhx_cb_relieve_tianxia_member",
    ):
        require(forbidden not in punitive_cb, f"punitive CB must remain a trigger-only vanilla-wargoal layer: {forbidden}")

    diplomatic_actions = texts["diplomatic_actions"]
    relief_action = block(diplomatic_actions, "zhx_relieve_tianxia_member")
    masked_relief_action = masked_clausewitz(relief_action)
    require("category = influence" in relief_action, "relief action must use the native influence category")
    require("require_acceptance = no" in relief_action, "relief action must join immediately without recipient acceptance")

    relief_visible = block(relief_action, "is_visible")
    masked_relief_visible = masked_clausewitz(relief_visible)
    require("zhx_is_tianzi = yes" in relief_visible, "only the Tianzi may see the relief action")
    require(
        re.search(
            r"FROM\s*=\s*\{[^{}]*"
            r"exists\s*=\s*yes[^{}]*"
            r"is_subject\s*=\s*no[^{}]*"
            r"zhx_is_tianxia_polity\s*=\s*yes[^{}]*"
            r"NOT\s*=\s*\{\s*zhx_is_tianzi\s*=\s*yes\s*\}",
            masked_relief_visible,
            re.S,
        )
        is not None,
        "relief target must be an existing independent ordinary Zhou member",
    )
    require(
        re.search(
            r"any_war_enemy_country\s*=\s*\{[^{}]*"
            r"exists\s*=\s*yes[^{}]*"
            r"NOT\s*=\s*\{\s*zhx_is_tianxia_polity\s*=\s*yes\s*\}[^{}]*"
            r"offensive_war_with\s*=\s*PREV[^{}]*"
            r"is_in_war\s*=\s*\{[^{}]*"
            r"attacker_leader\s*=\s*THIS[^{}]*"
            r"defender_leader\s*=\s*PREV[^{}]*\}",
            masked_relief_visible,
            re.S,
        )
        is not None,
        "relief action must require an external war leader directly attacking the member as defender leader",
    )

    relief_allowed = block(relief_action, "is_allowed")
    masked_relief_allowed = masked_clausewitz(relief_allowed)
    for token, message in (
        ("tooltip = zhx_relieve_tianxia_member_requires_peace_tt", "relief action must explain the Tianzi peace requirement"),
        ("is_at_war = no", "the Tianzi must be at peace before joining a member's defensive war"),
        ("tooltip = zhx_relieve_tianxia_member_not_enemy_tt", "relief action must explain the direct-war exclusion"),
        ("NOT = { war_with = FROM }", "the Tianzi must not already be at war with the relief target"),
        ("tooltip = zhx_relieve_tianxia_member_no_internal_war_tt", "relief action must explain the mixed internal-war exclusion"),
        ("tooltip = zhx_relieve_tianxia_member_no_allied_attacker_tt", "relief action must explain attacker-side diplomatic conflicts"),
        ("alliance_with = ROOT", "the Tianzi must not be allied with an attacking participant"),
        ("is_subject_of = ROOT", "the Tianzi must not be overlord of an attacking participant"),
    ):
        require(token in relief_allowed, message)
    require(
        re.search(
            r"NOT\s*=\s*\{\s*any_war_enemy_country\s*=\s*\{[^{}]*"
            r"zhx_is_tianxia_polity\s*=\s*yes[^{}]*"
            r"offensive_war_with\s*=\s*PREV[^{}]*\}\s*\}",
            masked_relief_allowed,
            re.S,
        )
        is not None,
        "relief action must reject a member whose defensive wars include a Zhou attacker",
    )
    require(
        re.search(
            r"NOT\s*=\s*\{\s*any_war_enemy_country\s*=\s*\{[^{}]*"
            r"offensive_war_with\s*=\s*PREV[^{}]*"
            r"OR\s*=\s*\{[^{}]*"
            r"alliance_with\s*=\s*ROOT[^{}]*"
            r"is_subject_of\s*=\s*ROOT[^{}]*\}\s*\}\s*\}",
            masked_relief_allowed,
            re.S,
        )
        is not None,
        "relief action must reject attacking participants allied to or subject to the Tianzi",
    )

    relief_accept = block(relief_action, "on_accept")
    require(
        re.fullmatch(
            r"\s*on_accept\s*=\s*\{\s*join_all_defensive_wars_of\s*=\s*FROM\s*\}\s*",
            masked_clausewitz(relief_accept),
            re.S,
        )
        is not None,
        "relief action acceptance must consist solely of joining FROM's defensive wars",
    )
    require(masked_relief_action.count("join_all_defensive_wars_of") == 1, "relief action must join defensive wars exactly once")
    relief_ai = block(relief_action, "ai_will_do")
    require(
        re.fullmatch(r"\s*ai_will_do\s*=\s*\{\s*always\s*=\s*no\s*\}\s*", masked_clausewitz(relief_ai), re.S)
        is not None,
        "first relief-action iteration must keep AI initiation disabled",
    )
    for forbidden in (
        "casus_belli",
        "add_casus_belli",
        "reverse_add_casus_belli",
        "declare_war",
        "every_country",
        "country_event",
        "province_event",
        "on_war_started",
        "zhx_cb_relieve_tianxia_member",
        "zhx_relieve_member_wargoal",
    ):
        require(forbidden not in relief_action, f"relief action must remain a direct native war-join action: {forbidden}")

    appeal_action = block(diplomatic_actions, "zhx_appeal_to_tianzi_for_relief")
    masked_appeal_action = masked_clausewitz(appeal_action)
    for token, message in (
        ("category = influence", "relief appeal must use the native influence category"),
        ("alert_index = 10", "relief appeal must reuse the native call-to-arms message icon"),
        (
            "alert_tooltip = zhx_appeal_to_tianzi_for_relief_alert_tooltip",
            "relief appeal must provide a recipient alert tooltip",
        ),
        ("require_acceptance = yes", "the Tianzi must be allowed to accept or decline a relief appeal"),
    ):
        require(token in appeal_action, message)

    appeal_visible = block(appeal_action, "is_visible")
    masked_appeal_visible = masked_clausewitz(appeal_visible)
    for token, message in (
        ("has_global_flag = zhx_system_initialised_v14", "relief appeal must require the active diplomacy system"),
        ("is_subject = no", "relief appeal actor must be independent"),
        ("zhx_is_tianxia_member = yes", "only an ordinary Zhou member may appeal for relief"),
        ("NOT = { zhx_is_tianzi = yes }", "the Tianzi must not appeal to itself"),
        ("is_at_war = yes", "relief appeal actor must currently be at war"),
    ):
        require(token in appeal_visible, message)
    require(
        re.search(
            r"FROM\s*=\s*\{[^{}]*"
            r"exists\s*=\s*yes[^{}]*"
            r"is_subject\s*=\s*no[^{}]*"
            r"zhx_is_tianzi\s*=\s*yes[^{}]*\}",
            masked_appeal_visible,
            re.S,
        )
        is not None,
        "relief appeal recipient must be the existing independent Tianzi",
    )
    require(
        re.search(
            r"any_war_enemy_country\s*=\s*\{[^{}]*"
            r"exists\s*=\s*yes[^{}]*"
            r"NOT\s*=\s*\{\s*zhx_is_tianxia_polity\s*=\s*yes\s*\}[^{}]*"
            r"offensive_war_with\s*=\s*ROOT[^{}]*"
            r"is_in_war\s*=\s*\{[^{}]*"
            r"attacker_leader\s*=\s*THIS[^{}]*"
            r"defender_leader\s*=\s*ROOT[^{}]*\}",
            masked_appeal_visible,
            re.S,
        )
        is not None,
        "relief appeal must require an external war leader directly attacking actor ROOT as defender leader",
    )
    require(
        re.search(
            r"NOT\s*=\s*\{\s*is_in_war\s*=\s*\{[^{}]*"
            r"defenders\s*=\s*FROM[^{}]*defender_leader\s*=\s*THIS[^{}]*\}\s*\}",
            masked_appeal_visible,
            re.S,
        )
        is not None,
        "relief appeal must disappear after the Tianzi has joined the member's defensive side",
    )

    appeal_allowed = block(appeal_action, "is_allowed")
    masked_appeal_allowed = masked_clausewitz(appeal_allowed)
    for token, message in (
        (
            "tooltip = zhx_appeal_to_tianzi_for_relief_tianzi_at_war_tt",
            "relief appeal must explain why a warring Tianzi cannot answer",
        ),
        ("FROM = { is_at_war = no }", "relief appeal must require the Tianzi to be at peace"),
        (
            "tooltip = zhx_appeal_to_tianzi_for_relief_not_enemy_tt",
            "relief appeal must explain the direct-war exclusion",
        ),
        ("NOT = { war_with = FROM }", "the appealing member must not be at war with the Tianzi"),
        (
            "tooltip = zhx_appeal_to_tianzi_for_relief_no_internal_war_tt",
            "relief appeal must explain the mixed internal-war exclusion",
        ),
        (
            "tooltip = zhx_appeal_to_tianzi_for_relief_no_allied_attacker_tt",
            "relief appeal must explain attacker-side diplomatic conflicts",
        ),
        ("alliance_with = FROM", "an attacking participant must not be allied to the Tianzi"),
        ("is_subject_of = FROM", "an attacking participant must not be subject to the Tianzi"),
    ):
        require(token in appeal_allowed, message)
    require(
        re.search(
            r"NOT\s*=\s*\{\s*any_war_enemy_country\s*=\s*\{[^{}]*"
            r"zhx_is_tianxia_polity\s*=\s*yes[^{}]*"
            r"offensive_war_with\s*=\s*ROOT[^{}]*\}\s*\}",
            masked_appeal_allowed,
            re.S,
        )
        is not None,
        "relief appeal must reject a member whose defensive wars include a Zhou attacker",
    )
    require(
        re.search(
            r"NOT\s*=\s*\{\s*any_war_enemy_country\s*=\s*\{[^{}]*"
            r"offensive_war_with\s*=\s*ROOT[^{}]*"
            r"OR\s*=\s*\{[^{}]*"
            r"alliance_with\s*=\s*FROM[^{}]*"
            r"is_subject_of\s*=\s*FROM[^{}]*\}\s*\}\s*\}",
            masked_appeal_allowed,
            re.S,
        )
        is not None,
        "relief appeal must reject attacking participants allied to or subject to the Tianzi",
    )

    appeal_accept = block(appeal_action, "on_accept")
    for token, message in (
        ("if =", "accepted relief appeal must revalidate its delayed request"),
        ("has_global_flag = zhx_system_initialised_v14", "delayed relief acceptance must require the live system"),
        ("zhx_is_tianxia_member = yes", "delayed relief acceptance must revalidate the appealing member"),
        ("NOT = { zhx_is_tianzi = yes }", "delayed relief acceptance must reject a former member who became Tianzi"),
        ("NOT = { war_with = FROM }", "delayed relief acceptance must recheck direct war with the Tianzi"),
        ("zhx_is_tianzi = yes", "delayed relief acceptance must revalidate the recipient as current Tianzi"),
        ("is_at_war = no", "delayed relief acceptance must revalidate Tianzi peace"),
        ("offensive_war_with = ROOT", "delayed relief acceptance must revalidate an offensive enemy"),
        ("attacker_leader = THIS", "delayed relief acceptance must revalidate the attacking war leader"),
        ("defender_leader = ROOT", "delayed relief acceptance must revalidate the member as defender leader"),
        ("alliance_with = FROM", "delayed relief acceptance must recheck Tianzi alliances on the attacking side"),
        ("is_subject_of = FROM", "delayed relief acceptance must recheck Tianzi subjects on the attacking side"),
        ("defenders = FROM", "delayed relief acceptance must reject duplicate Tianzi participation"),
        ("join_all_defensive_wars_of = ROOT", "accepted relief appeal must join ROOT's current defensive wars"),
    ):
        require(token in appeal_accept, message)
    require(appeal_accept.count("zhx_is_tianxia_polity = yes") >= 2, "delayed relief acceptance must recheck external and internal attackers")
    require(appeal_accept.count("any_war_enemy_country") >= 3, "delayed relief acceptance must recheck direct, internal and allied attackers")
    require(masked_appeal_action.count("join_all_defensive_wars_of") == 1, "relief appeal must join defensive wars exactly once")
    appeal_decline = block(appeal_action, "on_decline")
    require(
        re.fullmatch(r"\s*on_decline\s*=\s*\{\s*\}\s*", masked_clausewitz(appeal_decline), re.S) is not None,
        "declining a relief appeal must have no scripted side effects",
    )
    appeal_ai_sender = block(appeal_action, "ai_will_do")
    require(
        re.fullmatch(r"\s*ai_will_do\s*=\s*\{\s*always\s*=\s*no\s*\}\s*", masked_clausewitz(appeal_ai_sender), re.S)
        is not None,
        "AI Zhou members must not proactively spam relief appeals",
    )
    appeal_ai_acceptance = block(appeal_action, "ai_acceptance")
    for token in (
        "name = zhx_appeal_to_tianzi_for_relief_duty_ai",
        "variable_name = ai_value",
        "value = 1",
        "which = ai_value",
        "value = 100",
    ):
        require(token in appeal_ai_acceptance, f"AI Tianzi relief acceptance missing deterministic duty term: {token}")
    require(appeal_ai_acceptance.count("add_entry") == 1, "AI Tianzi relief acceptance must remain one predictable duty entry")
    for forbidden in (
        "casus_belli",
        "add_casus_belli",
        "reverse_add_casus_belli",
        "declare_war",
        "every_country",
        "country_event",
        "province_event",
        "on_war_started",
        "add_opinion",
        "add_country_modifier",
    ):
        require(forbidden not in appeal_action, f"relief appeal must remain a direct native request with no side channel: {forbidden}")
    runtime_relief_bridges = "\n".join((effects, texts["events"], texts["on_actions"]))
    require(
        "zhx_appeal_to_tianzi_for_relief" not in runtime_relief_bridges,
        "relief appeal must not acquire an event, on-action, effect, scan or queue bridge",
    )

    on_actions = texts["on_actions"]
    owner_change = block(on_actions, "on_province_owner_change")
    require("war_with = FROM" in owner_change, "illegal acquisition must require an active war")
    require("NOT = { is_core = owner }" in owner_change, "new-owner core whitelist missing")
    require("zhx_diplomacy_lawful_transfer" in owner_change, "explicit lawful scripted-transfer escape hatch missing")
    require("is_subject = yes" in owner_change and "overlord =" in owner_change, "subject feeding must route responsibility to overlord")
    require("zhx_diplomacy_queue_illegal_cession = yes" in owner_change, "owner change missing boolean covenant-breach marker")
    require("country_event" not in owner_change, "owner change must never queue an event from SetOwner")
    require("every_country" not in owner_change, "owner change must never scan countries from SetOwner")
    require("development =" not in owner_change, "owner change must not retain province development tiers")
    require("add_aggressive_expansion" not in owner_change, "owner change must not add per-province AE")
    require("change_variable" not in owner_change, "owner change must not maintain a per-province ledger")
    require("add_casus_belli" not in owner_change, "owner change must not grant a CB")
    require("reverse_add_casus_belli" not in owner_change, "owner change must not grant a reverse CB")
    for peace_hook in ("on_peace_actor", "on_peace_recipient"):
        peace_body = block(on_actions, peace_hook)
        for token in (
            "ai = no",
            "has_country_flag = zhx_diplomacy_illegal_cession_queued",
            "NOT = { has_country_flag = zhx_diplomacy_illegal_notice_shown }",
            "set_country_flag = zhx_diplomacy_illegal_notice_shown",
            "country_event = { id = zhx_diplomacy.10 }",
        ):
            require(token in peace_body, f"{peace_hook} missing same-day human notification guard: {token}")
        for forbidden in (
            "add_aggressive_expansion",
            "add_casus_belli",
            "reverse_add_casus_belli",
            "add_opinion",
            "change_variable",
            "every_country",
            "zhx_diplomacy_settle_illegal_cession",
        ):
            require(forbidden not in peace_body, f"{peace_hook} must remain presentation-only: {forbidden}")
    diplomacy_monthly = block(on_actions, "on_monthly_pulse")
    require("country_event = { id = zhx_diplomacy.11 }" in diplomacy_monthly, "monthly pulse must enter the hidden country-event opinion bridge")
    require("country_event = { id = zhx_diplomacy.12 }" in diplomacy_monthly, "monthly pulse must enter the isolated punitive-CB bridge")
    require("zhx_diplomacy_settle_illegal_cession = yes" in diplomacy_monthly, "monthly pulse must settle covenant breaches outside the peace stack")
    require("zhx_diplomacy_settle_extinction_ae = yes" in diplomacy_monthly, "monthly pulse must settle the independent extinction-AE queue")
    require("zhx_diplomacy_settle_extinction_ritual_loss = yes" in diplomacy_monthly, "Tianzi monthly pulse must settle extinction ritual losses")
    require("refresh_relief" not in diplomacy_monthly, "monthly pulse must not retain a relief-CB world scan")
    require("on_country_released" in on_actions, "missing historic restoration hook")
    system_annexed = block(texts["system_on_actions"], "on_annexed")
    require(
        system_annexed.find("zhx_diplomacy_queue_member_extinction = yes") < system_annexed.find("zhx_queue_tianxia_member_removal = yes"),
        "member extinction must be priced before membership removal",
    )
    require("zhx_diplomacy_queue_member_extinction = yes" in system_annexed, "every member extinction must queue its fixed five-point AE surcharge")
    require("has_country_flag = zhx_diplomacy_illegal_cession_queued" not in system_annexed, "extinction AE must not depend on the final province-transfer callback order")
    require("id = zhx_diplomacy.4" not in system_annexed, "annexation must not schedule a stale-scope event")
    require("country_event" not in system_annexed, "annexation callback must not fire or schedule country events")
    require("zhx_remove_tianxia_member = yes" not in system_annexed, "annexation callback must defer global membership rebuilding")
    require("zhx_tianxia_extinction_penalty_count" in system_annexed, "annexation must queue the universal five-point ritual loss")
    require("zhx_tianxia_extinction_penalty_recorded" in system_annexed, "annexation ritual loss must be idempotent")
    system_integrate = block(texts["system_on_actions"], "on_integrate")
    require("zhx_tianxia_extinction_penalty_count" in system_integrate, "diplomatic integration must also queue the universal ritual loss")
    require("zhx_tianxia_extinction_penalty_recorded" in system_integrate, "integration ritual loss must be idempotent")
    system_diplomatic_annex = block(texts["system_on_actions"], "on_diplomatic_annex")
    require("zhx_tianxia_extinction_penalty_count" in system_diplomatic_annex, "ordinary vassal annexation must also queue the universal ritual loss")
    require("zhx_tianxia_extinction_penalty_recorded" in system_diplomatic_annex, "vassal annexation ritual loss must be idempotent")
    require("zhx_queue_tianxia_member_removal = yes" in system_diplomatic_annex, "vassal annexation must defer removal of the extinguished member")
    queued_removal = block(texts["system_effects"], "zhx_queue_tianxia_member_removal")
    require("every_country" not in queued_removal and "country_event" not in queued_removal, "transaction-safe member removal must remain local")
    require("set_country_flag = zhx_tianxia_membership_dirty" in queued_removal, "transaction-safe member removal must dirty the CZH caches")
    reconcile = block(texts["system_effects"], "zhx_reconcile_tianxia_membership_after_transfer")
    for effect in (
        "zhx_rebuild_tianxia_member_cache",
        "zhx_rebuild_six_great_feudatory_cache",
        "zhx_build_gui_roster",
        "gdd_recalculate_all_reform_votes_effect",
    ):
        require(effect in reconcile, f"deferred membership reconciliation missing {effect}")
    system_monthly = block(texts["system_on_actions"], "on_monthly_pulse")
    require("zhx_reconcile_tianxia_membership_after_transfer = yes" in system_monthly, "monthly pulse must consume membership dirty state")
    clear_batch = block(effects, "zhx_diplomacy_clear_illegal_batch")
    require(
        "clr_country_flag = zhx_diplomacy_illegal_cession_queued" in clear_batch,
        "batch cleanup must clear the owner-change queue marker",
    )
    event_text = texts["events"]
    for event_id in (10, 11, 12, 30):
        require(re.search(rf"\bid\s*=\s*zhx_diplomacy\.{event_id}\b", event_text) is not None, f"missing diplomacy event {event_id}")
    for event_id in (1, 2, 3, 4, 20, 99):
        require(re.search(rf"\bid\s*=\s*zhx_diplomacy\.{event_id}\b", event_text) is None, f"obsolete delayed event {event_id} must be removed")
    peace_notice = event_block(event_text, "zhx_diplomacy.10")
    for field in (
        "title = zhx_diplomacy.10.t",
        "desc = zhx_diplomacy.10.d",
        "picture = DIPLOMACY_eventPicture",
        "is_triggered_only = yes",
        "name = zhx_diplomacy.10.a",
    ):
        require(field in peace_notice, f"same-day peace notice missing presentation field: {field}")
    for forbidden in (
        "immediate =",
        "hidden_effect =",
        "add_aggressive_expansion",
        "add_casus_belli",
        "add_opinion",
        "change_variable",
        "every_country",
        "set_country_flag",
        "add_country_modifier",
    ):
        require(forbidden not in peace_notice, f"same-day peace notice must remain effect-free: {forbidden}")
    opinion_bridge = event_block(event_text, "zhx_diplomacy.11")
    require("hidden = yes" in opinion_bridge, "opinion bridge must remain invisible")
    require("has_saved_global_event_target = zhx_tianzi" in opinion_bridge, "opinion bridge must use the authoritative Tianzi target")
    require("event_target:zhx_tianzi" in opinion_bridge and "who = ROOT" in opinion_bridge, "opinion bridge must make the Tianzi judge the offending event root")
    require("modifier = zhx_opinion_covenant_breaker" in opinion_bridge, "opinion bridge is missing the covenant-breaker penalty")
    require("add_casus_belli" not in opinion_bridge, "opinion bridge must remain isolated from the punitive-CB grant")
    cb_bridge = event_block(event_text, "zhx_diplomacy.12")
    require("hidden = yes" in cb_bridge, "punitive-CB bridge must remain invisible")
    require("NOT = { zhx_is_tianzi = yes }" in cb_bridge, "Tianzi must never receive a punitive CB against itself")
    require("has_saved_global_event_target = zhx_tianzi" in cb_bridge, "punitive-CB bridge must use the authoritative Tianzi target")
    require(cb_bridge.count("add_casus_belli") == 1, "punitive-CB bridge must grant exactly one CB")
    masked_cb_bridge = masked_clausewitz(cb_bridge)
    require(
        re.search(
            r"event_target:zhx_tianzi\s*=\s*\{\s*"
            r"add_casus_belli\s*=\s*\{[^{}]*"
            r"target\s*=\s*ROOT\b[^{}]*"
            r"type\s*=\s*zhx_cb_punish_covenant_breaker\b[^{}]*"
            r"months\s*=\s*120\b[^{}]*\}\s*\}",
            masked_cb_bridge,
            re.S,
        )
        is not None,
        "punitive CB must be granted by event-target Tianzi against offender ROOT for 120 months",
    )
    for forbidden in ("every_country", "reverse_add_casus_belli"):
        require(forbidden not in cb_bridge, f"punitive-CB bridge must not use {forbidden}")
    admission = event_block(event_text, "zhx_diplomacy.30")
    require("zhx_diplomacy.30.a" in admission and "zhx_diplomacy.30.b" in admission, "Tianzi admission must be accept/reject only")

    retired_wargoal = MOD / "common/wargoal_types/zhx_diplomacy_wargoal_types.txt"
    require(not retired_wargoal.exists(), f"retired custom-wargoal file returned: {retired_wargoal.relative_to(ROOT)}")
    runtime_diplomacy = "\n".join((cb_types, diplomatic_actions, effects, event_text, on_actions))
    for forbidden in (
        "reverse_add_casus_belli",
        "zhx_cb_relieve_tianxia_member",
        "zhx_restore_covenant_wargoal",
        "zhx_relieve_member_wargoal",
    ):
        require(forbidden not in runtime_diplomacy, f"retired dynamic-CB runtime token returned: {forbidden}")

    decisions = texts["decisions"]
    apply_decision = block(decisions, "zhx_apply_to_join_tianxia")
    require("zhx_can_apply_for_tianxia_membership = yes" in apply_decision, "membership application must use common eligibility trigger")
    require("factor = 0.01" in apply_decision, "AI membership application must remain low-frequency")
    leave_decision = block(decisions, "zhx_leave_tianxia")
    require("add_prestige = -25" in leave_decision, "leaving must cost 25 prestige")
    require("duration = 7300" in leave_decision, "rejoin bar must last twenty years")
    require("zhx_remove_tianxia_member = yes" in leave_decision, "leaving must use authoritative member removal")
    require("zhx_ritual_tier_collapsed" in leave_decision, "AI exit must require collapsed order")

    triggers = texts["triggers"]
    eligibility = block(triggers, "zhx_can_apply_for_tianxia_membership")
    for token in (
        "is_subject = no",
        "value = 150",
        "superregion = china_superregion",
        "any_neighbor_country",
        "war_with = ROOT",
        "zhx_covenant_breaker",
    ):
        require(token in eligibility, f"membership eligibility missing {token}")
    historic = tags_in(block(triggers, "zhx_is_historic_tianxia_tag"))
    initial = tags_in(block(texts["system_effects"], "zhx_initialise_tianxia_system"))
    require(historic == initial, f"historic member catalogue drift: missing={sorted(initial-historic)}, extra={sorted(historic-initial)}")

    require("zhx_system_initialised_v14" in texts["system_events"], "startup event must gate diplomacy v14")
    require("zhx_migrate_tianxia_system_v13_to_v14 = yes" in texts["system_events"], "startup event must invoke v14 migration")
    require("set_global_flag = zhx_system_initialised_v14" in effects, "v14 migration must set global flag")
    require("ae_impact" not in block(texts["ritual_modifiers"], "zhx_ritual_order_ordered"), "ordered ritual tier still modifies global AE")
    require("ae_impact" not in block(texts["ritual_modifiers"], "zhx_ritual_order_stable"), "stable ritual tier still modifies global AE")
    require("ae_impact" not in block(texts["ritual_modifiers"], "zhx_ritual_order_balanced"), "balanced ritual tier still modifies global AE")

    required_loc = (
        "zhx_covenant_breaker",
        "zhx_cb_punish_covenant_breaker",
        "zhx_cb_punish_covenant_breaker_desc",
        "zhx_relieve_tianxia_member",
        "zhx_relieve_tianxia_member_title",
        "zhx_relieve_tianxia_member_desc",
        "zhx_relieve_tianxia_member_tooltip",
        "zhx_relieve_tianxia_member_requires_peace_tt",
        "zhx_relieve_tianxia_member_not_enemy_tt",
        "zhx_relieve_tianxia_member_no_internal_war_tt",
        "zhx_relieve_tianxia_member_no_allied_attacker_tt",
        "zhx_appeal_to_tianzi_for_relief",
        "zhx_appeal_to_tianzi_for_relief_title",
        "zhx_appeal_to_tianzi_for_relief_desc",
        "zhx_appeal_to_tianzi_for_relief_tooltip",
        "zhx_appeal_to_tianzi_for_relief_alert_tooltip",
        "zhx_appeal_to_tianzi_for_relief_dialog",
        "zhx_appeal_to_tianzi_for_relief_tianzi_at_war_tt",
        "zhx_appeal_to_tianzi_for_relief_not_enemy_tt",
        "zhx_appeal_to_tianzi_for_relief_no_internal_war_tt",
        "zhx_appeal_to_tianzi_for_relief_no_allied_attacker_tt",
        "zhx_appeal_to_tianzi_for_relief_duty_ai",
        "zhx_diplomacy.10.d",
        "zhx_diplomacy.30.d",
        "zhx_apply_to_join_tianxia_title",
        "zhx_leave_tianxia_title",
    )
    for key in required_loc:
        require(re.search(rf"(?m)^\s*{re.escape(key)}:0\s", texts["loc_source"]) is not None, f"readable localisation missing {key}")
        require(re.search(rf"(?m)^\s*{re.escape(key)}:0\s", texts["loc_encoded"]) is not None, f"encoded localisation missing {key}")
    for retired_key in (
        "zhx_cb_relieve_tianxia_member",
        "zhx_restore_covenant_wargoal",
        "zhx_relieve_member_wargoal",
    ):
        require(retired_key not in texts["loc_source"], f"readable localisation retained retired key {retired_key}")
        require(retired_key not in texts["loc_encoded"], f"encoded localisation retained retired key {retired_key}")
    require("zhx_diplomacy_readable_utf8.txt" in texts["encoder"], "diplomacy localisation missing from encoder manifest")


def main() -> int:
    try:
        validate()
    except (AssertionError, UnicodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("PASS: Zhou diplomacy static contract")
    print("  ordinary province cessions add no scripted AE; member extinction: +5")
    print("  every member extinction queues a universal -5 ritual-authority loss")
    print("  real peace uses a same-day presentation-only notice; punishments settle monthly")
    print("  Tianzi receives an isolated 120-month punitive CB through a hidden monthly bridge")
    print("  Tianzi may manually join an externally attacked member's defensive wars through a native diplomatic action")
    print("  a player member may appeal to the Tianzi, with eligible AI recipients accepting by a single duty term")
    print("  relief action has no CB, world scan, event/on-action bridge or custom wargoal")
    print("  membership application, voluntary exit and historic restoration wired")
    print("  this command performs static checks only; runtime evidence is documented separately")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

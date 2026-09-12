#!/usr/bin/env python3
"""Shared source helpers and compatibility entry for the retired Mandate economy."""

from __future__ import annotations

import json
import re
from pathlib import Path
from generate_zhx_tianxia_roster import EOC_SLOTS


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
    # Keep this established command and shared parser helpers available.
    # The 2026-09-12 design retires the former Mandate economy.
    from validate_wangming_carrier import main as validate_carrier
    validate_carrier()


if __name__ == "__main__":
    main()

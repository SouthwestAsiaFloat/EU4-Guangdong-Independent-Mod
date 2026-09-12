#!/usr/bin/env python3
"""Validate the integrated Mandate / Zhou-member window layout."""

from __future__ import annotations

from io import BytesIO
import re
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"
GUI = MOD / "interface/celestialempireview.gui"
PROVINCE_GUI = MOD / "interface/provinceview.gui"
TIANXIA_GFX = MOD / "interface/gdd_tianxia_territory.gfx"
CUSTOM_GUI = MOD / "common/custom_gui/gdd_celestial_vassal_shields.txt"
TIANXIA_CUSTOM_GUI = MOD / "common/custom_gui/gdd_tianxia_territory_gui.txt"
LOCALISATION = MOD / "localisation_source/gdd_l_english_readable_utf8.txt"
REFORM_ACTIONS = MOD / "common/scripted_triggers/gdd_celestial_action_triggers.txt"
REFORM_VOTE_TRIGGERS = MOD / "common/scripted_triggers/gdd_celestial_reform_vote_triggers.txt"
REFORM_VOTE_EFFECTS = MOD / "common/scripted_effects/gdd_celestial_reform_vote_effects.txt"
REFORM_EFFECTS = MOD / "common/scripted_effects/gdd_celestial_proxy_effects.txt"
REFORM_MODIFIERS = MOD / "common/triggered_modifiers/gdd_celestial_proxy_reforms.txt"
TIANXIA_SUBJECTS = MOD / "common/subject_types/gdd_tianxia_subjects.txt"
LONG_ACTION_BUTTON = MOD / "gfx/interface/gdd_eoc_button_type_1_220.tga"


def controls(text: str) -> dict[str, dict[str, float | int]]:
    """Read direct children of celestial_window; nested position braces are safe."""
    parsed: dict[str, dict[str, float | int]] = {}
    current: list[str] | None = None
    for line in text.splitlines():
        if re.match(r"^\t\t(?:guiButtonType|iconType|instantTextBoxType) = \{$", line):
            current = [line]
            continue
        if current is None:
            continue
        current.append(line)
        if line != "\t\t}":
            continue
        block = "\n".join(current)
        current = None
        name_match = re.search(r'\bname = "([^"]+)"', block)
        if not name_match:
            continue
        values: dict[str, float | int] = {}
        position = re.search(r"position = \{ x = (-?\d+) y = (-?\d+) \}", block)
        scale = re.search(r"\bscale = ([0-9.]+)", block)
        size = re.search(r"size = \{ x = (\d+) y = (\d+) \}", block)
        if position:
            values["x"], values["y"] = map(int, position.groups())
        if scale:
            values["scale"] = float(scale.group(1))
        if size:
            values["width"], values["height"] = map(int, size.groups())
        parsed[name_match.group(1)] = values
    return parsed


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def validate_clausewitz_braces(path: Path) -> None:
    """Balance braces while ignoring comments and quoted localisation text."""
    text = path.read_text(encoding="utf-8-sig")
    depth = 0
    quoted = False
    escaped = False
    comment = False
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
    require(not quoted, f"{path.name}: unterminated quoted string")
    require(depth == 0, f"{path.name}: unbalanced braces ({depth})")


def custom_block(text: str, name: str) -> str:
    match = re.search(
        rf"(?ms)^custom_(?:button|icon) = \{{\n    name = {re.escape(name)}\n.*?^\}}$",
        text,
    )
    require(match is not None, f"missing scripted GUI binding: {name}")
    return match.group(0)


def gui_control_block(text: str, name: str) -> str:
    match = re.search(
        rf'(?ms)^\t\t(?:guiButtonType|iconType) = \{{\n'
        rf'\t\t\tname = "{re.escape(name)}"\n.*?^\t\t\}}$',
        text,
    )
    require(match is not None, f"missing GUI control: {name}")
    return match.group(0)


def main() -> None:
    gui_text = GUI.read_text(encoding="utf-8")
    custom_text = CUSTOM_GUI.read_text(encoding="utf-8")
    parsed = controls(gui_text)

    for path in (
        GUI, PROVINCE_GUI, TIANXIA_GFX, CUSTOM_GUI, TIANXIA_CUSTOM_GUI,
        REFORM_ACTIONS, REFORM_VOTE_TRIGGERS,
        REFORM_VOTE_EFFECTS, REFORM_EFFECTS, REFORM_MODIFIERS,
        TIANXIA_SUBJECTS,
    ):
        validate_clausewitz_braces(path)
    require(
        "decree_label" in parsed,
        "missing hard-coded vanilla child decree_label from celestial_window",
    )

    decree_names = [
        name
        for name in parsed
        if name.startswith("gdd_decree_") and name.endswith("_button")
    ]
    expected_decree_rows = {162 + 40 * row for row in range(12)}
    require(len(decree_names) == 18, "expected 18 decree controls")
    require(
        {int(parsed[name]["y"]) for name in decree_names} == expected_decree_rows,
        "decree rows do not fill the paged 12-row viewport",
    )
    require(
        all(
            parsed[name].get("x") == 123 and parsed[name].get("scale") == 1.0
            for name in decree_names
        ),
        "native-size compact decree scrolls are not centred",
    )
    require(
        gui_text.count('quadTextureSprite = "GFX_gdd_eoc_decree_button_compact"') == 18,
        "every visible decree must use the compact native-size scroll",
    )
    require(parsed["meritocracy_icon"]["x"] == 182
            and parsed["meritocracy_value"]["x"] == 190
            and parsed["meritocracy_value"]["y"] == 127,
            "meritocracy icon/value group is not aligned")

    page_one_decrees = [
        "expand_bureaucracy", "improved_expand_bureaucracy",
        "conduct_census", "improved_conduct_census",
        "promote_naval_officers", "increase_tariff_control",
        "improve_defence_effort", "boost_officer_corps",
        "fund_new_centers_of_education", "proclaim_dynastic_name",
        "issue_the_great_warnings", "six_ordinances",
        "sacred_edict_of_confucianism", "promote_taoist_studies",
    ]
    page_two_decrees = [
        "appoint_entrusted_eunuchs", "increase_trade_cooperation",
        "reinforce_the_inner_guard", "issue_bureaucratic_imperial_seal",
    ]
    for stem in page_one_decrees:
        for suffix in ("button", "active"):
            require("NOT = { has_country_flag = gdd_eoc_decree_page_2 }"
                    in custom_block(custom_text, f"gdd_decree_{stem}_{suffix}"),
                    f"page-one condition missing from {stem}_{suffix}")
    for stem in page_two_decrees:
        for suffix in ("button", "active"):
            require("has_country_flag = gdd_eoc_decree_page_2"
                    in custom_block(custom_text, f"gdd_decree_{stem}_{suffix}"),
                    f"page-two condition missing from {stem}_{suffix}")
    custom_block(custom_text, "gdd_eoc_decree_scroll_up")
    custom_block(custom_text, "gdd_eoc_decree_scroll_down")

    for name in ("gdd_eoc_member_scroll_up", "gdd_eoc_member_scroll_down"):
        block = custom_block(custom_text, name)
        require("hidden_trigger = { always = yes }" in block,
                f"member-scroll condition is visible for {name}")
        require("tooltip =" not in block,
                f"member-scroll arrow still exposes explanatory text: {name}")

    member_count_match = re.search(
        r"(?ms)^custom_text_box = \{\n    name = gdd_eoc_member_count\n.*?^\}$",
        custom_text,
    )
    require(member_count_match is not None, "missing member-count text binding")
    require("tooltip =" not in member_count_match.group(0),
            "member-count ribbon still exposes explanatory text")

    for index in range(1, 67):
        name = f"gdd_eoc_member_shield_{index:02d}"
        item = parsed.get(name)
        require(item is not None, f"missing member shield {index:02d}")
        page_index = (index - 1) % 48
        column = page_index % 8
        row = page_index // 8
        require(
            item.get("x") == 105 + column * 23
            and item.get("y") == 698 + row * 30
            and item.get("scale") == 0.55,
            f"member shield {index:02d} is outside the paged grid",
        )

    bindings = custom_text.split("# GDD_EOC_MEMBER_BINDINGS_BEGIN", 1)[1].split(
        "# GDD_EOC_MEMBER_BINDINGS_END", 1
    )[0]
    require(bindings.count("gdd_eoc_member_roster_page_2") == 66,
            "every member shield must have one page condition")

    require(parsed["gdd_eoc_member_frame"] == {
        "x": 98,
        "y": 650,
        "width": 220,
        "height": 250,
    }, "member frame geometry drifted")
    require(parsed["gdd_eoc_member_count"]["x"] == 108
            and parsed["gdd_eoc_member_count"]["y"] == 659,
            "member count is not centred in the reused original ribbon")
    require("gdd_eoc_decree_frame" not in parsed, "decree gold frame must stay removed")
    require(parsed["gdd_eoc_decree_scroll_track"]["x"] == 302,
            "decree scrollbar is not on the right edge")
    require(parsed["gdd_eoc_decree_scroll_track"]["height"] == 402,
            "decree scrollbar does not span the extended decree column")
    require(parsed["gdd_eoc_member_scroll_track"]["x"] == 300,
            "member scrollbar is not on the right edge")
    require(parsed["gdd_principal_vassal_slot"]["y"] == 684,
            "principal feudatory is not below the existing ribbon")
    for index in range(1, 7):
        require(parsed[f"gdd_vassal_slot_{index}"]["y"] == 790,
                "great-feudatory row is not above the bottom actions")
    require(parsed["gdd_eoc_authority_track"]["y"] == 328, "authority track is not tucked under the nameplate")
    require(parsed["emperor_label"]["y"] == 258, "emperor label is not centred on the extended nameplate")
    require(parsed["decisions_label"]["x"] == 982
            and parsed["decisions_label"]["y"] == 91,
            "Celestial Reforms title moved off its original green ribbon")

    require(re.search(
        r'name = "celestial_window"\s+position = \{ x = -485 y = -430 \}\s+'
        r'size = \{ x = 1030 y = 850 \}',
        gui_text,
    ) is not None, "final widened window geometry drifted")
    for name, x, sprite in (
        ("gdd_leave_tianxia_button", 374, "button_type_1"),
        (
            "gdd_add_all_tianxia_provinces_button",
            535,
            "GFX_gdd_eoc_button_type_1_220",
        ),
        ("gdd_dismantle_tianxia_button", 767, "button_type_1"),
    ):
        require(parsed.get(name) == {"x": x, "y": 869},
                f"Tianxia action row drifted: {name}")
        control = gui_control_block(gui_text, name)
        require(f'quadTextureSprite = "{sprite}"' in control
                and 'buttonFont = "vic_18"' in control,
                f"Tianxia action does not reuse the approved native HRE style: {name}")
        custom_block(TIANXIA_CUSTOM_GUI.read_text(encoding="utf-8"), name)
    require(318 < 374 and 535 + 220 < 767 and 767 + 149 < 972,
            "Tianxia action row overlaps the member or reform frame")
    require(Image.open(LONG_ACTION_BUTTON).size == (220, 31),
            "long Tianxia action button is not 220x31")

    province_gui = PROVINCE_GUI.read_text(encoding="utf-8")
    tianxia_gfx = TIANXIA_GFX.read_text(encoding="utf-8")
    territory_custom = TIANXIA_CUSTOM_GUI.read_text(encoding="utf-8")
    for name, sprite, sprite_field in (
        (
            "gdd_tianxia_province_member_status_button",
            "GFX_gdd_tianxia_province_status",
            "quadTextureSprite",
        ),
        ("gdd_tianxia_province_add_button", "GFX_gdd_tianxia_province_add", "quadTextureSprite"),
        ("gdd_tianxia_province_remove_button", "GFX_gdd_tianxia_province_remove", "quadTextureSprite"),
    ):
        require(re.search(
            rf'name = "{name}".*?{sprite_field} = "{sprite}".*?'
            rf'position = \{{ x = 20 y = 328 \}}',
            province_gui,
            re.S,
        ) is not None, f"province Tianxia indicator left the native HRE slot: {name}")
        custom_block(territory_custom, name)
        require(f'name = "{sprite}"' in tianxia_gfx,
                f"missing province indicator sprite: {sprite}")
    require(province_gui.index('name ="hre_button"')
            < province_gui.index('name = "gdd_tianxia_province_member_status_button"'),
            "Tianxia indicator no longer overlays the hard-coded HRE button")
    for filename in (
        "gdd_tianxia_province_status.tga",
        "gdd_tianxia_province_add.tga",
        "gdd_tianxia_province_remove.tga",
    ):
        require(Image.open(MOD / "gfx/interface" / filename).size == (216, 42),
                f"{filename} is not a four-frame 54px button strip")

    ordinary_reforms = [
        "keju", "civil_registration", "silver_standard", "kanhe",
        "unified_market", "military_branch", "foreign_ship_designs",
        "inclusive_monarchy",
    ]
    centralising_reforms = [
        "establish_gaituguiliu", "land_tax", "single_whip",
        "centralizing_government", "reign_in_estates",
        "vassalize_tributaries",
    ]
    decentralising_reforms = [
        "seaban", "military_governors", "tributary_embassies",
        "modernize_banners", "bureaucratic_faction", "new_world",
    ]
    reform_rows = {
        **dict(zip(ordinary_reforms, range(149, 374, 32))),
        **dict(zip(centralising_reforms, range(467, 618, 30))),
        **dict(zip(decentralising_reforms, range(711, 862, 30))),
    }
    require(len(reform_rows) == 20, "expected an 8/6/6 set of twenty reforms")
    for stem, y in reform_rows.items():
        button = f"gdd_reform_{stem}_button"
        passed = f"gdd_reform_{stem}_passed"
        vote = f"gdd_reform_vote_{stem}_button"
        checked = f"gdd_reform_vote_{stem}_checked"
        require(parsed.get(button) == {"x": 982, "y": y, "scale": 0.9},
                f"reform row drifted: {stem}")
        require(parsed.get(passed) == {"x": 988, "y": y + 7, "scale": 0.75},
                f"passed overlay drifted: {stem}")
        require(parsed.get(vote) == {"x": 1164, "y": y + 5, "scale": 0.65},
                f"vote checkbox drifted: {stem}")
        require(parsed.get(checked) == {"x": 1164, "y": y + 5, "scale": 0.65},
                f"vote checkmark drifted: {stem}")
        require('quadTextureSprite = "GFX_reform_button"'
                in gui_control_block(gui_text, button),
                f"reform does not reuse vanilla button: {stem}")
        button_binding = custom_block(custom_text, button)
        require("tooltip = GDD_CELESTIAL_REFORM_BUTTON_TRIGGER_TT"
                in button_binding,
                f"reform exposes verbose internal trigger tree: {stem}")
        custom_block(custom_text, passed)
        custom_block(custom_text, vote)
        custom_block(custom_text, checked)

    require(parsed["gdd_eoc_ordinary_reform_frame"] == {
        "x": 972, "y": 108, "width": 220, "height": 304,
    }, "ordinary reform frame geometry drifted")
    require(parsed["gdd_eoc_centralizing_reform_frame"] == {
        "x": 972, "y": 430, "width": 220, "height": 226,
    }, "centralising reform frame geometry drifted")
    require(parsed["gdd_eoc_decentralizing_reform_frame"] == {
        "x": 972, "y": 674, "width": 220, "height": 226,
    }, "decentralising reform frame geometry drifted")
    require(parsed["gdd_reform_ordinary_header"]["y"] == 116
            and parsed["gdd_reform_centralizing_header"]["y"] == 438
            and parsed["gdd_reform_decentralizing_header"]["y"] == 682,
            "reform group headers are not lowered into their frames")
    require("gdd_reform_military_faction_button" not in gui_text
            and "gdd_reform_military_faction_button" not in custom_text,
            "removed twenty-first reform is still exposed")
    require(parsed["gdd_central_final_conflict_mark"]["y"] == 617
            and parsed["gdd_decentral_final_conflict_mark"]["y"] == 861,
            "final-reform mutual-exclusion marks drifted")
    require("gdd_bureaucratic_faction_conflict_mark" not in gui_text
            and "gdd_military_faction_conflict_mark" not in gui_text,
            "obsolete faction mutual-exclusion marks remain")

    # Check relationships as well as coordinates: keep hitboxes separated,
    # state overlays attached, and the reserved central area unobstructed.
    member_frame = parsed["gdd_eoc_member_frame"]
    frame_names = [f"gdd_eoc_{group}_reform_frame" for group in
                   ("ordinary", "centralizing", "decentralizing")]
    frames = [parsed[name] for name in frame_names]
    axis = 645
    require(all(frame["width"] == member_frame["width"] for frame in frames),
            "side columns no longer have equal widths")
    require(member_frame["x"] + member_frame["width"] + frames[0]["x"] == 2 * axis,
            "side columns are not mirrored around the feudatory ribbon")
    require(all(b["y"] - a["y"] - a["height"] == 18
                for a, b in zip(frames, frames[1:])),
            "reform group spacing is uneven")
    require(frames[-1]["y"] + frames[-1]["height"]
            == member_frame["y"] + member_frame["height"]
            == parsed["gdd_leave_tianxia_button"]["y"] + 31,
            "member, reform and action bottoms are not aligned")
    left = parsed["gdd_leave_tianxia_button"]["x"]
    middle = parsed["gdd_add_all_tianxia_provinces_button"]["x"]
    right = parsed["gdd_dismantle_tianxia_button"]["x"]
    require(middle - left - 149 == right - middle - 220 == 12
            and left + right + 149 == 2 * axis,
            "action buttons lost their equal gaps or centre alignment")
    for index in range(1, 7):
        require(parsed[f"gdd_vassal_slot_{index}"]
                == parsed[f"gdd_vassal_empty_slot_{index}"],
                "live and empty feudatory shield layers are misaligned")
    for name in decree_names:
        active = parsed[name.removesuffix("_button") + "_active"]
        require(active["x"] - parsed[name]["x"] == 162
                and active["y"] - parsed[name]["y"] == 8,
                f"decree active mark left its button: {name}")
    for stems, frame in zip(
        (ordinary_reforms, centralising_reforms, decentralising_reforms), frames
    ):
        rows = [parsed[f"gdd_reform_{stem}_button"] for stem in stems]
        for row, stem in zip(rows, stems):
            # Vanilla reform_button.dds is 198x33; checkbox frames are 32x32.
            vote = parsed[f"gdd_reform_vote_{stem}_button"]
            require(frame["x"] < row["x"]
                    and row["x"] + 198 * row["scale"] < vote["x"]
                    and vote["x"] + 32 * vote["scale"] < frame["x"] + frame["width"]
                    and frame["y"] < row["y"]
                    and row["y"] + 33 * row["scale"] < frame["y"] + frame["height"],
                    f"reform row overflows its frame or vote checkbox: {stem}")
        require(all(a["y"] + 33 * a["scale"] <= b["y"]
                    for a, b in zip(rows, rows[1:])),
                "reform button hitboxes overlap vertically")
    for name, item in parsed.items():
        require(not (318 < item.get("x", -1) < 972
                     and 393 <= item.get("y", -1) < 644),
                f"control intrudes into the reserved central area: {name}")

    actions = REFORM_ACTIONS.read_text(encoding="utf-8")
    vote_triggers = REFORM_VOTE_TRIGGERS.read_text(encoding="utf-8")
    vote_effects = REFORM_VOTE_EFFECTS.read_text(encoding="utf-8")
    effects = REFORM_EFFECTS.read_text(encoding="utf-8")
    modifiers = REFORM_MODIFIERS.read_text(encoding="utf-8")
    subjects = TIANXIA_SUBJECTS.read_text(encoding="utf-8")
    require(actions.count("gdd_five_ordinary_celestial_reforms_passed = yes") >= 12,
            "route reforms are not gated behind five ordinary reforms")
    require("NOT = { gdd_reform_new_world_passed = yes }" in actions
            and "NOT = { gdd_reform_vassalize_tributaries_passed = yes }" in actions,
            "the two final reforms are not mutually exclusive")
    require("gdd_reform_vote_total_without_principal_dev" in vote_triggers
            and "gdd_reform_vote_total_without_principal_plus_one" in vote_triggers
            and "gdd_reform_vote_total_without_principal_dev" in vote_effects,
            "executor-excluded strict-majority cache is incomplete")
    require("set_country_flag = $which$" in effects
            and "gdd_pay_reform_authority_cost = yes" in effects,
            "reform ownership or authority cost routing is missing")
    require("subject_type = gdd_tianxia_vassal" in effects
            and "zhx_is_tianxia_polity = yes" in effects,
            "central final does not target Zhou polities with its special subject")
    require("is_subject_of_type = tributary_state" not in modifiers,
            "reform modifiers still target tributaries instead of Zhou polities")
    for stem in ordinary_reforms:
        require(f"gdd_proxy_reform_{stem}_member = {{" in modifiers,
                f"ordinary reform has no Zhou-wide benefit: {stem}")
        require(re.search(
            rf"(?s)gdd_reform_{stem}_passed = yes.*?"
            rf"gdd_begin_ai_reform_vote_effect = yes\s+"
            rf"change_variable = \{{ which = gdd_ai_reform_vote_score value = 2 \}}",
            vote_effects,
        ) is not None, f"ordinary reform lacks its Zhou-benefit AI vote weight: {stem}")
    require("takes_diplo_slot = no" in subjects
            and "max_government_rank = 0" in subjects,
            "Tianxia vassal does not support no-slot unrestricted-rank subjects")

    for name in ("influence_label", "influence_value", "influence_growth",
                 "gdd_eoc_mandate_value_tooltip", "gdd_eoc_mandate_growth_tooltip",
                 "benefits_icon", "diplomatic_actions_icon"):
        require(parsed[name]["x"] == -10000 and parsed[name]["y"] == -10000,
                f"retired native Mandate UI remains visible: {name}")


    localisation = LOCALISATION.read_text(encoding="utf-8-sig")
    require(
        "GDD_CELESTIAL_GREAT_FEUDATORIES:0 \"七大诸侯\"" in localisation,
        "missing seven-great-feudatories localisation",
    )

    sys.path.insert(0, str(ROOT / "tools"))
    import generate_gdd_eoc_reform_groups as groups
    import generate_gdd_eoc_wide_background as background
    import generate_gdd_eoc_final_wide_layout as final_layout

    require(background.OUTPUT.read_bytes() == background.render(), "stale Mandate background")
    require(groups.OUTPUT.read_bytes() == groups.render(), "stale grouped-panel overlay")
    require(groups.DECREE_OUTPUT.read_bytes() == groups.render_compact_decree_button(),
            "stale compact decree scroll")
    require(final_layout.BACKGROUND_OUTPUT.read_bytes() == final_layout.render_background(),
            "stale final 1180px Mandate background")
    require(final_layout.OVERLAY_OUTPUT.read_bytes() == final_layout.render_overlay(),
            "stale final 1180px grouped-panel overlay")
    require(background.FEUDATORY_HEADER_TARGET == (314, 626, 684, 658),
            "seven-feudatory green scroll is not aligned with its GUI label")
    mandate_right = (
        background.MANDATE_COUNTER_TARGET[0]
        + background.MANDATE_COUNTER[2]
        - background.MANDATE_COUNTER[0]
    )
    require(final_layout.TITLE_SECOND_CUT
            - final_layout.TITLE_BRIDGE_SAMPLE_WIDTH // 2 >= mandate_right,
            "title widening sample crosses and stretches the Mandate frame edge")

    overlay = Image.open(BytesIO(final_layout.render_overlay())).convert("RGBA")
    for gui_x, gui_y, label in (
        (1060, 200, "ordinary"),
        (1060, 500, "centralising"),
        (1060, 780, "decentralising"),
        (1060, 95, "Celestial Reforms ribbon"),
    ):
        alpha = overlay.getpixel((gui_x - groups.BACKGROUND_X,
                                  gui_y - groups.BACKGROUND_Y))[3]
        require(alpha == 0, f"overlay still covers transparent {label} area")
    print("Integrated Mandate / Zhou-member layout: PASS")
    print("  Centred decrees fill the extended functional 12 + 4 page viewport")
    print("  Short member panel uses a functional 48 + 18 page scrollbar")
    print("  Original entry and window retained; retired Mandate controls are off canvas")
    print("  Equal 220px side columns share the existing seven-feudatory centre axis")
    print("  Three native HRE buttons have equal gaps and align with the panel bottoms")
    print("  Reforms retain their native art, scales and 8 / 6 / 6 grouping")


if __name__ == "__main__":
    main()

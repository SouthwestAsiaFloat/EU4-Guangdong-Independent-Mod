#!/usr/bin/env python3
"""Static contract for the Zhou merit store and 25-year dignity election."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"

EFFECTS = MOD / "common/scripted_effects/zhx_merit_store_effects.txt"
TRIGGERS = MOD / "common/scripted_triggers/zhx_merit_store_triggers.txt"
MODIFIERS = MOD / "common/event_modifiers/zhx_merit_store_modifiers.txt"
GUI = MOD / "common/custom_gui/zhx_merit_store_gui.txt"
TOPBAR = MOD / "interface/topbar.gui"
MERIT_GFX = MOD / "interface/zhx_merit_store.gfx"
EVENTS = MOD / "events/zhx_system_events.txt"
SYSTEM = MOD / "common/scripted_effects/zhx_system_effects.txt"
ROSTER = MOD / "common/scripted_effects/zhx_gui_roster_effects.txt"
LOC = MOD / "localisation_source/zhx_system_readable_utf8.txt"
CUSTOM_LOC = MOD / "customizable_localization/zhx_merit_store_customizable_localization.txt"


def read(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"missing {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8", errors="strict")


effects = read(EFFECTS)
triggers = read(TRIGGERS)
modifiers = read(MODIFIERS)
gui = read(GUI)
topbar = read(TOPBAR)
merit_gfx = read(MERIT_GFX)
events = read(EVENTS)
system = read(SYSTEM)
roster = read(ROSTER)
loc = read(LOC)
custom_loc = read(CUSTOM_LOC)

for variable in ("zhx_merit", "zhx_merit_term", "zhx_merit_lifetime"):
    assert f"which = {variable}" in effects, f"missing ledger {variable}"

assert triggers.count("which = zhx_merit value = 50") == 4, "all four category gates must require 50 merit"
assert effects.count("value = -50") == 8, "all eight purchases must cost 50"
assert effects.count("which = zhx_merit value = 50") == 1, "AI purchase gate must require 50 merit"
assert custom_loc.count("which = zhx_merit value = 50") == 8, "all eight item states must require 50 merit"
assert effects.count("duration = 3650") == 8, "all eight purchases must last ten years"
assert "value = 25 }" in effects and "zhx_settle_merit_term" in effects
assert "zhx_merit_active_contribution_this_term" in triggers
assert effects.count("zhx_select_next_merit_rank = { rank =") == 7
assert "which = zhx_merit_term which = event_target:zhx_merit_rank_best" in triggers
assert "which = zhx_merit_lifetime which = event_target:zhx_merit_rank_best" in triggers
assert "which = zhx_merit_rank_prestige which = event_target:zhx_merit_rank_best" in triggers

items = (
    "relief", "governance", "trade", "industry",
    "army", "fortification", "honour", "diplomacy",
)
item_pairs = {
    "relief": "governance",
    "governance": "relief",
    "trade": "industry",
    "industry": "trade",
    "army": "fortification",
    "fortification": "army",
    "honour": "diplomacy",
    "diplomacy": "honour",
}
defined_text_names = {
    "relief": "GetZhxMeritStoreReliefStatus",
    "governance": "GetZhxMeritStoreGovernanceStatus",
    "trade": "GetZhxMeritStoreTradeStatus",
    "industry": "GetZhxMeritStoreIndustryStatus",
    "army": "GetZhxMeritStoreArmyStatus",
    "fortification": "GetZhxMeritStoreFortificationStatus",
    "honour": "GetZhxMeritStoreHonourStatus",
    "diplomacy": "GetZhxMeritStoreDiplomacyStatus",
}
for item in items:
    assert f"zhx_merit_store_{item} = {{" in modifiers
    assert f"name = zhx_gui_merit_store_{item}_button" in gui
    assert f'name = "zhx_gui_merit_store_{item}_button"' in topbar
    assert f"name = zhx_gui_merit_store_{item}_status" in gui
    assert f'name = "zhx_gui_merit_store_{item}_status"' in topbar
    assert f"zhx_gui_merit_store_{item}_tt:0" in loc
    assert f"zhx_gui_merit_store_{item}_status:0" in loc

    status_block = re.search(
        rf"defined_text\s*=\s*\{{\s*name\s*=\s*{defined_text_names[item]}\b(.*?)(?=\ndefined_text\s*=|\Z)",
        custom_loc,
        re.S,
    )
    assert status_block, f"missing display status for {item}"
    status_body = status_block.group(1)
    assert f"has_country_modifier = zhx_merit_store_{item}" in status_body
    assert f"has_country_modifier = zhx_merit_store_{item_pairs[item]}" in status_body
    assert "zhx_merit_store_item_status_available" in status_body
    assert "zhx_merit_store_item_status_insufficient" in status_body

assert "yearly_prestige" not in modifiers
assert "prestige = 0.5" in modifiers
assert gui.count("trigger = { hidden_trigger = {") == 8
assert gui.count("effect = { hidden_effect = {") == 8
assert gui.count("potential = { has_global_flag = zhx_system_initialised_v13 }") == 8
for textbox in ("available", "rank", "lifetime", "cutoff", "years", "qualification"):
    assert f"name = zhx_gui_merit_store_{textbox}" in gui
    assert f'name = "zhx_gui_merit_store_{textbox}"' in topbar

for category, sprite in {
    "governance": "GFX_zhx_merit_governance",
    "economy": "GFX_zhx_merit_economy",
    "military": "GFX_zhx_merit_military",
    "diplomacy": "GFX_zhx_merit_diplomacy",
}.items():
    assert f'name = "zhx_gui_merit_store_{category}_frame"' in topbar
    assert f'name = "zhx_gui_merit_store_{category}_icon"' in topbar
    assert f'spriteType = "{sprite}"' in topbar
    assert f'name = "{sprite}"' in merit_gfx
    texture = MOD / f"gfx/interface/zhx_merit_{category}.tga"
    assert texture.exists(), f"missing text-free merit icon {texture.relative_to(ROOT)}"
    assert texture.stat().st_size > 4096, f"merit icon is unexpectedly small: {texture.name}"
    assert f'texturefile = "gfx/interface/zhx_merit_{category}.tga"' in merit_gfx
assert topbar.count('quadTextureSprite = "GFX_gdd_eoc_reform_frame"') >= 5
assert 'name = "zhx_gui_merit_store_explanation"' not in topbar
for layout_anchor in (
    'position = { x = 68 y = 624 } size = { x = 414 y = 108 }',
    'position = { x = 498 y = 624 } size = { x = 414 y = 108 }',
    'position = { x = 68 y = 740 } size = { x = 414 y = 108 }',
    'position = { x = 498 y = 740 } size = { x = 414 y = 108 }',
):
    assert layout_anchor in topbar, "merit folios must remain a bounded 2x2 grid"
assert "name = zhx_gui_merit_store_header" in gui
header = re.search(
    r'instantTextBoxType\s*=\s*\{\s*name\s*=\s*"zhx_gui_merit_store_header"(.*?)\n\s*\}',
    topbar,
    re.S,
)
assert header, "missing merit presentation header"
assert "scripted = yes" in header.group(1), "merit header must expose its tooltip binding"
assert 'text = ""' in header.group(1), "scripted merit header must use its name localization"
assert 'zhx_gui_merit_store_header:0 "叙功行赏"' in loc
assert "zhx_gui_merit_store_header_tt:0" in loc
for source_label in ("发展度岁计", "攘外", "公议", "勤王"):
    assert f"§G{source_label}§!" in loc, f"merit header tooltip does not highlight {source_label}"
for reward_label in ("王命敕赏", "七大诸侯", "首席诸侯"):
    assert f"§G{reward_label}§!" in loc, f"merit header tooltip does not highlight {reward_label}"
assert "ZHX_GUI_MERIT_STORE_HEADER" not in topbar + loc
assert "zhx_gui_merit_store_unranked" not in gui + topbar
assert "zhx_gui_merit_store_unqualified" not in gui + topbar
assert "zhx_gui_merit_store_cutoff_empty" not in gui + topbar
assert "name = GetZhxMeritStoreRankStatus" in custom_loc
assert "name = GetZhxMeritStoreCutoffStatus" in custom_loc
assert "name = GetZhxMeritStoreQualificationStatus" in custom_loc
for status_key in (
    "available", "active", "locked", "insufficient", "nonmember",
):
    assert f"zhx_merit_store_item_status_{status_key}:0" in loc

assert "NOT = { has_global_flag = zhx_system_initialised_v13 }" in events
assert "zhx_migrate_tianxia_system_v12_to_v13 = yes" in events
assert "zhx_yearly_merit_tick = yes" in events
assert "save_global_event_target_as = gdd_principal_vassal" in effects
assert "gdd_build_eoc_great_feudatory_roster = yes" in effects
assert "gdd_refresh_authority_balance_effects = yes" in effects

assert "ZHX_ROSTER_SHIELDS_BEGIN" not in topbar
assert "zhx_gui_member_shield_01" not in topbar
assert "ZHX_ROSTER_BINDINGS_BEGIN" not in read(MOD / "common/custom_gui/zhx_tianxia_gui.txt")
assert "zhx_allocate_gui_roster_slot = yes" not in re.search(
    r"zhx_build_gui_roster\s*=\s*\{(.*?)\n\}", roster, re.S
).group(1)

assert "NOT = { tag = YAN }" not in re.search(
    r"gdd_build_eoc_great_feudatory_roster\s*=\s*\{(.*?)\n\}", roster, re.S
).group(1)
assert "tag = event_target:gdd_principal_vassal" in roster

print("Zhou merit store static contract: PASS")
print("  Three ledgers; 25-year term; active-contribution eligibility; seven-place ranking")
print("  Eight 50-merit / 10-year items in four mutually exclusive categories")
print("  Dynamic Principal and Seven identities reuse the existing Mandate-page roster")
print("  Former 200-shield Zhou roster is absent from the rendered panel and annual builder")

"""Source contracts for an inert native window and authority-paid reforms.

This does not claim to emulate EU4's hard-coded diplomatic behaviour.
"""
import json
from pathlib import Path
import re
import subprocess

from validate_gdd_celestial_mandate import balanced, block, compact, require

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"


def read(rel):
    raw = (MOD / rel).read_bytes()
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("latin1")


def code(text):
    return re.sub(r'#[^\n]*|"(?:\\.|[^"\\])*"', '', text)


def main():
    manifest = json.loads((ROOT / "tools/gdd_mandate_carrier_overrides.json").read_text())
    paths = {row["path"] for row in manifest["files"]}
    for rel in paths:
        balanced(MOD / rel, read(rel))
    guard = compact(read("common/scripted_triggers/gdd_mandate_carrier_triggers.txt"))
    require(guard == "gdd_gameplay_emperor_of_china = { always = no }",
            "native gameplay identity is not disabled")
    native = read("common/on_actions/00_on_actions.txt")
    for hook in ("on_mandate_of_heaven_gained", "on_mandate_of_heaven_lost"):
        require(compact(block(native, hook)) == hook + " = { }",
                f"native transfer still changes gameplay: {hook}")
    require("save_global_event_target_as = EmperorOfChina" in block(native, "on_startup"),
            "native window/decree target lost startup initialization")
    cb = block(read("common/cb_types/00_cb_types.txt"), "cb_take_mandate")
    for gate in ("prerequisites_self", "prerequisites"):
        require("always = no" in block(cb, gate), "Mandate can still be contested")

    raw_identity_allowlist = {
        "common/on_actions/00_on_actions.txt",  # original window target
        "events/gdd_celestial_mandate_events.txt",  # shell setup
        "events/gdd_celestial_test_events.txt",  # unchanged decree AI only
        "common/scripted_triggers/gdd_celestial_action_triggers.txt",  # decrees
    }
    for folder in ("common", "events", "missions", "decisions"):
        for path in (MOD / folder).rglob("*.txt"):
            rel = path.relative_to(MOD).as_posix()
            text = code(read(rel))
            if re.search(r"\bis_emperor_of_china\s*=", text):
                require(rel in raw_identity_allowlist, f"native identity gameplay leak: {rel}")
            require(not re.search(r"\bset_emperor_of_china\s*=", text),
                    f"scripted native title transfer remains: {rel}")
            require(not re.search(r"\badd_mandate\s*=", text), f"Mandate award remains: {rel}")
            if re.search(r"\bset_mandate\s*=", text):
                require(rel == "events/gdd_celestial_mandate_events.txt"
                        and "set_mandate = 50" in text, f"unapproved Mandate mutation: {rel}")

    static = read("common/static_modifiers/zz_gdd_neutral_mandate.txt")
    for name in ("positive_mandate", "negative_mandate", "lost_mandate_of_heaven"):
        require(compact(block(static, name)) == name + " = { }", f"native bonus/penalty remains: {name}")
    defines = read("common/defines/zz_gdd_mandate.lua")
    for name in ("STABILITY", "STATE_WITH_PROSPERITY", "HUNDRED_TRIBUTARY_DEV",
                 "HUNDRED_NONTRIBUTARY_DEV", "HUNDRED_DEVASTATION", "5_LOANS"):
        require(f"CELESTIAL_EMPIRE_MANDATE_PER_{name} = 0" in defines,
                f"native monthly source not retired: {name}")
    require("CELESTIAL_EMPIRE_REFORM_MIN_VALUE = 101" in defines, "native reform gate is reachable")

    actions = read("common/scripted_triggers/gdd_celestial_action_triggers.txt")
    for name in ("gdd_proxy_celestial_reform_base_trigger", "gdd_can_actively_revoke_proxy_celestial_reform_trigger"):
        body = block(actions, name)
        require("gdd_has_reform_authority_cost = yes" in body, f"missing payment gate: {name}")
        require("EmperorOfChina" not in body and "imperial_mandate" not in body,
                f"reform still requires the native carrier: {name}")
    proxy = read("common/scripted_effects/gdd_celestial_proxy_effects.txt")
    for name in ("gdd_enact_proxy_celestial_reform_effect", "gdd_actively_revoke_proxy_celestial_reform_effect"):
        require("gdd_pay_reform_authority_cost = yes" in block(proxy, name), f"unpaid transaction: {name}")
    require("$which$_can_enact = yes" in block(proxy, "gdd_enact_proxy_celestial_reform_effect"),
            "selected reform vote/prerequisites are not rechecked")
    require("$which$_on_pass = yes" in block(proxy, "gdd_enact_proxy_celestial_reform_effect"),
            "final reform actions are not inside the paid transaction")
    votes = read("common/scripted_effects/gdd_celestial_reform_vote_effects.txt")
    require("trigger_value:imperial_mandate" not in votes, "retired Mandate still changes AI support")
    # Existing authority accrual, clamps, and modifiers must be unchanged.
    for rel in ("common/scripted_effects/gdd_celestial_authority_effects.txt",
                "common/event_modifiers/gdd_celestial_authority_modifiers.txt"):
        before = subprocess.check_output(["git", "show", "HEAD:guangdong_independent_practice/" + rel], cwd=ROOT)
        require(before == (MOD / rel).read_bytes(), f"authority mechanics changed beyond payment: {rel}")

    # Preserve the complete decree transaction, including its 20 Meritocracy cost.
    before = subprocess.check_output(["git", "show", "HEAD:guangdong_independent_practice/common/scripted_effects/gdd_celestial_proxy_effects.txt"], cwd=ROOT).decode()
    require(compact(block(before, "gdd_enact_proxy_decree_effect")) == compact(block(proxy, "gdd_enact_proxy_decree_effect")),
            "decree cost/effect changed")
    gui = read("interface/celestialempireview.gui")
    require('name = "celestial_window"' in gui and 'name = "close_button"' in gui,
            "native window contract lost")
    for rel in ("interface/topbar.gui", "interface/menubar.gui"):
        if (MOD / rel).exists():
            before = subprocess.check_output(["git", "show", "HEAD:guangdong_independent_practice/" + rel], cwd=ROOT)
            require(before == (MOD / rel).read_bytes(), f"original entry changed: {rel}")
    print(f"PASS: native window carrier and authority transactions; {len(paths)} inherited/script override files checked")
    print("Runtime/hard-coded diplomatic neutrality is not established by this source check.")


if __name__ == "__main__":
    main()

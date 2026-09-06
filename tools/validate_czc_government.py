#!/usr/bin/env python3
"""Check the CZC council's script and asset contracts without changing files.

This catches broken routing, references, asset frames and unintended changes to
the inherited government view. It does not emulate EU4 succession or prove that
the native view accepts the custom controls; those require the runtime matrix
in docs/gameplay/11_chaozhou_government.md.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import struct
import sys

from encode_eu4_chinese_localisation import FILES, verify_file


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"
STEAM = Path.home() / "Library/Application Support/Steam/steamapps"
VANILLA = STEAM / "common/Europa Universalis IV"
DEPENDENCIES = [STEAM / "workshop/content/236850" / item for item in ("2976470733", "1999055990")]
REFORM = "gdd_czc_council_reform"
ELIGIBLE = "gdd_czc_is_council_trigger"
COOLDOWN = "gdd_czc_can_shift_power_trigger"
CROWN = "gdd_czc_should_proclaim_king_trigger"
PREFIX = "gdd_czc_"
PATHS = {
    "reforms": "common/government_reforms/zzz_gdd_czc_government_reforms.txt",
    "triggers": "common/scripted_triggers/gdd_czc_government_triggers.txt",
    "effects": "common/scripted_effects/gdd_czc_government_effects.txt",
    "on_actions": "common/on_actions/gdd_czc_government_on_actions.txt",
    "events": "events/gdd_czc_government_events.txt",
    "gui": "interface/countrygovernmentview.gui",
    "custom_gui": "common/custom_gui/gdd_czc_government_gui.txt",
    "gfx": "interface/gdd_czc_government.gfx",
}
SOURCE = "019_gdd_czc_government_readable_utf8.txt"
ASSET_DIMENSIONS = {
    "frame.dds": (280, 50, 1),
    "gentry.dds": (64, 32, 2),
    "ruler.dds": (64, 32, 2),
    "pointer_track.dds": (5880, 50, 21),
    "government_reform.dds": (64, 64, 1),
}
TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|\#[^\n]*|[{}]|[=<>!]+|[^\s{}=<>!#"]+')


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def parse(text: str, label: str = "script") -> list:
    """Small ordered Clausewitz tree; duplicate blocks and list atoms survive."""
    tokens = []
    cursor = 0
    for match in TOKEN.finditer(text):
        require(not text[cursor:match.start()].strip(), f"{label}: malformed quoted text")
        token = match.group()
        cursor = match.end()
        if not token.startswith("#"):
            tokens.append(token[1:-1] if token.startswith('"') else token)
    require(not text[cursor:].strip(), f"{label}: unterminated text")
    position = 0

    def level(nested=False):
        nonlocal position
        result = []
        while position < len(tokens):
            key = tokens[position]
            position += 1
            if key == "}":
                require(nested, f"{label}: extra closing brace")
                return result
            require(key not in {"{", "="}, f"{label}: unexpected {key}")
            if position < len(tokens) and tokens[position] in {"=", ">", "<", ">=", "<=", "!="}:
                operation = tokens[position]
                position += 1
                require(position < len(tokens), f"{label}: missing value after {key}")
                value = tokens[position]
                position += 1
                if value == "{":
                    value = level(True)
                require(value != "}", f"{label}: missing value after {key}")
                result.append((key, operation, value))
            else:
                result.append((key, None, None))
        require(not nested, f"{label}: unclosed block")
        return result

    return level()


def read_tree(path: Path) -> list:
    require(path.is_file(), f"missing {path}")
    return parse(path.read_bytes().decode("latin-1"), str(path))


def values(tree: list, key: str) -> list:
    return [value for name, operation, value in tree if name == key and operation == "="]


def one(tree: list, key: str):
    found = values(tree, key)
    require(len(found) == 1, f"expected one {key}, found {len(found)}")
    return found[0]


def scalar(tree: list, key: str, expected: str) -> None:
    require(one(tree, key) == expected, f"{key} must be {expected}")


def walk(tree: list):
    for entry in tree:
        yield entry
        if isinstance(entry[2], list):
            yield from walk(entry[2])


def contains(tree: list, key: str, value: str) -> bool:
    return (key, "=", value) in walk(tree)


def named_controls(tree: list) -> dict:
    result = {}
    for kind, _, body in walk(tree):
        if isinstance(body, list) and values(body, "name"):
            name = one(body, "name")
            if name.startswith(PREFIX):
                require(name not in result, f"duplicate custom control {name}")
                result[name] = (kind, body)
    return result


def effective(relative: str, include_mod=True) -> Path:
    roots = [VANILLA, *DEPENDENCIES, *([MOD] if include_mod else [])]
    providers = [root / relative for root in roots if (root / relative).is_file()]
    require(bool(providers), f"missing effective upstream resource {relative}")
    return providers[-1]


def check_mechanics(trees: dict) -> None:
    reform = one(trees["reforms"], REFORM)
    scalar(one(reform, "potential"), "tag", "CZC")
    require(one(reform, "potential") == [("tag", "=", "CZC")], "reform eligibility must stay CZC-only")
    for key, expected in {"republican_name": "yes", "has_term_election": "no", "election_on_death": "no", "duration": "0"}.items():
        scalar(reform, key, expected)
    require(not contains(reform, "has_dutch_election", "yes"), "Dutch candidate elections are not the CZC succession contract")
    scalar(one(reform, "custom_attributes"), "cannot_become_dictatorship", "yes")
    scalar(reform, "has_parliament", "yes")
    require(not any(contains(body, "has_parliament", "yes") for body in values(reform, "conditional")), "parliament must be permanent, independent of changing succession conditions")
    native = one(reform, "states_general_mechanic")
    require([entry[0] for entry in native] == ["gdd_czc_gentry", "gdd_czc_ruler"], "native faction order must be gentry left, ruler right")
    require(float(one(one(native, "gdd_czc_ruler"), "republican_tradition")) < -1, "ruler side must outweigh the republic's +1 base tradition")
    require(not contains(reform, "maintain_dynasty", "yes"), "do not rely on the failed republic maintain_dynasty property")
    succession = one(one(trees["effects"], "gdd_czc_succession_effect"), "if")
    scalar(one(succession, "limit"), ELIGIBLE, "yes")
    require(contains(one(succession, "limit"), "has_country_flag", "gdd_czc_installing_successor"), "missing recursion guard")
    family = one(succession, "if")
    scalar(one(family, "limit"), "is_statists_in_power", "no")
    scalar(one(family, "limit"), "has_country_flag", "gdd_czc_successor_prepared")
    scalar(family, "set_ruler", "gdd_czc_family_successor")
    scalar(succession, "gdd_czc_prepare_successor_effect", "yes")
    prepare = one(trees["effects"], "gdd_czc_prepare_successor_effect")
    scalar(one(prepare, "define_exiled_ruler"), "name", "lastname")
    scalar(one(trees["on_actions"], "on_new_monarch"), "gdd_czc_succession_effect", "yes")

    eligible = one(trees["triggers"], ELIGIBLE)
    scalar(eligible, "tag", "CZC")
    scalar(eligible, "government", "republic")
    scalar(eligible, "has_reform", REFORM)
    require(contains(one(eligible, "NOT"), "has_country_flag", "gdd_czc_crowned"), "crowned countries must stop using council scripts")
    threshold = one(trees["triggers"], CROWN)
    scalar(threshold, ELIGIBLE, "yes")
    require(one(threshold, "NOT") == [("republican_tradition", "=", "20")], "threshold must be strictly below 20; 20 remains republican")
    cooldown = one(trees["triggers"], COOLDOWN)
    scalar(cooldown, ELIGIBLE, "yes")
    scalar(cooldown, "adm_power", "50")
    dates = [body for name, _, body in walk(cooldown) if name == "had_country_flag"]
    require(len(dates) == 1, "shared action cooldown needs one dated flag")
    scalar(dates[0], "flag", "gdd_czc_last_council_action")
    scalar(dates[0], "days", "365")

    effects = trees["effects"]
    require(not any(name in {"define_ruler", "kill_ruler", "set_variable", "change_variable", "define_heir"} for name, _, _ in walk(effects)), "production council effects must not replace rulers or mirror native political state")
    for side, change in (("gentry", "-0.10"), ("ruler", "0.10")):
        body = one(one(effects, f"gdd_czc_support_{side}_effect"), "if")
        scalar(one(body, "limit"), COOLDOWN, "yes")
        hidden = one(body, "hidden_effect")
        scalar(hidden, "change_statists_vs_orangists", change)
        scalar(hidden, "add_adm_power", "-50")
        payments = [(key, value) for key, _, value in walk(body) if key == "add_adm_power"]
        require(payments == [("add_adm_power", "-50")], "each guarded support action must charge exactly 50 ADM once")
        clear = ("clr_country_flag", "=", "gdd_czc_last_council_action")
        set_flag = ("set_country_flag", "=", "gdd_czc_last_council_action")
        require(clear in hidden and set_flag in hidden and hidden.index(clear) < hidden.index(set_flag), "each action must refresh the same cooldown date")
        scalar(hidden, "gdd_czc_check_transition_effect", "yes")
    conversion = one(one(effects, "gdd_czc_proclaim_king_effect"), "if")
    scalar(one(conversion, "limit"), CROWN, "yes")
    scalar(conversion, "change_government", "monarchy")
    scalar(conversion, "add_government_reform", "autocracy_reform")
    require(conversion.index(("set_country_flag", "=", "gdd_czc_crowned")) < conversion.index(("change_government", "=", "monarchy")), "crown callback guard must precede government conversion")
    initialization = one(one(effects, "gdd_czc_initialize_effect"), "if")
    require(contains(one(initialization, "limit"), "has_country_flag", "gdd_czc_council_initialized"), "initialization must be once per campaign/save")
    initial_tradition = one(initialization, "if")
    require(one(one(initial_tradition, "limit"), "NOT") == [("is_date", "=", "1444.11.12")], "initial tradition reset must use the native is_date cutoff at 1444.11.12")
    require(not any(key == "date" for key, _, _ in walk(effects)), "date is not a valid EU4 trigger; use is_date for the historical startup cutoff")
    require(values(initial_tradition, "add_republican_tradition") == ["-100", "50"], "new historical council must start at 50 tradition")
    require(not values(initialization, "add_republican_tradition"), "old saves must not be reset to 50 tradition")
    legacy = one(trees["triggers"], "gdd_czc_should_migrate_legacy_trigger")
    scalar(legacy, "tag", "CZC")
    scalar(legacy, "government", "republic")
    scalar(legacy, "has_reform", "oligarchy_reform")
    excluded = values(legacy, "NOT")
    require(any(contains(body, "has_country_flag", "gdd_czc_crowned") for body in excluded), "legacy migration must not reverse coronation")
    require(any(contains(body, "has_country_flag", "gdd_czc_council_initialized") for body in excluded), "legacy migration must be one-time")
    migration = one(one(effects, "gdd_czc_migrate_legacy_council_effect"), "if")
    scalar(one(migration, "limit"), "gdd_czc_should_migrate_legacy_trigger", "yes")
    require({name for name, _, _ in migration} == {"limit", "remove_government_reform", "add_government_reform"}, "legacy migration must preserve government, ruler and other saved state")
    scalar(migration, "remove_government_reform", "oligarchy_reform")
    scalar(migration, "add_government_reform", REFORM)

    events = {one(body, "id"): body for body in values(trees["events"], "country_event")}
    require(len(events) == len(values(trees["events"], "country_event")), "duplicate CZC event id")
    for event_id, event in events.items():
        scalar(event, "is_triggered_only", "yes")
        # This macOS build reports missing name/description/option even for
        # hidden country_event shells, so preserve the full event contract.
        for key in ("title", "desc", "picture"):
            require(bool(one(event, key)), f"{event_id}: missing {key}")
        require(bool(values(event, "option")), f"{event_id}: missing required event option")
        trigger = one(event, "trigger")
        require(any(contains(trigger, key, value) for key, value in ((ELIGIBLE, "yes"), (CROWN, "yes"), ("tag", "CZC"))), f"{event_id}: unguarded event")
    crown_event = events["gdd_czc_government.20"]
    scalar(one(crown_event, "trigger"), CROWN, "yes")
    scalar(one(crown_event, "immediate"), "gdd_czc_proclaim_king_effect", "yes")
    callbacks = trees["on_actions"]
    require({entry[0] for entry in callbacks} == {"on_startup", "on_monthly_pulse", "on_new_monarch"}, "unexpected council callback")
    for callback, event_id in (("on_startup", "gdd_czc_government.1"), ("on_monthly_pulse", "gdd_czc_government.2")):
        require((event_id, None, None) in one(one(callbacks, callback), "events"), f"missing {callback} initialization/transition hook")
        immediate = one(events[event_id], "immediate")
        route = [(key, "=", "yes") for key in ("gdd_czc_migrate_legacy_council_effect", "gdd_czc_initialize_effect", "gdd_czc_check_transition_effect")]
        require(all(entry in immediate for entry in route) and [immediate.index(entry) for entry in route] == sorted(immediate.index(entry) for entry in route), f"{event_id}: migration, initialization, transition must occur in order")
    references = {value for name, _, value in walk(trees["events"]) if name == "id" and isinstance(value, str)}
    references |= {value for name, _, value in walk(effects) if name == "id" and isinstance(value, str)}
    require(references <= set(events), f"unresolved CZC event references: {references - set(events)}")
    for name, _, value in walk(callbacks + effects):
        event_id = name if value is None else value
        require(not (isinstance(event_id, str) and re.fullmatch(r"gdd_czc_government\.9\d\d", event_id)), "diagnostic event is reachable from production callbacks/effects")


def check_integration(trees: dict) -> None:
    manifest = json.loads((ROOT / "planning/lingnan_nations/lingnan_nations_manifest.json").read_text())
    config = manifest["countries"]["CZC"]
    require(config["government"] == "republic" and config["reform"] == REFORM, "CZC manifest still replays an obsolete reform")
    history = read_tree(MOD / "history/countries" / config["history"])
    scalar(history, "government", "republic")
    scalar(history, "add_government_reform", REFORM)
    for path in (MOD / "history/countries").glob("*.txt"):
        if path.name != config["history"]:
            require(REFORM not in path.read_bytes().decode("latin-1"), f"unrelated country has CZC reform: {path.name}")
    government = one(read_tree(MOD / "common/governments/00_governments.txt"), "republic")
    tier = one(one(one(government, "reform_levels"), "oligarchy_merchant_class_noble_elite"), "reforms")
    require((REFORM, None, None) in tier, "CZC reform missing from republic tier one")
    upstream = read_tree(effective(PATHS["reforms"].replace("zzz_gdd_czc_government_reforms.txt", "02_government_reforms_republics.txt"), False))
    inherited = read_tree(MOD / "common/government_reforms/02_government_reforms_republics.txt")
    require(one(inherited, "dutch_republic") == one(upstream, "dutch_republic"), "native Dutch Republic mechanics changed outside CZC scope")


def check_localisation(trees: dict) -> int:
    sources = [MOD / "localisation_source" / SOURCE]
    if "custom_gui" in trees:
        ui_sources = sorted((MOD / "localisation_source").glob("020_*czc*"))
        require(len(ui_sources) == 1, "expected one dedicated 020 CZC interface localisation source")
        sources.extend(ui_sources)
    names = []
    for source in sources:
        require(source.name in FILES, f"{source.name}: localisation is not registered with the encoding tool")
        verify_file(source, MOD / "localisation" / FILES[source.name])
        text = source.read_text(encoding="utf-8-sig")
        require(text.startswith("l_english:\n"), f"{source.name}: localisation must use l_english")
        names.extend(re.findall(r"(?m)^\s*([\w.]+):\d+\s+\"", text))
    require(len(names) == len(set(names)), "duplicate CZC localisation key")
    references = {REFORM, REFORM + "_desc", "gdd_czc_gentry", "gdd_czc_ruler"}
    for tree in trees.values():
        for key, _, value in walk(tree):
            if key in {"title", "desc", "custom_tooltip", "tooltip", "buttonText", "text"} and isinstance(value, str) and value.startswith(PREFIX):
                references.add(value)
    for event in values(trees["events"], "country_event"):
        references.update(one(option, "name") for option in values(event, "option") if one(option, "name").startswith(PREFIX))
    if "custom_gui" in trees:
        references.update(one(body, "name") for body in values(trees["custom_gui"], "custom_text_box"))
    require(references <= set(names), f"missing CZC localisation: {sorted(references - set(names))}")
    return len(names)


def check_references(trees: dict) -> None:
    definitions = {name for kind in ("triggers", "effects") for name, _, _ in trees[kind]}
    calls = {name for tree in trees.values() for name, _, _ in walk(tree) if name.startswith(PREFIX) and name.endswith(("_trigger", "_effect"))}
    require(calls <= definitions, f"unresolved script calls: {sorted(calls - definitions)}")
    # An event picture or reform icon can name a native sprite. Resolve the
    # effective file stack, rather than accepting a plausible-looking name.
    gfx_files = {}
    for root in (VANILLA, *DEPENDENCIES, MOD):
        for path in (root / "interface").glob("*.gfx"):
            gfx_files[path.name] = path
    sprite_names = set()
    for path in gfx_files.values():
        sprite_names.update(re.findall(r'\bname\s*=\s*"([^"\n]+)"', path.read_bytes().decode("latin-1")))
    pictures = {value for key, _, value in walk(trees["events"]) if key == "picture" and isinstance(value, str)}
    reform_icon = one(one(trees["reforms"], REFORM), "icon")
    pictures.add("government_reform_" + reform_icon)
    require(pictures <= sprite_names, f"undefined event picture/reform icon sprites: {sorted(pictures - sprite_names)}")


def strip_custom(tree: list) -> list:
    result = []
    for name, operation, value in tree:
        if isinstance(value, list):
            names = values(value, "name")
            if names and names[0].startswith((PREFIX, "gdd_hak_", "zhx_feudatory_")):
                continue
            value = strip_custom(value)
        result.append((name, operation, value))
    return result


def check_ui(trees: dict) -> tuple[int, int]:
    gui = named_controls(trees["gui"])
    bindings = named_controls(trees["custom_gui"])
    require(bool(gui), "no CZC government controls")
    require(set(gui) == set(bindings), f"GUI/custom_gui control mismatch: {set(gui) ^ set(bindings)}")
    for name, (kind, body) in gui.items():
        scalar(body, "scripted", "yes")
        binding_type, binding = bindings[name]
        potential = one(binding, "potential")
        require(contains(potential, ELIGIBLE, "yes"), f"{name}: visual is not guarded by the CZC council gate")
        if binding_type == "custom_button" and values(binding, "effect"):
            require(contains(one(binding, "trigger"), COOLDOWN, "yes"), f"{name}: action bypasses the shared cooldown")
    require(strip_custom(trees["gui"]) == read_tree(effective(PATHS["gui"], False)), "inherited native government GUI changed outside the CZC additions")
    graphics = one(trees["gfx"], "spriteTypes")
    sprites = {one(body, "name"): body for kind, _, body in graphics if isinstance(body, list) and values(body, "name")}
    require(len(sprites) == len(graphics), "duplicate or unsupported CZC GFX declaration")
    sprite_references = {value for tree in (trees["gui"], trees["custom_gui"]) for key, _, value in walk(tree) if key in {"spriteType", "quadTextureSprite", "sprite"} and isinstance(value, str) and PREFIX in value}
    require(sprite_references <= set(sprites), f"undefined CZC sprites: {sprite_references - set(sprites)}")
    textures = set()
    for name, sprite in sprites.items():
        textures.add(one(sprite, "texturefile").replace("//", "/"))
        texture = MOD / one(sprite, "texturefile").replace("//", "/")
        require(texture.is_file(), f"{name}: missing {texture}")
        data = texture.read_bytes()
        require(data[:4] == b"DDS " and len(data) >= 128, f"{texture.name}: invalid DDS header")
        header_size, _, height, width = struct.unpack_from("<4I", data, 4)
        require(header_size == 124 and width > 0 and height > 0, f"{texture.name}: invalid DDS dimensions")
        frames = int((values(sprite, "noOfFrames") or ["1"])[0])
        require(frames > 0 and width % frames == 0, f"{texture.name}: width {width} cannot hold {frames} equal horizontal frames")
        if texture.name in ASSET_DIMENSIONS:
            require((width, height, frames) == ASSET_DIMENSIONS[texture.name], f"{texture.name}: expected width/height/frames {ASSET_DIMENSIONS[texture.name]}, got {(width, height, frames)}")
        require(width <= 16384 and height <= 16384, f"{texture.name}: exceeds conservative texture size limit")
        for control, (_, body) in gui.items():
            if contains(body, "spriteType", name) or contains(body, "quadTextureSprite", name):
                for frame in values(body, "frame"):
                    require(1 <= int(frame) <= frames, f"{control}: frame {frame} exceeds {frames}")
                for frame in values(bindings[control][1], "frame"):
                    number = int(one(frame, "number"))
                    require(1 <= number <= frames, f"{control}: dynamic frame {number} exceeds {frames}")
        four_cc = data[84:88]
        if four_cc in {b"DXT1", b"DXT3", b"DXT5"}:
            minimum = ((width + 3) // 4) * ((height + 3) // 4) * (8 if four_cc == b"DXT1" else 16)
            require(len(data) >= 128 + minimum, f"{texture.name}: truncated DDS pixel payload")
        elif four_cc == b"\0\0\0\0":
            bit_count = struct.unpack_from("<I", data, 88)[0]
            require(bit_count in {8, 16, 24, 32}, f"{texture.name}: unsupported raw DDS pixel format")
            require(len(data) >= 128 + width * height * bit_count // 8, f"{texture.name}: truncated raw DDS pixels")
        else:
            raise ValueError(f"{texture.name}: unverified EU4 DDS compression {four_cc!r}")
    require(set(ASSET_DIMENSIONS) <= {Path(texture).name for texture in textures}, "a required council asset is not registered with GFX")
    pointer = bindings["gdd_czc_power_pointer"][1]
    pointer_frames = values(pointer, "frame")
    require(len(pointer_frames) == 21, "power pointer must cover all 21 native balance bins")
    thresholds = []
    for frame in pointer_frames[:-1]:
        threshold = float(one(one(frame, "trigger"), "statists_vs_orangists"))
        thresholds.append(threshold)
        require(int(one(frame, "number")) == round((threshold + 1) * 10) + 1, "pointer artwork frame runs opposite to the native balance")
    require(thresholds == sorted(thresholds, reverse=True) and len(set(thresholds)) == 20, "thresholds must descend so the first eligible pointer frame is the correct bin")
    require(abs(thresholds[0] - 1) < 1e-9 and abs(thresholds[-1] + 0.9) < 1e-9, "pointer must cover both native range endpoints")
    scalar(pointer_frames[-1], "number", "1")
    require(one(pointer_frames[-1], "trigger") == [("always", "=", "yes")], "pointer needs a final fallback for the far-left endpoint")
    # Ready/cooling text shares one rectangle; it must never overlap itself.
    ready = one(bindings["gdd_czc_action_ready"][1], "potential")
    cooling = one(bindings["gdd_czc_action_cooling"][1], "potential")
    scalar(ready, COOLDOWN, "yes")
    require(one(cooling, "NOT") == [(COOLDOWN, "=", "yes")], "ready/cooling visibility must remain complementary")
    return len(gui), len(textures)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mechanics-only", action="store_true", help="check script contracts while GUI/assets are being integrated")
    args = parser.parse_args()
    paths = {key: relative for key, relative in PATHS.items() if not args.mechanics_only or key not in {"gui", "custom_gui", "gfx"}}
    try:
        trees = {key: read_tree(MOD / relative) for key, relative in paths.items()}
        check_mechanics(trees)
        check_references(trees)
        check_integration(trees)
        localisations = check_localisation(trees)
        print(f"PASS: CZC-only eligibility, lifelong terms, guarded family succession, shared cooldown, strict RT <20 transition, manifest/history/tier, script references, {localisations} encoded localisation keys")
        if not args.mechanics_only:
            controls, textures = check_ui(trees)
            print(f"PASS: {controls} scripted controls and {textures} DDS textures; inherited government view and Dutch reform preserved")
        print("Static contracts only; runtime results and remaining coverage are recorded separately in docs/gameplay/11_chaozhou_government.md.")
        return 0
    except (OSError, ValueError, KeyError, IndexError, TypeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

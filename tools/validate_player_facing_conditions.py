#!/usr/bin/env python3
"""Reject raw project internals on player-facing decision/event conditions.

EU4 expands an ordinary decision ``allow`` block and an event option
``trigger`` into native requirement text.  A raw ``zhx_*``/``gdd_*`` flag,
variable, or scripted trigger in either surface therefore produces the kind of
developer-facing tooltip that this project does not want players to see.

The audit is intentionally narrow to keep false positives low:

* only project decisions (names beginning with ``zhx_`` or ``gdd_``) are read;
* their direct ``allow`` and ``effect`` blocks are checked;
* visible production event option ``trigger`` and effect surfaces are checked;
* debug/test files and hidden events are ignored;
* religion, culture, school, modifier, tag, and event-target identifiers are
  not treated as leaks merely because they use a project prefix;
* conditions inside ``custom_trigger_tooltip`` or ``hidden_trigger`` are safe.

Use ``custom_trigger_tooltip`` for a condition the player should understand.
Use ``hidden_trigger`` only for routing/AI state that should not be presented.
This validator is structural; it does not prove that the Chinese prose is good.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"
DECISION_DIR = MOD / "decisions"
EVENT_DIR = MOD / "events"
LOCALISATION_SOURCE_DIR = MOD / "localisation_source"

PROJECT_PREFIXES = ("zhx_", "gdd_")
DECISION_CONTAINERS = {"country_decisions", "province_decisions"}
EVENT_BLOCKS = {"country_event", "province_event"}
PROTECTED_WRAPPERS = {"custom_trigger_tooltip", "hidden_trigger"}
EFFECT_PROTECTED_BLOCKS = {"hidden_effect", "trigger", "ai_chance"}
EXCLUDED_NAME_PARTS = ("debug", "test")

BLOCK_RE = re.compile(r"\b([A-Za-z0-9_.:-]+)\s*=\s*\{")
SCALAR_RE_TEMPLATE = r"\b{key}\s*=\s*([^\s{{}}#]+)"

SUSPICIOUS_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "internal flag",
        re.compile(
            r"\b(?:has|had)_(?:country|province|global|ruler)_flag\s*=\s*"
            r"(?:zhx_|gdd_)[A-Za-z0-9_]+"
        ),
    ),
    (
        "internal flag",
        re.compile(r"\bflag\s*=\s*(?:zhx_|gdd_)[A-Za-z0-9_]+"),
    ),
    (
        "internal variable",
        re.compile(
            r"\b(?:which|has_variable)\s*=\s*(?:zhx_|gdd_)[A-Za-z0-9_]+"
        ),
    ),
    (
        "project scripted trigger",
        re.compile(r"\b(?:zhx_|gdd_)[A-Za-z0-9_]+\s*=\s*(?:yes|no)\b"),
    ),
)

SUSPICIOUS_EFFECT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "internal flag mutation",
        re.compile(
            r"\b(?:set|clr)_(?:country|province|global|ruler)_flag\s*=\s*"
            r"(?:zhx_|gdd_)[A-Za-z0-9_]+"
        ),
    ),
    (
        "internal variable operation",
        re.compile(r"\bwhich\s*=\s*(?:zhx_|gdd_)[A-Za-z0-9_]+"),
    ),
    (
        "project scripted effect",
        re.compile(r"\b(?:zhx_|gdd_)[A-Za-z0-9_]+\s*=\s*(?:yes|no)\b"),
    ),
)


@dataclass(frozen=True)
class Block:
    key: str
    start: int
    opening: int
    closing: int

    @property
    def body_start(self) -> int:
        return self.opening + 1

    @property
    def body_end(self) -> int:
        return self.closing


@dataclass(frozen=True)
class Finding:
    path: Path
    offset: int
    surface: str
    kind: str
    snippet: str


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    decision_allows: int = 0
    decision_effects: int = 0
    event_option_triggers: int = 0
    event_option_effects: int = 0
    protected_tooltips: int = 0
    hidden_routes: int = 0
    excluded_files: int = 0
    hidden_events: int = 0

    def finish(self) -> None:
        if self.errors or self.findings:
            total = len(self.errors) + len(self.findings)
            print(f"Player-facing condition readability: FAIL ({total})")
            for index, error in enumerate(self.errors, 1):
                print(f"  E{index:02d}. {error}")
            for index, finding in enumerate(self.findings, 1):
                line = line_number(finding.path, finding.offset)
                print(
                    f"  F{index:02d}. {relative(finding.path)}:{line}: "
                    f"{finding.surface} exposes {finding.kind}: "
                    f"`{finding.snippet}`"
                )
            print(
                "  Fix: wrap player-readable logic in custom_trigger_tooltip; "
                "wrap pure routing/AI state in hidden_trigger; hide internal "
                "writes in hidden_effect and describe outcomes with custom_tooltip."
            )
            raise SystemExit(1)

        print("Player-facing condition readability: PASS")
        print(
            f"  Checked {self.decision_allows} decision allow blocks, "
            f"{self.decision_effects} decision effects, "
            f"{self.event_option_triggers} visible option triggers, and "
            f"{self.event_option_effects} visible option effect surfaces"
        )
        print(
            f"  Accepted {self.protected_tooltips} localized condition wrappers and "
            f"{self.hidden_routes} hidden routing wrappers"
        )
        print(
            f"  Excluded {self.excluded_files} debug/test files and "
            f"{self.hidden_events} hidden events"
        )


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_script(path: Path, report: Report) -> str:
    try:
        data = path.read_bytes()
    except OSError as exc:
        report.errors.append(f"cannot read {relative(path)}: {exc}")
        return ""

    # Some vanilla-derived event files use legacy Chinese bytes.  Project
    # identifiers and Clausewitz punctuation are ASCII, so a lossless Latin-1
    # fallback remains safe for this structural audit.
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def mask_clausewitz(text: str) -> str:
    """Mask comments and quoted strings while preserving all offsets."""

    output = list(text)
    in_string = False
    in_comment = False
    escaped = False
    for index, char in enumerate(text):
        if in_comment:
            if char == "\n":
                in_comment = False
            else:
                output[index] = " "
            continue
        if in_string:
            if char != "\n":
                output[index] = " "
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == "#":
            output[index] = " "
            in_comment = True
        elif char == '"':
            output[index] = " "
            in_string = True
    return "".join(output)


def depth_before(masked: str) -> list[int]:
    depths: list[int] = []
    depth = 0
    for char in masked:
        depths.append(depth)
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
    return depths


def closing_brace(masked: str, opening: int) -> int | None:
    depth = 0
    for index in range(opening, len(masked)):
        if masked[index] == "{":
            depth += 1
        elif masked[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    return None


def iter_direct_blocks(text: str, keys: set[str] | None = None) -> Iterator[Block]:
    """Yield blocks whose assignment is at depth zero in ``text``.

    Unlike line-oriented helpers, this also understands compact one-line event
    options such as ``option = { name = foo trigger = { ... } }``.
    """

    masked = mask_clausewitz(text)
    depths = depth_before(masked)
    for match in BLOCK_RE.finditer(masked):
        key = match.group(1)
        if depths[match.start()] != 0 or (keys is not None and key not in keys):
            continue
        opening = masked.find("{", match.start(), match.end())
        closing = closing_brace(masked, opening)
        if closing is not None:
            yield Block(key=key, start=match.start(), opening=opening, closing=closing)


def iter_all_blocks(text: str, keys: set[str]) -> Iterator[Block]:
    masked = mask_clausewitz(text)
    for match in BLOCK_RE.finditer(masked):
        key = match.group(1)
        if key not in keys:
            continue
        opening = masked.find("{", match.start(), match.end())
        closing = closing_brace(masked, opening)
        if closing is not None:
            yield Block(key=key, start=match.start(), opening=opening, closing=closing)


def direct_scalar(text: str, key: str) -> str | None:
    masked = mask_clausewitz(text)
    depths = depth_before(masked)
    pattern = re.compile(SCALAR_RE_TEMPLATE.format(key=re.escape(key)))
    for match in pattern.finditer(masked):
        if depths[match.start()] == 0:
            return match.group(1)
    return None


def is_project_name(name: str) -> bool:
    return name.startswith(PROJECT_PREFIXES)


def is_excluded_name(name: str) -> bool:
    lowered = name.lower()
    return lowered.startswith("zzz_") or any(part in lowered for part in EXCLUDED_NAME_PARTS)


def protected_intervals(text: str, report: Report, localisation_keys: set[str]) -> list[tuple[int, int]]:
    intervals: list[tuple[int, int]] = []
    for wrapper in iter_all_blocks(text, PROTECTED_WRAPPERS):
        intervals.append((wrapper.start, wrapper.closing + 1))
        body = text[wrapper.body_start : wrapper.body_end]
        if wrapper.key == "hidden_trigger":
            report.hidden_routes += 1
            continue

        report.protected_tooltips += 1
        tooltip = direct_scalar(body, "tooltip")
        if tooltip is None:
            report.errors.append("custom_trigger_tooltip is missing a direct tooltip key")
        elif is_project_name(tooltip) and tooltip not in localisation_keys:
            report.errors.append(
                f"custom_trigger_tooltip references missing readable localisation `{tooltip}`"
            )
    return intervals


def suspicious_conditions(text: str, protected: Iterable[tuple[int, int]]) -> list[tuple[int, str, str]]:
    masked = mask_clausewitz(text)
    protected_list = list(protected)
    matches: list[tuple[int, str, str]] = []
    seen: set[tuple[int, str]] = set()
    for kind, pattern in SUSPICIOUS_PATTERNS:
        for match in pattern.finditer(masked):
            if any(start <= match.start() < end for start, end in protected_list):
                continue
            snippet = " ".join(match.group(0).split())
            identity = (match.start(), snippet)
            if identity in seen:
                continue
            seen.add(identity)
            matches.append((match.start(), kind, snippet))
    return sorted(matches)


def suspicious_effects(text: str, protected: Iterable[tuple[int, int]]) -> list[tuple[int, str, str]]:
    masked = mask_clausewitz(text)
    protected_list = list(protected)
    matches: list[tuple[int, str, str]] = []
    seen: set[tuple[int, str]] = set()
    for kind, pattern in SUSPICIOUS_EFFECT_PATTERNS:
        for match in pattern.finditer(masked):
            if any(start <= match.start() < end for start, end in protected_list):
                continue
            snippet = " ".join(match.group(0).split())
            identity = (match.start(), snippet)
            if identity in seen:
                continue
            seen.add(identity)
            matches.append((match.start(), kind, snippet))
    return sorted(matches)


def localisation_keys(report: Report) -> set[str]:
    keys: set[str] = set()
    if not LOCALISATION_SOURCE_DIR.is_dir():
        report.errors.append(
            f"missing localisation source directory: {relative(LOCALISATION_SOURCE_DIR)}"
        )
        return keys
    pattern = re.compile(r"(?m)^\s*([^\s:#]+):\d+\s+")
    for path in sorted(LOCALISATION_SOURCE_DIR.glob("*.txt")):
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            report.errors.append(f"cannot read readable localisation {relative(path)}: {exc}")
            continue
        keys.update(pattern.findall(text))
    return keys


def inspect_surface(
    *,
    path: Path,
    full_text: str,
    body: str,
    body_absolute_start: int,
    surface: str,
    report: Report,
    localisation: set[str],
) -> None:
    protected = protected_intervals(body, report, localisation)
    for offset, kind, snippet in suspicious_conditions(body, protected):
        report.findings.append(
            Finding(
                path=path,
                offset=body_absolute_start + offset,
                surface=surface,
                kind=kind,
                snippet=snippet,
            )
        )


def inspect_effect_surface(
    *,
    path: Path,
    body: str,
    body_absolute_start: int,
    surface: str,
    report: Report,
    localisation: set[str],
) -> None:
    tooltip = direct_scalar(body, "custom_tooltip")
    if tooltip is not None and is_project_name(tooltip) and tooltip not in localisation:
        report.errors.append(
            f"custom_tooltip references missing readable localisation `{tooltip}`"
        )
    protected = [
        (wrapper.start, wrapper.closing + 1)
        for wrapper in iter_all_blocks(body, EFFECT_PROTECTED_BLOCKS)
    ]
    for offset, kind, snippet in suspicious_effects(body, protected):
        report.findings.append(
            Finding(
                path=path,
                offset=body_absolute_start + offset,
                surface=surface,
                kind=kind,
                snippet=snippet,
            )
        )


def validate_decisions(report: Report, localisation: set[str]) -> None:
    for path in sorted(DECISION_DIR.glob("*.txt")):
        if is_excluded_name(path.stem):
            report.excluded_files += 1
            continue
        text = read_script(path, report)
        for container in iter_direct_blocks(text, DECISION_CONTAINERS):
            container_body = text[container.body_start : container.body_end]
            for decision in iter_direct_blocks(container_body):
                if not is_project_name(decision.key) or is_excluded_name(decision.key):
                    continue
                decision_body = container_body[decision.body_start : decision.body_end]
                for allow in iter_direct_blocks(decision_body, {"allow"}):
                    report.decision_allows += 1
                    allow_body = decision_body[allow.body_start : allow.body_end]
                    absolute = (
                        container.body_start
                        + decision.body_start
                        + allow.body_start
                    )
                    inspect_surface(
                        path=path,
                        full_text=text,
                        body=allow_body,
                        body_absolute_start=absolute,
                        surface=f"decision `{decision.key}` allow",
                        report=report,
                        localisation=localisation,
                    )
                for effect in iter_direct_blocks(decision_body, {"effect"}):
                    report.decision_effects += 1
                    effect_body = decision_body[effect.body_start : effect.body_end]
                    absolute = (
                        container.body_start
                        + decision.body_start
                        + effect.body_start
                    )
                    inspect_effect_surface(
                        path=path,
                        body=effect_body,
                        body_absolute_start=absolute,
                        surface=f"decision `{decision.key}` effect",
                        report=report,
                        localisation=localisation,
                    )


def event_is_hidden(event_body: str) -> bool:
    return direct_scalar(event_body, "hidden") == "yes" or direct_scalar(
        event_body, "hide_window"
    ) == "yes"


def event_is_ai_only(event_body: str) -> bool:
    """Exclude events whose direct event trigger is unconditionally AI-only."""

    for trigger in iter_direct_blocks(event_body, {"trigger"}):
        trigger_body = event_body[trigger.body_start : trigger.body_end]
        if direct_scalar(trigger_body, "ai") == "yes":
            return True
    return False


def validate_events(report: Report, localisation: set[str]) -> None:
    for path in sorted(EVENT_DIR.glob("*.txt")):
        if is_excluded_name(path.stem):
            report.excluded_files += 1
            continue
        text = read_script(path, report)
        for event in iter_direct_blocks(text, EVENT_BLOCKS):
            event_body = text[event.body_start : event.body_end]
            event_id = direct_scalar(event_body, "id") or "<unnamed>"
            if is_excluded_name(event_id):
                continue
            if event_is_hidden(event_body) or event_is_ai_only(event_body):
                report.hidden_events += 1
                continue

            option_index = 0
            for option in iter_direct_blocks(event_body, {"option"}):
                option_index += 1
                option_body = event_body[option.body_start : option.body_end]
                option_name = direct_scalar(option_body, "name") or f"option#{option_index}"
                for trigger in iter_direct_blocks(option_body, {"trigger"}):
                    report.event_option_triggers += 1
                    trigger_body = option_body[trigger.body_start : trigger.body_end]
                    absolute = event.body_start + option.body_start + trigger.body_start
                    inspect_surface(
                        path=path,
                        full_text=text,
                        body=trigger_body,
                        body_absolute_start=absolute,
                        surface=f"event `{event_id}` option `{option_name}` trigger",
                        report=report,
                        localisation=localisation,
                    )
                report.event_option_effects += 1
                absolute = event.body_start + option.body_start
                inspect_effect_surface(
                    path=path,
                    body=option_body,
                    body_absolute_start=absolute,
                    surface=f"event `{event_id}` option `{option_name}` effect",
                    report=report,
                    localisation=localisation,
                )


def line_number(path: Path, offset: int) -> int:
    try:
        data = path.read_bytes()
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = data.decode("latin-1")
    except OSError:
        return 0
    return text.count("\n", 0, offset) + 1


def parser_self_test() -> None:
    sample = """
has_country_flag = zhx_raw_flag
check_variable = { which = gdd_raw_value value = 1 }
zhx_complex_requirement = yes
religion = zhx_lijiao
has_religious_school = zhx_ru_school
custom_trigger_tooltip = {
    tooltip = zhx_readable_tt
    zhx_wrapped_requirement = yes
}
hidden_trigger = { has_global_flag = zhx_route_only }
"""
    protected = []
    for wrapper in iter_all_blocks(sample, PROTECTED_WRAPPERS):
        protected.append((wrapper.start, wrapper.closing + 1))
    found = [snippet for _, _, snippet in suspicious_conditions(sample, protected)]
    expected = {
        "has_country_flag = zhx_raw_flag",
        "which = gdd_raw_value",
        "zhx_complex_requirement = yes",
    }
    if set(found) != expected:
        raise AssertionError(f"condition parser self-test failed: {found!r}")

    compact = "option = { name = x trigger = { zhx_raw = yes } }"
    option = next(iter_direct_blocks(compact, {"option"}))
    option_body = compact[option.body_start : option.body_end]
    trigger = next(iter_direct_blocks(option_body, {"trigger"}))
    trigger_body = option_body[trigger.body_start : trigger.body_end]
    if not suspicious_conditions(trigger_body, []):
        raise AssertionError("inline option parser self-test failed")

    effect_sample = """
set_country_flag = zhx_raw_effect_flag
change_variable = { which = zhx_raw_effect_value value = 1 }
zhx_raw_scripted_effect = yes
hidden_effect = { zhx_hidden_effect = yes }
"""
    protected_effects = [
        (wrapper.start, wrapper.closing + 1)
        for wrapper in iter_all_blocks(effect_sample, EFFECT_PROTECTED_BLOCKS)
    ]
    effect_found = {snippet for _, _, snippet in suspicious_effects(effect_sample, protected_effects)}
    if effect_found != {
        "set_country_flag = zhx_raw_effect_flag",
        "which = zhx_raw_effect_value",
        "zhx_raw_scripted_effect = yes",
    }:
        raise AssertionError(f"effect parser self-test failed: {sorted(effect_found)!r}")


def main() -> None:
    parser_self_test()
    report = Report()
    readable_keys = localisation_keys(report)
    validate_decisions(report, readable_keys)
    validate_events(report, readable_keys)
    report.finish()


if __name__ == "__main__":
    main()

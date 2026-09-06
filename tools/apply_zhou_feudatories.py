#!/usr/bin/env python3
"""Apply the reviewed opening dignity catalogue without touching encoded names."""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"
MANIFEST = ROOT / "planning/zhou_feudatories/opening_dignities.json"


def render(data: bytes, entry: dict) -> bytes:
    # Work byte-for-byte: character names in country history use EU4's escaped
    # Chinese encoding. Only ASCII opening government assignments are changed.
    split = re.search(rb"(?m)^\s*\d+\.\d+\.\d+\s*=\s*\{", data)
    end = split.start() if split else len(data)
    before, after = data[:end], data[end:]
    reform = f"zhx_feudatory_{entry['dignity']}_reform".encode()
    rank = b"2" if entry["dignity"] == "gong" else b"1"
    for field, value in ((b"add_government_reform", reform), (b"government_rank", rank)):
        pattern = rb"(?m)^" + field + rb"\s*=\s*[^\r\n#]+"
        if re.search(pattern, before):
            before = re.sub(pattern, field + b" = " + value, before, count=1)
        else:
            line = b"\r\n" if b"\r\n" in before else b"\n"
            before = field + b" = " + value + line + before
    # Setting the base government clears reforms already applied by history.
    # Ming has no opening reform in the inherited file, so prepending its new
    # reform above `government = monarchy` silently loses the intended dignity.
    government = re.search(rb"(?m)^government\s*=[^\r\n]*(?:\r?\n|$)", before)
    reform_line = re.search(rb"(?m)^add_government_reform\s*=[^\r\n]*(?:\r?\n|$)", before)
    if government and reform_line and reform_line.start() < government.start():
        assignment = reform_line.group()
        before = before[:reform_line.start()] + before[reform_line.end():]
        government = re.search(rb"(?m)^government\s*=[^\r\n]*(?:\r?\n|$)", before)
        before = before[:government.end()] + assignment + before[government.end():]
    return before + after


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    catalog = json.loads(MANIFEST.read_text())
    stale = []
    for tag, entry in catalog["countries"].items():
        path = MOD / "history/countries" / entry["history"]
        data = path.read_bytes()
        result = render(data, entry)
        if result != data:
            if args.check:
                stale.append(tag)
            else:
                path.write_bytes(result)
    if stale:
        raise SystemExit("stale Zhou opening governments: " + ", ".join(stale))
    print(f"ZHOU_FEUDATORIES_VALID; countries={len(catalog['countries'])}; excluded=TSF,republics,Tianzi")


if __name__ == "__main__":
    main()

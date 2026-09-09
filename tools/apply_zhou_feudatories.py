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


def opening_sizes():
    """Read effective 1444 ownership/development; do not mutate map history."""
    from collections import defaultdict
    import validate_czc_government as cw
    files = {}
    for root in (cw.VANILLA, *cw.DEPENDENCIES, MOD):
        for path in sorted((root / 'history/provinces').glob('*.txt')):
            match = re.match(r'(\d+)', path.name)
            if match:
                files[int(match[1])] = path
    totals = defaultdict(lambda: {'development': 0, 'cities': 0})
    start = (1444, 11, 11)
    for path in files.values():
        tree = cw.read_tree(path)
        state = {k: v for k, _, v in tree if not isinstance(v, list)}
        dated = [(tuple(map(int, k.split('.'))), body) for k, _, body in tree
                 if re.fullmatch(r'\d+\.\d+\.\d+', k) and isinstance(body, list)]
        for date, body in sorted(dated, key=lambda item: item[0]):
            if date <= start:
                for k, _, v in body:
                    if not isinstance(v, list):
                        state[k] = v
        tag = state.get('owner')
        if not tag or tag == '---':
            continue
        totals[tag]['development'] += sum(float(state.get(k, 0)) for k in ('base_tax', 'base_production', 'base_manpower'))
        if state.get('is_city') != 'no' and float(state.get('colony_size', 1000)) >= 1000:
            totals[tag]['cities'] += 1
    return dict(totals)


def project_catalog(catalog):
    import copy
    result = copy.deepcopy(catalog)
    sizes = opening_sizes()
    chu_path = ROOT / 'planning/opening_backgrounds/chu_opening_manifest.json'
    chu_bo = {r['tag'] for r in json.loads(chu_path.read_text())['countries'] if r['tag'] not in ('CHC', 'TSF')}
    for tag, entry in result['countries'].items():
        entry.setdefault('pre_zi_dignity', entry['dignity'])
        explicit = entry['basis'].startswith('explicit') or tag in chu_bo or 'user correction' in entry['basis']
        entry.setdefault('opening_policy', 'explicit' if explicit else 'scale' if entry['pre_zi_dignity'] == 'bo' else 'retained')
        entry['opening_size'] = sizes[tag]
        if entry['opening_policy'] == 'scale':
            entry['dignity'] = 'zi' if sizes[tag]['development'] < 50 or sizes[tag]['cities'] < 5 else 'bo'
    result['scope'] = 'Opening Zhou monarchies; explicit dignities preserved, otherwise former Bo below 50 development or five cities enter as Zi.'
    return result


def render_opening_triggers(text, catalog):
    for name, dignity in [('is_opening_country', None), ('opening_zi', 'zi'), ('opening_bo', 'bo'), ('opening_hou', 'hou'), ('opening_gong', 'gong')]:
        key = 'zhx_feudatory_' + name
        tags = [tag for tag, entry in catalog['countries'].items() if dignity is None or entry['dignity'] == dignity]
        block = key + ' = {\n    OR = {\n' + ''.join('        tag = ' + tag + '\n' for tag in tags) + '    }\n}\n'
        pattern = r'(?ms)^' + key + r' = \{\n    OR = \{\n.*?^    \}\n\}\n'
        if re.search(pattern, text):
            text = re.sub(pattern, lambda _: block, text, count=1)
        else:
            text += '\n' + block
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    old_catalog = json.loads(MANIFEST.read_text())
    catalog = project_catalog(old_catalog)
    stale = []
    if catalog != old_catalog:
        if args.check:
            stale.append('opening catalogue/size projection')
        else:
            MANIFEST.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    triggers = MOD / 'common/scripted_triggers/zhx_feudatory_triggers.txt'
    old_triggers = triggers.read_text()
    new_triggers = render_opening_triggers(old_triggers, catalog)
    if old_triggers != new_triggers:
        if args.check:
            stale.append('opening triggers')
        else:
            triggers.write_text(new_triggers)
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

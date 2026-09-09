#!/usr/bin/env python3
"""Project the reviewed Chu setup without changing province ownership or borders."""
import argparse
import json
import re
from build_lingnan_opening_events import ROOT, MOD, CHU_MANIFEST
from apply_zhou_feudatories import render as render_dignity


def render():
    rows = json.loads(CHU_MANIFEST.read_text())['countries']
    catalog = json.loads((ROOT / 'planning/zhou_feudatories/opening_dignities.json').read_text())['countries']
    outputs = {}
    for row in rows:
        path = MOD / 'history/countries' / row['history_file']
        data = path.read_bytes()
        data, count = re.subn(rb'(?m)^primary_culture\s*=\s*\w+',
                              ('primary_culture = ' + row['culture']).encode(), data)
        assert count == 1
        if row['tag'] in catalog:
            data = render_dignity(data, catalog[row['tag']])
        outputs[path] = data
    path = MOD / 'history/diplomacy/gdd_b52_chu_vassals.txt'
    text = path.read_text()
    if not re.search(r'second\s*=\s*HNG\b', text):
        text += '\n# Huguang setting: Heng is a Chu fief at the 1444 opening.\nvassal = {\n\tfirst = CHC\n\tsecond = HNG\n\tstart_date = 1444.1.1\n\tend_date = 1821.1.1\n}\n'
    outputs[path] = text.encode()
    schools = json.loads((ROOT / 'planning/religion_opening_schools/opening_schools_manifest.json').read_text())['schools']
    for row in rows:
        assert row['tag'] in schools[row['school']]['tags'], row['tag']
    path = MOD / 'events/zhx_opening_school_events.txt'
    text = path.read_text()
    # Preserve the initializer's scope, eligibility, practice tiers and native
    # synchronization. Only replace each six-way branch's tag projection.
    for school, config in schools.items():
        pattern = (r'(OR\s*=\s*\{)\s*(?:tag\s*=\s*\w+\s*)+'
                   r'(\}\s*\}\s*set_country_flag\s*=\s*zhx_doctrine_' + school + r'\b)')
        body = '\n' + ''.join('                        tag = ' + tag + '\n' for tag in config['tags']) + '                    '
        text, count = re.subn(pattern, lambda m: m[1] + body + m[2], text)
        assert count == 1, school
    outputs[path] = text.encode()
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for path, data in render().items():
        if args.check:
            assert path.read_bytes() == data, f'stale setup: {path}'
        else:
            path.write_bytes(data)
    print('Chu opening setup: 10 cultures/schools, reviewed dignities and Heng affiliation checked.')


if __name__ == '__main__':
    main()

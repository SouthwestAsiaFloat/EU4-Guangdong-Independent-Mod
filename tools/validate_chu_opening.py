#!/usr/bin/env python3
"""Source/lore and existing-content regression checks for the Chu opening batch."""
import hashlib
import json
import re
import validate_czc_government as cw
from build_lingnan_opening_events import ROOT, MOD, CHU_MANIFEST
from encode_eu4_chinese_localisation import from_escaped_bytes
from apply_chu_opening_setup import render


def main():
    data = json.loads(CHU_MANIFEST.read_text())
    rows = data['countries']
    assert [r['tag'] for r in rows] == ['CHC','CSA','HNG','ZHU','QVN','ACG','EGU','NCH','LCH','TSF']
    assert [r['event_id'] for r in rows] == [f'zhx_opening.{n}' for n in range(301, 311)]
    draft = ROOT / data['source_draft']
    assert hashlib.sha256(draft.read_bytes()).hexdigest() == data['source_draft_sha256']
    parts = re.findall(r'^## \d+\. (.+?)\n\n(.*?)\n\n\*\*按钮：\*\*「(.*?)」', draft.read_text(), re.M | re.S)
    source = json.loads((ROOT / 'planning/opening_backgrounds/chu_setting_source_snapshot.json').read_text())
    source_text = json.dumps(source, ensure_ascii=False)
    for row, (header, body, button) in zip(rows, parts):
        assert header == row['name'] + '｜' + row['title']
        assert (body, button) == (row['body'], row['button']), 'reviewed prose changed'
        history = MOD / 'history/countries' / row['history_file']
        tree = cw.read_tree(history)
        decoded = from_escaped_bytes(history.read_bytes())
        opening = cw.one(tree, '1444.11.11')
        assert cw.one(tree, 'primary_culture') == row['culture']
        assert cw.one(tree, 'religion') == 'confucianism'
        if row['tag'] not in ('CHC', 'TSF'):
            assert cw.one(tree, 'government_rank') == '1'
            assert cw.one(tree, 'add_government_reform') == 'zhx_feudatory_bo_reform'
        for field, kind in (('ruler', 'monarch'), ('heir', 'heir'), ('queen', 'queen')):
            if field not in row:
                assert not cw.values(opening, kind)
                continue
            character = row[field]
            block = cw.one(opening, kind)
            for stat in ('adm', 'dip', 'mil'):
                assert int(cw.one(block, stat)) == character[stat]
            assert f'name = "{character["name"]}"' in decoded
            assert f'dynasty = "{character["dynasty"]}"' in decoded
            if row['tag'] != 'TSF':
                assert character['dynasty'] + character['name'] in source_text
            if field in ('heir', 'queen'):
                assert cw.one(block, 'death_date') == '1821.1.1'
    for path, blob in render().items():
        assert path.read_bytes() == blob, f'stale setup: {path}'
    diplomacy = cw.read_tree(MOD / 'history/diplomacy/gdd_b52_chu_vassals.txt')
    pairs = [(cw.one(v, 'first'), cw.one(v, 'second')) for k, _, v in diplomacy if k == 'vassal']
    expected = {('CHC', tag) for tag in ('CSA','HNG','ZHU','QVN','ACG','EGU')}
    assert set(pairs) == expected and len(pairs) == 6
    # Heng must not acquire two simultaneous overlords in different history files.
    heng = []
    for path in (MOD / 'history/diplomacy').glob('*.txt'):
        for kind, _, block in cw.read_tree(path):
            if kind in ('vassal', 'march', 'union') and cw.values(block, 'second') == ['HNG']:
                heng.append((path.name, cw.one(block, 'first')))
    assert heng == [('gdd_b52_chu_vassals.txt', 'CHC')], heng
    hashes = json.loads((ROOT / 'planning/opening_backgrounds/chu_prior_outputs_sha256.json').read_text())
    for rel, digest in hashes.items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == digest, f'previous art/ruler changed: {rel}'
    assert cw.values(cw.read_tree(MOD / 'history/countries' / rows[3]['history_file']), 'capital') == ['5344']
    print('PASS: 10 approved stories/characters, eight bo states, six Chu vassals, Heng unique overlord, existing 13 images/five rulers unchanged; province geography retained.')


if __name__ == '__main__':
    main()

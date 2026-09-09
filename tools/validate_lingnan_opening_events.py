#!/usr/bin/env python3
"""Check assets/references and execute the narrow opening-queue script subset.

This is a source-level state-machine check, not proof of EU4 rendering or timing.
"""
from pathlib import Path
from copy import deepcopy
import json
import re
from PIL import Image
import validate_czc_government as cw
from encode_eu4_chinese_localisation import verify_file, from_escaped_bytes
from build_lingnan_opening_events import render, ROOT, MOD, load_manifest


def date(value):
    return tuple(map(int, value.split('.')))


TR = dict((k, v) for k, _, v in cw.read_tree(MOD / 'common/scripted_triggers/zhx_opening_background_triggers.txt'))
FX = dict((k, v) for k, _, v in cw.read_tree(MOD / 'common/scripted_effects/zhx_opening_background_effects.txt'))
FX.update((k, v) for k, _, v in cw.read_tree(MOD / 'common/scripted_effects/zhx_mod_guide_effects.txt'))
EVENTS = {}
for filename in ('zhx_opening_background_events.txt', 'zhx_system_events.txt', 'zhx_mod_guide_events.txt'):
    for k, _, v in cw.read_tree(MOD / 'events' / filename):
        if k == 'country_event':
            EVENTS[cw.one(v, 'id')] = v


def condition(tree, state):
    def test(k, v):
        if k == 'OR': return any(test(a, c) for a, _, c in v)
        if k == 'NOT': return not any(test(a, c) for a, _, c in v)
        if k == 'AND': return condition(v, state)
        if k in TR: return condition(TR[k], state) == (v == 'yes')
        if k == 'ai': return state['ai'] == (v == 'yes')
        if k == 'tag': return state['tag'] == v
        if k == 'has_country_flag': return v in state['flags']
        if k == 'has_global_flag': return v in state['globals']
        if k == 'is_date': return date(state['date']) >= date(v)
        if k == 'start_date': return date(state['start']) >= date(v)
        raise AssertionError('unsupported condition: ' + k)
    return all(test(k, v) for k, _, v in tree)


def apply(tree, state):
    matched = False
    for k, _, v in tree:
        if k == 'if':
            matched = condition(cw.one(v, 'limit'), state)
            if matched: apply([entry for entry in v if entry[0] != 'limit'], state)
        elif k == 'else_if':
            if not matched and condition(cw.one(v, 'limit'), state):
                matched = True
                apply([entry for entry in v if entry[0] != 'limit'], state)
        elif k == 'else':
            if not matched: apply(v, state)
        elif k in FX: apply(FX[k], state)
        elif k == 'hidden_effect': apply(v, state)
        elif k in ('name', 'custom_tooltip'): pass
        elif k == 'set_country_flag': state['flags'].add(v)
        elif k == 'clr_country_flag': state['flags'].discard(v)
        elif k == 'country_event':
            state['queue'].append((cw.one(v, 'id'), cw.values(v, 'days')))
        else: raise AssertionError('unexpected gameplay effect: ' + k)


def fresh(tag):
    return dict(tag=tag, ai=False, flags=set(), globals={'zhx_system_initialised_v4'},
                date='1444.11.11', start='1444.11.11', queue=[])


def main():
    rows = load_manifest()['countries']
    assert {r['tag'] for r in rows} == {'GDD','GUI','CZC','HAK','NUN','TZZ','LIL','DAI','CDE','JJG','HYA','WHU','ZHO','CHC','CSA','HNG','ZHU','QVN','ACG','EGU','NCH','LCH','TSF'}
    for path, data in render().items():
        assert path.read_bytes() == data, f'stale: {path}'
    verify_file(MOD / 'localisation_source/026_zhx_opening_backgrounds_readable_utf8.txt',
                MOD / 'localisation/replace/026_zhx_opening_backgrounds_l_english.yml')
    sprites = cw.one(cw.read_tree(MOD / 'interface/zhx_opening_background_eventpictures.gfx'), 'spriteTypes')
    sprite_map = {cw.one(v, 'name'): cw.one(v, 'texturefile') for _, _, v in sprites}
    assert len(sprite_map) == len(rows)
    hook = cw.one(cw.read_tree(MOD / 'common/on_actions/zhx_opening_background_on_actions.txt'), 'on_startup')
    registered = [k for k, _, v in cw.one(hook, 'events')]
    assert registered == [r['event_id'] for r in rows] + ['zhx_guide.0']
    assert len(hook) == 1, 'startup must use native event registration only'
    all_ids = []
    for file in (MOD / 'events').glob('*.txt'):
        all_ids.extend(re.findall(r'^\s*id\s*=\s*(zhx_opening\.\d+)\s*$', file.read_bytes().decode('latin-1'), re.M))
    assert sorted(all_ids) == sorted(r['event_id'] for r in rows)
    for filename in ('events/zhx_opening_background_events.txt', 'events/zhx_mod_guide_events.txt',
                     'common/scripted_effects/zhx_opening_background_effects.txt',
                     'common/scripted_effects/zhx_mod_guide_effects.txt'):
        tree = cw.read_tree(MOD / filename)
        assert not any(k in ('days', 'months', 'mean_time_to_happen') for k, _, v in cw.walk(tree)), 'reader introduced a date delay'

    def startup(state, order):
        visible = []
        for eid in order:
            event = EVENTS[eid]
            if condition(cw.one(event, 'trigger'), state):
                assert not cw.values(event, 'hidden'), 'startup should show the event itself'
                visible.append(eid)
                apply(cw.one(event, 'immediate'), state)
        return visible

    # The native hook owns the country scope; no world-init invocation required.
    cases = 0
    for row in rows:
        event = EVENTS[row['event_id']]
        if 'ruler' in row and row.get('history_group', 'GONGYI') == 'GONGYI':
            assert '蒙古' in row['body'], 'public-city foundation lost its invasion context'
            assert row['ruler']['dynasty'] + row['ruler']['name'] in row['body']
            history = cw.read_tree(MOD / 'history/countries' / row['history_file'])
            assert cw.one(history, 'government') == 'republic'
            assert cw.one(history, 'add_government_reform') == 'zhx_gongyi_reform'
            monarch = cw.one(cw.one(history, '1444.11.11'), 'monarch')
            for stat in ('adm', 'dip', 'mil'):
                assert int(cw.one(monarch, stat)) == row['ruler'][stat]
            assert bool(cw.values(monarch, 'female')) == row['ruler']['female']
            decoded = from_escaped_bytes((MOD / 'history/countries' / row['history_file']).read_bytes())
            assert f'name = "{row["ruler"]["name"]}"' in decoded
            assert f'dynasty = "{row["ruler"]["dynasty"]}"' in decoded
        with Image.open(MOD / sprite_map[cw.one(event, 'picture')]) as im:
            assert im.size == (512, 132) and im.format == 'DDS'
        for day in ('1444.11.11', '1444.11.12', '1444.11.13'):
            for order in (registered, list(reversed(registered))):
                state = fresh(row['tag']); state['date'] = day; state['globals'] = set()
                assert startup(state, order) == [row['event_id']], 'story/menu exclusion depends on order'
                assert not state['queue'], 'native startup must not queue a delayed story'
                state = deepcopy(state)
                assert not startup(state, order), 'reload repeated an open story'
                apply(FX['zhx_open_mod_guide'], state)
                assert not state['queue'], 'manual directory overtook unconfirmed story'
                apply(cw.one(event, 'option'), state)
                assert state['queue'] == [('zhx_guide.1', [])], 'story confirmation must open directory without a date tick'
                state['queue'].clear()
                apply(cw.one(EVENTS['zhx_guide.1'], 'immediate'), state)
                apply(cw.values(EVENTS['zhx_guide.1'], 'option')[-1], state)
                assert not startup(state, order), 'completed intro repeated'
                apply(FX['zhx_open_mod_guide'], state)
                assert state['queue'] == [('zhx_guide.1', [])], 'manual reopen must be immediate'
                cases += 1
        ai = fresh(row['tag']); ai['ai'] = True
        assert not startup(ai, registered) and not ai['flags'], 'AI received player-only introduction'
        for overrides in ({'date': '1444.11.14'}, {'start': '1453.1.1', 'date': '1453.1.1'},
                          {'start': '1399.10.14', 'date': '1444.11.11'}):
            other = fresh(row['tag']); other.update(overrides)
            assert startup(other, registered) == ['zhx_guide.0'], 'story appeared outside its campaign window'
    for tag in ('CZH', 'QIN', 'FRA'):
        state = fresh(tag); state['globals'] = set()
        assert startup(state, registered) == ['zhx_guide.0'], 'other countries lost their native opening directory'
        assert not state['queue']
        assert not startup(deepcopy(state), registered), 'directory repeated on reload'
    system = (MOD / 'common/scripted_effects/zhx_system_effects.txt').read_text()
    assert 'zhx_route_opening_introduction' not in system
    assert not re.search(r'id\s*=\s*zhx_system\.2\b', system)
    print(f'PASS: {len(rows)} native on_startup stories, {cases} date/order/scope cases, immediate story-to-guide/reopen, AI/reload exclusions, no reader timers, Gongyi rulers, DDS/IDs and Chinese encoding.')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Check authored tier branches and lifecycle hooks; not an EU4 engine emulator."""
from math import floor
from validate_czc_government import parse, require
from encode_eu4_chinese_localisation import MOD, FILES, verify_file

FX_PATH = MOD / 'common/scripted_effects/zhx_ritual_warscore_effects.txt'
FX = {k: v for k, _, v in parse(FX_PATH.read_text())}


def fields(tree):
    return {k: v for k, _, v in tree}


def condition(tree, state):
    for key, _, value in tree:
        if key == 'NOT': result = not condition(value, state)
        elif key in ('owner', 'event_target:zhx_tianzi'): result = condition(value, state)
        elif key == 'zhx_is_tianxia_polity': result = state['member']
        elif key in ('has_saved_global_event_target', 'exists', 'zhx_is_tianzi'): result = state['authority']
        elif key == 'check_variable': result = state['ritual'] >= float(fields(value)['value'])
        elif key == 'has_province_modifier': result = value in state['modifiers']
        elif key == 'has_province_flag': result = value in state['flags']
        else: raise AssertionError('Unmodelled condition: ' + key)
        if not result: return False
    return True


def execute(tree, state):
    matched = False
    for key, _, value in tree:
        if key in ('if', 'else_if', 'else'):
            if key == 'if': matched = False
            if not matched and (key == 'else' or condition(fields(value)['limit'], state)):
                execute([(k, op, v) for k, op, v in value if k != 'limit'], state)
                matched = True
        elif key in FX: execute(FX[key], state)
        elif key == 'remove_province_modifier': state['modifiers'].discard(value)
        elif key == 'add_province_modifier':
            require(fields(value)['duration'] == '-1', 'unexpected expiration')
            state['modifiers'].add(fields(value)['name'])
        elif key == 'clr_province_flag': state['flags'].discard(value)
        elif key == 'set_province_flag': state['flags'].add(value)
        else: raise AssertionError('Unmodelled effect: ' + key)


def main():
    modifiers = fields(parse((MOD / 'common/event_modifiers/zhx_ritual_warscore_modifiers.txt').read_text()))
    require(len(modifiers) == 20, 'expected twenty nonzero tiers')
    for p in range(5, 101, 5):
        definition = fields(modifiers[f'zhx_ritual_warscore_{p:03d}'])
        require(set(definition) == {'local_warscore_cost_modifier'}, 'defender protection must not add attacker-side costs or unrelated effects')
        require(float(definition['local_warscore_cost_modifier']) == p / 100, 'wrong modifier magnitude')
    state = dict(member=True, authority=True, ritual=50, modifiers={'unrelated_modifier'}, flags=set())
    # Ascending and descending sweeps exercise every boundary and replacement.
    values = [i / 2 for i in range(-202, 203)]
    for r in values + values[::-1]:
        state['ritual'] = r
        execute(FX['zhx_refresh_province_ritual_warscore'], state)
        p = max(0, min(100, floor((r + 100) / 10) * 5))
        expected = {'unrelated_modifier'} | ({f'zhx_ritual_warscore_{p:03d}'} if p else set())
        require(state['modifiers'] == expected, f'wrong tier/stack at {r}')
        execute(FX['zhx_refresh_province_ritual_warscore'], state)
        require(state['modifiers'] == expected, 'refresh is not idempotent')
    for cause in ('member', 'authority'):
        state.update(member=True, authority=True, ritual=50)
        execute(FX['zhx_refresh_province_ritual_warscore'], state)
        state[cause] = False
        execute(FX['zhx_refresh_province_ritual_warscore'], state)
        require(state['modifiers'] == {'unrelated_modifier'} and not state['flags'], 'exit/dead authority left protection')
    # Coverage is independent of the human viewer: no ai/ROOT filter in either wrapper.
    world = fields(fields(FX['zhx_refresh_all_ritual_warscore'])['every_country'])
    require(fields(world['limit']) == {'exists': 'yes'}, 'all live countries, including the player, must receive protection')
    require(world['zhx_refresh_country_ritual_warscore'] == 'yes', 'world refresh must visit owned provinces')
    owned = fields(fields(FX['zhx_refresh_country_ritual_warscore'])['every_owned_province'])
    require(owned['zhx_refresh_province_ritual_warscore'] == 'yes', 'country refresh must apply the province effect')
    scope_guard = fields(fields(owned['limit'])['OR'])
    require(scope_guard == {'owner': [('zhx_is_tianxia_polity', '=', 'yes')], 'has_province_flag': 'zhx_ritual_warscore_active'}, 'province coverage must depend on owner membership, not the viewer')
    system = fields(parse((MOD / 'common/scripted_effects/zhx_system_effects.txt').read_text()))
    for hook, effect in [('zhx_refresh_ritual_order', 'zhx_refresh_all_ritual_warscore'), ('zhx_set_tianzi', 'zhx_refresh_all_ritual_warscore'), ('zhx_register_tianxia_member', 'zhx_refresh_country_ritual_warscore'), ('zhx_remove_tianxia_member', 'zhx_refresh_country_ritual_warscore')]:
        require(effect in str(system[hook]), 'missing lifecycle hook: ' + hook)
    actions = fields(parse((MOD / 'common/on_actions/zhx_ritual_warscore_on_actions.txt').read_text()))
    require(fields(actions['on_province_owner_change']) == {'zhx_refresh_province_ritual_warscore': 'yes'}, 'owner callback must stay province-local')
    require('zhx_refresh_country_ritual_warscore' in fields(actions['on_monthly_pulse']), 'missing monthly repair')
    source = 'zhx_ritual_warscore_readable_utf8.txt'
    verify_file(MOD / 'localisation_source' / source, MOD / 'localisation' / FILES[source])
    loc = (MOD / 'localisation_source' / source).read_text()
    for name in modifiers:
        require(f' {name}:0 ' in loc and f' desc_{name}:0 ' in loc, 'missing localisation')
    print('PASS: 20 tiers; 810 ascending/descending half-point cases; idempotence, exit and dead-authority cleanup; lifecycle hooks; Chinese encoding. Static/model checks only; engine numerical/ownership testing pending.')


if __name__ == '__main__':
    main()

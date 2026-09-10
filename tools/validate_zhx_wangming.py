#!/usr/bin/env python3
"""Static contracts and source-driven boundary simulations; not an EU4 runtime test."""
from decimal import Decimal as D
from itertools import product
import re
import struct
from validate_czc_government import MOD, read_tree, one, values, walk, contains
from encode_eu4_chinese_localisation import verify_file


def check(condition, message):
    if not condition:
        raise AssertionError(message)


effects = read_tree(MOD / 'common/scripted_effects/zhx_wangming_effects.txt')
triggers = read_tree(MOD / 'common/scripted_triggers/zhx_wangming_triggers.txt')
for path in MOD.rglob('*zhx_wangming*'):
    if path.suffix in ('.txt', '.gfx') and 'localisation' not in str(path):
        read_tree(path)


def spare_eval(tree, provinces):
    results = []
    for key, _, body in tree:
        if key in ('AND', 'OR'):
            children = [spare_eval([entry], provinces) for entry in body]
            results.append(all(children) if key == 'AND' else any(children))
        elif key == 'num_of_owned_provinces_with':
            count = int(one(body, 'value'))
            category = next(k for k, _, _ in body if k.startswith('base_'))
            minimum = int(one(body, category))
            results.append(sum(p[category] >= minimum and p['is_city'] for p in provinces) >= count)
        else:
            raise AssertionError(key)
    return all(results)


# Exhaust all small province arrangements independently for each development type,
# keeping the other two plentiful; include unfinished colonies with spare capacity.
cases = 0
categories = ('base_tax', 'base_production', 'base_manpower')
for amount in range(1, 5):
    tree = one(triggers, f'zhx_wm_spare_{amount}')
    for category in categories:
        for n in range(1, 5):
            for bases in product(range(1, 6), repeat=n):
                provinces = [dict.fromkeys(categories, 8) | {category: b, 'is_city': True} for b in bases]
                provinces.append(dict.fromkeys(categories, 20) | {'is_city': False})
                expected = sum(b - 1 for b in bases) >= amount
                check(spare_eval(tree, provinces) == expected, f'spare {amount}: {category} {bases}')
                cases += 1


def simulate_transfer(name, effect_key, variable, due, stock, clamp):
    remaining, donor, received = D(due), D(stock), D(0)
    for loop in values(one(effects, name), 'while'):
        denomination = D(one(one(one(loop, 'limit'), 'check_variable'), 'value'))
        debit = D(one(loop, effect_key))
        credit = D(one(one(loop, 'event_target:zhx_wm_sender'), effect_key))
        decrement = one(loop, 'subtract_variable')
        check(one(decrement, 'which') == variable, 'wrong remainder variable')
        check(D(one(decrement, 'value')) == denomination == credit == -debit, 'unbalanced transfer')
        while remaining >= denomination:
            remaining -= denomination
            donor += debit
            if clamp:
                donor = max(D(0), donor)
            received += credit
    check(remaining == 0 and received == D(due), 'lost fractional transfer')
    check(donor == (max(D(0), D(stock)-D(due)) if clamp else D(stock)-D(due)), 'incorrect deduction')


for due in ('0', '2.4', '12.024', '999.999', '1000.001', '12345.678'):
    for stock in ('0', '0.001', '1', '2400', '99999'):
        simulate_transfer('zhx_wm_apply_levy', 'add_manpower', 'zhx_wm_levy_remaining', due, stock, True)
    simulate_transfer('zhx_wm_transfer_tribute', 'add_treasury', 'zhx_wm_money_remaining', due, '99999', False)

move = one(effects, 'zhx_wm_move_points')
distribute = [v for k, _, v in walk(move) if k == 'distribute_development']
check(len(distribute) == 3, 'three development categories required')
for body in distribute:
    check(one(body, 'limit') == 'is_in_capital_area = yes is_city = yes', 'capital-area destination')
    check(one(body, 'amount') == '$amount$', 'must transfer equal development')
for action in ('tribute', 'migration', 'levy'):
    flag = f'zhx_wm_{action}_used'
    check(contains(one(effects, 'zhx_wm_new_term'), 'clr_global_flag', flag), 'term refresh')
    check(contains(one(effects, f'zhx_wm_issue_{action}'), 'set_global_flag', flag), 'office usage')

gui = read_tree(MOD / 'interface/countrygovernmentview.gui')
bindings = read_tree(MOD / 'common/custom_gui/zhx_wangming_gui.txt')
# Regression: GUI scopes are always seeded with zero in the installed engine.
# Neither direct random execution nor a GUI-chained event supplies fresh entropy.
events = read_tree(MOD / 'events/zhx_wangming_events.txt')
dispatcher = next(v for k, _, v in events if k == 'country_event' and one(v, 'id') == 'zhx_wangming.1')
check(one(dispatcher, 'hidden') == 'yes', 'monthly dispatcher must be hidden')
pulse = read_tree(MOD / 'common/on_actions/zhx_wangming_on_actions.txt')
check(one(one(pulse, 'on_monthly_pulse'), 'events') == [('zhx_wangming.1', None, None)], 'must use native pulse event list')
check(not any(k == 'country_event' and contains(v, 'id', 'zhx_wangming.1') for k, _, v in walk(effects)), 'GUI-chained dispatcher inherits zero seed')
for action in ('tribute', 'migration', 'levy'):
    queued, used = f'zhx_wm_{action}_queued', f'zhx_wm_{action}_used'
    gate = 'zhx_wm_can_' + ('migrate' if action == 'migration' else action)
    queue_name, issue_name = f'zhx_wm_queue_{action}', f'zhx_wm_issue_{action}'
    binding = next(v for _, _, v in bindings if one(v, 'name') == f'zhx_wm_{action}_button')
    check(one(binding, 'effect') == [('hidden_effect', '=', [(queue_name, '=', 'yes')])], 'GUI may only enqueue')
    queue = one(effects, queue_name)
    check(queue == [('if', '=', [('limit', '=', [(gate, '=', 'yes')]), ('set_global_flag', '=', queued)])], 'queue must not draw RNG or schedule an event')
    check([('has_global_flag', '=', queued)] in values(one(triggers, gate), 'NOT'), 'pending action must block double clicks and yearly AI')
    branch = next(v for v in values(one(dispatcher, 'immediate'), 'if') if contains(one(v, 'limit'), 'has_global_flag', queued))
    check(branch[1:] == [('clr_global_flag', '=', queued), (issue_name, '=', 'yes')], 'unlock then recheck full eligibility and execute once')
    check(contains(one(effects, 'zhx_wm_new_term'), 'clr_global_flag', queued), 'expired requests must not consume next term')
    # State scenarios derive routing from the actual queue/dispatch blocks.
    for eligible_at_dispatch in (False, True):
        flags = set()
        def eligible():
            return not {queued, used} & flags
        for _ in range(2):
            if eligible():
                flags.add(one(one(queue, 'if'), 'set_global_flag'))
        check(flags == {queued}, 'duplicate enqueue')
        for _ in range(2):
            if one(one(branch, 'limit'), 'has_global_flag') in flags:
                flags.discard(one(branch, 'clr_global_flag'))
                if eligible_at_dispatch and eligible():
                    flags.add(used)
        check(flags == ({used} if eligible_at_dispatch else set()), 'dispatch/recheck/repeat boundary')
controls = {one(v, 'name'): v for _, _, v in walk(gui) if isinstance(v, list) and values(v, 'name') and one(v, 'name').startswith('zhx_wm_')}
check(set(controls) == {one(v, 'name') for _, _, v in bindings}, 'GUI binding mismatch')
for body in controls.values():
    check(one(body, 'scripted') == 'yes', 'unscripted control')
for name in ('tribute', 'migration', 'levy', 'banner'):
    data = (MOD / f'gfx/interface/zhx_wangming/{name}.dds').read_bytes()
    height, width = struct.unpack_from('<II', data, 12)
    check(data[:4] == b'DDS ' and (width, height) == ((344, 93) if name == 'banner' else (144, 72)), 'DDS dimensions')
source = MOD / 'localisation_source/031_zhx_wangming_readable_utf8.txt'
verify_file(source, MOD / 'localisation/replace/031_zhx_wangming_l_english.yml')
text = source.read_text(encoding='utf-8-sig')
check(not re.search('[−－﹣]|[‒–](?=\\d)', text), 'unsupported numeric minus')
keys = set(re.findall(r'^ (\w+):', text, re.M))
for key, _, value in walk(bindings):
    if key in ('tooltip', 'name'):
        check(value in keys or value.endswith(('_button', '_banner')), f'missing localization {value}')
print(f'PASS: {cases} development-capacity cases, transfer boundaries, native pulse queue/recheck/expiry, term flags, GUI, DDS, localisation. Runtime remains untested.')

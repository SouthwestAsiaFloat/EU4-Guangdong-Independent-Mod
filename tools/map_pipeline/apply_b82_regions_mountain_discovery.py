#!/usr/bin/env python3
"""Southern Jianghuai/Huaiyang regions and East Asian mountain discovery.

Discovery-only wasteland histories follow vanilla Himalaya's technology-group
convention. A hidden startup/monthly migration adds the same known provinces
to existing Chinese/nomad campaigns without changing mountain ownership.
"""
import argparse
import re
from pathlib import Path

from apply_b78_daming_refinement import block_bounds

ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / 'guangdong_independent_practice'
MOUNTAINS = {
    5175: 'Daba Mountains', 5176: 'Min Mountains', 5183: 'Qinling Mountains',
    5187: 'Long Mountains', 5257: 'Heng-Wutai Mountains',
    5258: 'North Taihang Mountains', 5259: 'South Taihang Mountains',
    5260: 'Luliang Mountains', 5261: 'Zhongtiao Mountains', 5304: 'Wuzhishan',
    5310: 'Nanling West', 5311: 'Nanling East', 5354: 'Dabie Mountains',
    5355: 'Mount Tai', 5375: 'Rangrim Mountains', 5376: 'Taebaek Mountains',
    5377: 'Jiulian Mountains', 5378: 'Zhe-Min Mountains',
    5379: 'Wuyi Mountains', 5380: 'Huangshan',
}
AREAS = ('jianghuai_area', 'huaiyang_tongtai_area')
EVENT = MOD / 'events/gdd_mountain_discovery_events.txt'
HOOK = MOD / 'common/on_actions/gdd_mountain_discovery_on_actions.txt'

def province_path(pid):
    return MOD / f'history/provinces/{pid} - {MOUNTAINS[pid]}.txt'

def history_text(pid):
    return (f'# {pid} - {MOUNTAINS[pid]} - GDD_B82_MOUNTAIN_DISCOVERY\n'
            '# Discovery only: unowned and impassable.\n'
            'discovered_by = chinese\ndiscovered_by = nomad_group\n')

def event_text():
    effects = ''.join(f'        discover_province = {pid}\n' for pid in MOUNTAINS)
    return '''namespace = gdd_mountain_discovery

# Startup covers new campaigns/reloads; the monthly hook catches old saves
# and newly released countries. Each eligible country is migrated once.
country_event = {
    id = gdd_mountain_discovery.1
    hidden = yes
    is_triggered_only = yes
    trigger = {
        OR = {
            technology_group = chinese
            technology_group = nomad_group
        }
        NOT = { has_country_flag = gdd_b82_mountains_discovered }
    }
    immediate = {
''' + effects + '''        set_country_flag = gdd_b82_mountains_discovered
    }
}
'''

def hook_text():
    return '''# GDD_B82_MOUNTAIN_DISCOVERY
on_startup = { events = { gdd_mountain_discovery.1 } }
on_monthly_pulse = { events = { gdd_mountain_discovery.1 } }
'''

def apply():
    path = MOD / 'map/region.txt'
    text = path.read_text(encoding='cp1252')
    for area in AREAS:
        text = re.sub(rf'(?m)^[ \t]*{area}[ \t]*(?:#[^\n]*)?\n', '', text)
    start, end = block_bounds(text, 'south_china_region')
    region = text[start:end]
    a, b = block_bounds(region, 'areas')
    areas = region[a:b]
    areas = areas[:-1].rstrip() + '\n' + ''.join(f'        {name} # GDD_B82_SOUTH_CHINA\n' for name in AREAS) + '    }'
    region = region[:a] + areas + region[b:]
    path.write_text(text[:start] + region + text[end:], encoding='cp1252')
    for pid in MOUNTAINS:
        path = province_path(pid)
        if path.exists() and path.read_text() != history_text(pid):
            raise ValueError(f'Refusing to overwrite an unexpected mountain history: {path}')
        path.write_text(history_text(pid), encoding='utf-8')
    EVENT.write_text(event_text(), encoding='utf-8')
    HOOK.write_text(hook_text(), encoding='utf-8')

def check():
    region = (MOD / 'map/region.txt').read_text(encoding='cp1252')
    start, end = block_bounds(region, 'south_china_region')
    for area in AREAS:
        assert len(re.findall(rf'\b{area}\b', region)) == 1
        assert re.search(rf'\b{area}\b', region[start:end])
    climate = (MOD / 'map/climate.txt').read_text(encoding='cp1252')
    start, end = block_bounds(climate, 'impassable')
    impassable = set(map(int, re.findall(r'\b\d+\b', re.sub(r'#[^\n]*', '', climate[start:end]))))
    assert set(MOUNTAINS) == {pid for pid in impassable if pid >= 5000 and pid != 5029}
    for pid in MOUNTAINS:
        matches = [p for p in (MOD / 'history/provinces').glob('*.txt') if re.match(rf'^{pid}\D', p.name)]
        assert matches == [province_path(pid)], (pid, matches)
        assert province_path(pid).read_text() == history_text(pid)
    assert EVENT.read_text() == event_text()
    assert HOOK.read_text() == hook_text()
    assert set(map(int, re.findall(r'discover_province = (\d+)', EVENT.read_text()))) == set(MOUNTAINS)
    print('B82 PASS: Jianghuai/Huaiyang in South China; 20 unowned mountain histories; startup/monthly discovery migration')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if not args.check:
        apply()
    check()

#!/usr/bin/env python3
"""Merge Yiling/Guizhou into the northern Yanyong area; no province edits."""
import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from encode_eu4_chinese_localisation import encode_file, verify_file
from apply_b78_daming_refinement import block_bounds, replace_block

MOD = ROOT / 'guangdong_independent_practice'
MEMBERS = (5008, 5341, 2171, 5342, 681, 5346)
SOURCE = MOD / 'localisation_source/gdd_zzz_chunqiu_area_overrides_readable_utf8.txt'
TARGET = MOD / 'localisation/replace/zzz_gdd_chunqiu_area_overrides_l_english.yml'

def apply():
    verify_file(SOURCE, TARGET)
    path = MOD / 'map/area.txt'
    text = path.read_text(encoding='cp1252')
    text = replace_block(text, 'hanshang_area', 'hanshang_area = { # GDD_B80_YILING_HANSHANG_MERGE\n    ' + ' '.join(map(str, MEMBERS)) + '\n}')
    if re.search(r'(?m)^yigui_area\s*=', text):
        start, end = block_bounds(text, 'yigui_area')
        text = text[:start] + text[end:]
    path.write_text(text, encoding='cp1252')
    path = MOD / 'map/region.txt'
    text = re.sub(r'(?m)^[ \t]*yigui_area[ \t]*\n', '', path.read_text(encoding='cp1252'))
    path.write_text(text, encoding='cp1252')
    text = re.sub(r'(?m)^[ \t]*yigui_area(?:_name|_adj)?:\d+[^\n]*\n', '', SOURCE.read_text(encoding='utf-8-sig'))
    SOURCE.write_text('\ufeff' + text, encoding='utf-8')
    encode_file(SOURCE, TARGET)

def check():
    text = (MOD / 'map/area.txt').read_text(encoding='cp1252')
    start, end = block_bounds(text, 'hanshang_area')
    actual = tuple(map(int, re.findall(r'\b\d+\b', re.sub(r'#[^\n]*', '', text[start:end]))))
    assert actual == MEMBERS
    assert not re.search(r'\byigui_area\b', text)
    assert not re.search(r'\byigui_area\b', (MOD / 'map/region.txt').read_text(encoding='cp1252'))
    verify_file(SOURCE, TARGET)
    print('B80 PASS: hanshang_area = 5008 5341 2171 5342 681 5346; name=鄢庸')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if not args.check:
        apply()
    check()

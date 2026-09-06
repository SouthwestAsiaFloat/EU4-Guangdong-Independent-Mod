#!/usr/bin/env python3
"""Four strategic Yangtze crossings and a same-bank Chizhou-Wuwei land link."""
import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
import shutil

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from apply_b47_jingxiang_yunan_refinement import components, definition_rows
from apply_b78_daming_refinement import block_bounds

ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / 'guangdong_independent_practice'
MAP = MOD / 'map'
PLAN = ROOT / 'planning/yangtze_four_crossings_b81'
PIXELS = tuple((x, y) for y in (886, 887, 888) for x in (4635, 4636))
CROSSINGS = (
    '2172;5014;sea;5036;-1;-1;-1;-1;Jingzhou-Gongan Yangtze crossing',
    '4981;682;sea;5035;-1;-1;-1;-1;Hanyang-Wuchang crossing',
    '4979;686;sea;5038;-1;-1;-1;-1;Jiujiang-Anqing crossing',
    '5056;1821;sea;5033;-1;-1;-1;-1;Liuhe-Jiangning crossing',
)
WATER = set(range(5032, 5039))

def yangtze(line):
    row = line.split(';')
    return len(row) > 3 and row[3].isdigit() and int(row[3]) in WATER

def touches(a, b):
    return bool(np.any(a[:-1] & b[1:]) or np.any(a[1:] & b[:-1]) or np.any(a[:, :-1] & b[:, 1:]) or np.any(a[:, 1:] & b[:, :-1]))

def apply():
    PLAN.mkdir(parents=True, exist_ok=True)
    for name in ('provinces.bmp', 'adjacencies.csv', 'positions.txt'):
        backup = PLAN / ('pre_b81_' + name)
        if not backup.exists():
            shutil.copy2(MAP / name, backup)
    colors = {pid: row[0] for pid, row in definition_rows().items()}
    if not (PLAN / 'batch_manifest.json').exists():
        manifest = {'batch': 'B81', 'purpose': '用户批准四渡；池州无为改为同岸直接接壤',
                    'editable_pixels': PIXELS, 'from_id': 5354, 'from_rgb': colors[5354],
                    'to_id': 5065, 'to_rgb': colors[5065], 'unchanged_neighbor': 5062,
                    'locked': 'all pixels outside the six-cell patch, including every Yangtze water pixel',
                    'crossings': CROSSINGS, 'history_policy': 'unchanged',
                    'backup_bitmap_sha256': hashlib.sha256((PLAN / 'pre_b81_provinces.bmp').read_bytes()).hexdigest()}
        (PLAN / 'batch_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    image = np.array(Image.open(MAP / 'provinces.bmp').convert('RGB'))
    before = image.copy()
    for x, y in PIXELS:
        assert tuple(image[y, x]) in (colors[5354], colors[5065]), (x, y, image[y, x])
        image[y, x] = colors[5065]
    changed = np.any(image != before, axis=2)
    for x, y in PIXELS:
        changed[y, x] = False
    assert not changed.any()
    Image.fromarray(image).save(MAP / 'provinces.bmp', format='BMP')
    path = MAP / 'adjacencies.csv'
    lines = [line for line in path.read_text(encoding='cp1252').splitlines() if not yangtze(line)]
    end = next(i for i, line in enumerate(lines) if line.startswith('-1;-1;'))
    lines[end:end] = CROSSINGS
    path.write_text('\n'.join(lines) + '\n', encoding='cp1252')
    path = MAP / 'positions.txt'
    text = path.read_text(encoding='cp1252')
    start, end = block_bounds(text, '5065')
    block = text[start:end]
    # Existing 4629/1157 anchors were inside Dabie before this batch.
    points = ' '.join(['4634.000 1157.000'] * 6 + ['0.000 0.000'])
    block = re.sub(r'(position\s*=\s*\{)[^}]*', lambda m: m[1] + '\n        ' + points + '\n    ', block, count=1)
    path.write_text(text[:start] + block + text[end:], encoding='cp1252')
    check()
    render()

def check():
    colors = {pid: row[0] for pid, row in definition_rows().items()}
    image = np.array(Image.open(MAP / 'provinces.bmp').convert('RGB'))
    base = np.array(Image.open(PLAN / 'pre_b81_provinces.bmp').convert('RGB'))
    mask = lambda pid: np.all(image == colors[pid], axis=2)
    assert all(tuple(image[y, x]) == colors[5065] for x, y in PIXELS)
    assert touches(mask(5065), mask(5062)), 'Chizhou/Wuwei must share a four-way land edge'
    assert tuple(image[891, 4634]) == colors[5065]
    positions = (MAP / 'positions.txt').read_text(encoding='cp1252')
    start, end = block_bounds(positions, '5065')
    assert positions[start:end].count('4634.000 1157.000') == 6
    province_components = {}
    for pid in (5065, 5062, 5354):
        province_components[pid] = components(mask(pid))
        expected = components(np.all(base == colors[pid], axis=2)) if pid == 5354 else 1
        assert province_components[pid] == expected, (pid, province_components[pid], expected)
    for pid in WATER:
        assert np.array_equal(mask(pid), np.all(base == colors[pid], axis=2)), 'River pixels changed'
    current = (MAP / 'adjacencies.csv').read_text(encoding='cp1252').splitlines()
    assert [line for line in current if yangtze(line)] == list(CROSSINGS)
    old = (PLAN / 'pre_b81_adjacencies.csv').read_text(encoding='cp1252').splitlines()
    assert [line for line in current if not yangtze(line)] == [line for line in old if not yangtze(line)]
    for line in CROSSINGS:
        a, b, _, through, *_ = line.split(';')
        assert touches(mask(int(a)), mask(int(through))) and touches(mask(int(b)), mask(int(through)))
    print(json.dumps({'B81': 'PASS', 'crossings': 4, 'land_link': [5065, 5062], 'province_components': province_components, 'river_pixels_changed': 0}))

def render():
    colors = {pid: row[0] for pid, row in definition_rows().items()}
    box = (4618, 872, 4654, 906)
    scale = 13
    font = lambda size: ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc', size)
    out = Image.new('RGB', (1000, 540), (248, 245, 234))
    draw = ImageDraw.Draw(out)
    for index, filename in enumerate((PLAN / 'pre_b81_provinces.bmp', MAP / 'provinces.bmp')):
        data = np.array(Image.open(filename).convert('RGB').crop(box))
        rgb = np.full(data.shape, (206, 202, 188), dtype=np.uint8)
        for pid, color in ((5065, (96, 153, 124)), (5062, (216, 180, 111)), (5354, (105, 98, 83)), (5034, (98, 163, 193)), (5038, (98, 163, 193))):
            rgb[np.all(data == colors[pid], axis=2)] = color
        tile = Image.fromarray(rgb).resize((rgb.shape[1] * scale, rgb.shape[0] * scale), Image.Resampling.NEAREST)
        offset = 18 + index * 495
        out.paste(tile, (offset, 48))
        draw.text((offset, 10), '修改前' if index == 0 else '修改后：池州—无为陆路接壤', font=font(23), fill=(40, 48, 39))
        for pid, name in ((5065, '池州'), (5062, '无为'), (5354, '大别山'), (5034, '长江')):
            yy, xx = np.where(np.all(data == colors[pid], axis=2))
            x, y = float(np.median(xx)), float(np.median(yy))
            draw.text((offset + x * scale - 18, 48 + y * scale), name, font=font(20), fill='white', stroke_width=2, stroke_fill=(50, 55, 47))
        x0, y0 = PIXELS[0]
        draw.rectangle((offset + (x0 - box[0]) * scale - 2, 48 + (y0 - box[1]) * scale - 2, offset + (x0 - box[0] + 2) * scale + 2, 48 + (y0 - box[1] + 3) * scale + 2), outline=(232, 66, 38), width=3)
    draw.text((20, 506), '修整大别山末端 6 像素 · 长江水道完全保留 · 原池州—无为特殊渡口删除', font=font(21), fill=(48, 60, 48))
    out.save(PLAN / 'b81_land_link_preview.png')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    check() if args.check else apply()

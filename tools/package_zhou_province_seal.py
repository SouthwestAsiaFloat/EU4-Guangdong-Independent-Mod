#!/usr/bin/env python3
"""Package approved ImageGen artwork into EU4 strips; no glyph drawing.

Atlas rows: registered, add, remove. Columns: normal, pressed, hover.
EU4 strip order: normal, hover, pressed, disabled. Disabled uses the dark
frame. Keep the existing 54x42 hit area and render the square seal at 42x42.
"""
from pathlib import Path
import argparse
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'tools/assets/zhou_province_seal_v1/states.png'
TARGET = ROOT / 'guangdong_independent_practice/gfx/interface'


def build(check=False):
    with Image.open(SOURCE) as source:
        atlas = source.convert('RGBA')
    for row, name in enumerate(('status', 'add', 'remove')):
        strip = Image.new('RGBA', (216, 42), (16, 39, 43, 255))
        for state, col in enumerate((0, 2, 1, 1)):
            box = (round(col * atlas.width / 3), round(row * atlas.height / 3),
                   round((col + 1) * atlas.width / 3), round((row + 1) * atlas.height / 3))
            icon = atlas.crop(box).resize((42, 42), Image.Resampling.LANCZOS)
            strip.paste(icon, (state * 54, 0))
        path = TARGET / f'gdd_tianxia_province_{name}.tga'
        if check:
            with Image.open(path) as actual:
                assert actual.size == strip.size and actual.convert('RGBA').tobytes() == strip.tobytes(), path
        else:
            strip.save(path, format='TGA')
        print(('checked ' if check else 'wrote ') + str(path.relative_to(ROOT)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    build(parser.parse_args().check)

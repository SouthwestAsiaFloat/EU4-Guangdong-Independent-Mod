#!/usr/bin/env python3
"""Reproduce size/format exports of imagegen art; no semantic image edits."""
from pathlib import Path
import hashlib
import json
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = HERE / 'sources/mianliu.png'
TEXTURE = ROOT / 'guangdong_independent_practice/gfx/interface/zhx_tianzi/mianliu_57.dds'
PREVIEW = ROOT / 'planning/tianzi_government/icon_preview.png'


def main():
    original = Image.open(SOURCE).convert('RGBA')
    icon = original.resize((57, 57), Image.Resampling.LANCZOS)
    TEXTURE.parent.mkdir(parents=True, exist_ok=True)
    icon.save(TEXTURE)
    decoded = Image.open(TEXTURE).convert('RGBA')
    assert decoded.size == (57, 57) and decoded.tobytes() == icon.tobytes()
    board = Image.new('RGB', (430, 480), '#171f21')
    draw = ImageDraw.Draw(board)
    board.paste(original.resize((360, 360), Image.Resampling.LANCZOS), (35, 20))
    board.paste(decoded, (35, 402))
    draw.text((109, 412), '57 x 57 production texture', fill='#e7d7b1')
    draw.text((109, 433), 'Asset preview - not an in-game screenshot', fill='#a5b4b4')
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    board.save(PREVIEW)
    manifest = {
        'generator': 'built-in imagegen',
        'conversion': 'LANCZOS resize; uncompressed RGBA DDS',
        'assets': {'mianliu': {
            'source': str(SOURCE.relative_to(ROOT)),
            'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            'source_size': list(original.size),
            'texture': str(TEXTURE.relative_to(ROOT)),
            'texture_sha256': hashlib.sha256(TEXTURE.read_bytes()).hexdigest(),
            'texture_size': [57, 57], 'frames': 1,
        }},
    }
    (HERE / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('PASS: 57x57 DDS decodes pixel-exactly; manifest and preview exported')


if __name__ == '__main__':
    main()

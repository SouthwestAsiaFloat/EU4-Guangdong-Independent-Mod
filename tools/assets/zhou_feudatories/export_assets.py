#!/usr/bin/env python3
"""Size/format export of original imagegen art; no semantic image edits."""
from pathlib import Path
import hashlib
import json
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DEST = ROOT / 'guangdong_independent_practice/gfx/interface/zhx_feudatories'
PREVIEW = ROOT / 'planning/zhou_feudatories/government_icons_preview.png'
ASSETS = [('investiture', '伯国 · 玉圭册命'), ('ritual_ding', '侯／公 · 礼鼎印玺')]

def main():
    DEST.mkdir(parents=True, exist_ok=True)
    board = Image.new('RGB', (820, 530), '#171f21')
    draw = ImageDraw.Draw(board)
    font_path = str(next(p for p in [Path('/System/Library/Fonts/PingFang.ttc'), Path('/System/Library/Fonts/STHeiti Medium.ttc'), Path('/System/Library/Fonts/Supplemental/Arial Unicode.ttf')] if p.exists()))
    font = lambda n: ImageFont.truetype(font_path, n)
    draw.text((28, 20), '周制封国 · 政府改革图标', font=font(25), fill='#e7d7b1')
    draw.text((28, 59), '素材与 57 px 实际尺寸预览 · 非游戏截图', font=font(16), fill='#a5b4b4')
    manifest = {'generator': 'built-in imagegen', 'conversion': 'LANCZOS resize; uncompressed RGBA DDS', 'assets': {}}
    for i, (name, label) in enumerate(ASSETS):
        source = HERE / 'sources' / (name + '.png')
        original = Image.open(source).convert('RGBA')
        icon = original.resize((57, 57), Image.Resampling.LANCZOS)
        dest = DEST / (name + '_57.dds')
        icon.save(dest)
        decoded = Image.open(dest).convert('RGBA')
        assert decoded.size == (57, 57) and decoded.tobytes() == icon.tobytes()
        x = 28 + 400 * i
        board.paste(original.resize((300, 300), Image.Resampling.LANCZOS), (x, 102))
        draw.text((x, 414), label, font=font(21), fill='#e7d7b1')
        board.paste(decoded, (x + 238, 439))
        draw.text((x, 463), '游戏纹理 57 × 57 →', font=font(16), fill='#a5b4b4')
        manifest['assets'][name] = {
            'source': str(source.relative_to(ROOT)),
            'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'source_size': list(original.size),
            'texture': str(dest.relative_to(ROOT)),
            'texture_sha256': hashlib.sha256(dest.read_bytes()).hexdigest(),
            'texture_size': [57, 57], 'frames': 1,
        }
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    board.save(PREVIEW)
    (HERE / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('PASS: two 57x57 DDS textures decode pixel-exactly; manifest and preview exported')

if __name__ == '__main__':
    main()

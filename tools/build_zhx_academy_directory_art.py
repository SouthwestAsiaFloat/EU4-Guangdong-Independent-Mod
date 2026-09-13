#!/usr/bin/env python3
"""Native UI geometry over a province-panel teal texture; no baked text.

Run with the bundled Pillow Python. Preview uses production layout and textures
with sample world state and an approximate system CJK font, not game rendering.
"""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "guangdong_independent_practice/gfx/interface/zhx_academy_directory"
SPRITES = {
    "background": (690, 580, "spriteType"),
    "detail": (642, 199, "spriteType"),
    "row": (626, 35, "spriteType"),
    "selected": (626, 35, "spriteType"),
    "status": (94, 25, "spriteType"),
    "seal": (54, 28, "spriteType"),
    "track": (4, 166, "spriteType"),
    "thumb": (8, 24, "spriteType"),
    "small_button": (68, 28, "textSpriteType"),
    "action_button": (148, 32, "textSpriteType"),
    "close": (26, 26, "spriteType"),
    "up": (26, 24, "spriteType"),
    "down": (26, 24, "spriteType"),
}
FONTS = {
    "body": (16, "e5dfcc"),
    "muted": (16, "bcbda9"),
    "name": (18, "ead7a4"),
    "title": (24, "eed49b"),
    "red": (16, "d1b274"),
}


def artwork():
    from PIL import Image, ImageDraw
    texture = Image.open(ROOT / "tools/assets/academy_directory/teal_texture_v1.png").convert("RGBA")
    out = {}
    for name, (w, h, _) in SPRITES.items():
        im = Image.new("RGBA", (w, h))
        d = ImageDraw.Draw(im)
        if name == "background":
            im = texture.resize((w, h), Image.Resampling.LANCZOS)
            d = ImageDraw.Draw(im)
            d.rectangle((0, 0, w-1, h-1), outline="#121e20", width=3)
            d.rectangle((4, 4, w-5, h-5), outline="#a17e42", width=2)
            d.rectangle((8, 8, w-9, h-9), outline="#534a31")
            d.line((24, 76, 665, 76), fill="#77623e")
            d.line((30, 76, 125, 76), fill="#c39c59", width=2)
            d.line((24, 108, 645, 108), fill="#857044")
            for x in (14, w-15):
                for y in (14, h-15):
                    dx, dy = (1 if x < w/2 else -1), (1 if y < h/2 else -1)
                    d.line((x, y+dy*12, x, y, x+dx*12, y), fill="#c4a261")
                    d.line((x+dx*4, y+dy*9, x+dx*4, y+dy*4, x+dx*9, y+dy*4), fill="#887042")
        elif name == "detail":
            d.rectangle((0, 0, w-1, h-1), fill="#10262c", outline="#8e7448")
            d.rectangle((3, 3, w-4, h-4), outline="#344b48")
            d.line((0, 0, w-1, 0), fill="#b38d4d", width=2)
            d.line((14, 148, w-15, 148), fill="#5c5942")
        elif name == "row":
            d.line((10, h-1, w-8, h-1), fill="#3b4f4e")
        elif name == "selected":
            d.rectangle((0, 0, w-1, h-2), fill="#2c4949", outline="#8e7c50")
            d.rectangle((0, 0, 2, h-2), fill="#caa764")
        elif name in ("status", "seal"):
            tone = "#686d51" if name == "status" else "#aa8a4b"
            d.rectangle((1, 1, w-2, h-2), outline=tone)
            if name == "seal":
                d.rectangle((3, 3, w-4, h-4), outline=tone)
        elif name in ("small_button", "action_button"):
            d.rectangle((1, 1, w-2, h-2), fill="#263b3c", outline="#aa8a4c")
            d.line((3, 3, w-4, 3), fill="#69705b")
            d.line((3, h-3, w-4, h-3), fill="#111e23")
        elif name == "track":
            d.rectangle((1, 0, 2, h-1), fill="#526261")
        elif name == "thumb":
            d.rectangle((1, 0, 6, h-1), fill="#ab8b53", outline="#d0b578")
        elif name == "close":
            d.line((8, 8, 18, 18), fill="#c4a772", width=2)
            d.line((18, 8, 8, 18), fill="#c4a772", width=2)
        else:
            points = [(7, 15), (13, 8), (19, 15)] if name == "up" else [(7, 8), (13, 15), (19, 8)]
            d.line(points, fill="#bda16a", width=2)
        out[name] = im
    return out


def main():
    from PIL import Image
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    for name, im in artwork().items():
        path = DEST / f"{name}.dds"
        if args.check:
            assert path.exists(), path
            saved = Image.open(path).convert("RGBA")
            assert saved.size == im.size and saved.tobytes() == im.tobytes(), path
        else:
            DEST.mkdir(parents=True, exist_ok=True)
            im.save(path)
    print(f"academy folio textures: {len(SPRITES)} {'checked' if args.check else 'built'}")
    if args.preview:
        preview()


def preview():
    """Render the shipped GUI coordinates, with explicitly illustrative data."""
    import json
    import re
    from PIL import Image, ImageDraw, ImageFont
    from build_zhx_academy_directory import render, MANIFEST, MOD
    from test_zhx_academy_directory import DirectoryWorld
    from test_gdd_tianxia_territory import parse

    generated = render()
    academies = json.loads(MANIFEST.read_text())["academies"]
    loc = dict(re.findall(r'^ (\w+):0 "(.*)"$', generated["localisation_source/zhx_academy_directory_readable_utf8.txt"], re.M))
    gui = parse("file = {\n" + generated["directory_gui_fragment"] + "\n}")["file"]
    panel = next(v for k, v in gui if k == "windowType")
    definitions = parse("file = {\n" + generated["common/custom_gui/zhx_academy_directory.txt"] + "\n}")["file"]
    bindings = {dict(v)["name"]: dict(v) for _, v in definitions}
    assets = artwork()
    out = ROOT / "planning/religion_academies/directory_visuals"
    out.mkdir(parents=True, exist_ok=True)
    fonts = {"zhx_ad_" + n: ImageFont.truetype("/System/Library/Fonts/Supplemental/Songti.ttc", size)
             for n, (size, _) in FONTS.items()}
    colors = {"zhx_ad_" + n: "#" + color for n, (_, color) in FONTS.items()}
    for selected, offset in [("chongli", 0), ("xunming", 1)]:
        w = DirectoryWorld()
        w.root.flags.pop("zhx_doctrine_fa", None)
        w.root.flags["zhx_doctrine_ru"] = 0
        values = {}
        for i, e in enumerate(academies):
            province = w.province("CZH")
            province.modifiers.add(e["modifier"])
            cap, key = e["key"].capitalize(), e["key"]
            values.update({
                f"Root.GetZhxAd{cap}Location": e["province_name"],
                f"Root.GetZhxAd{cap}Owner": "周天子",
                f"Root.GetZhxAd{cap}Status": loc["zhx_ad_active"],
                f"Root.GetZhxAd{cap}Benefit": loc[f"zhx_ad_benefit_{key}"],
                f"Root.GetZhxAd{cap}Relation": loc["zhx_ad_synergy" if e["school"] == "ru" else "zhx_ad_tension"],
                f"Root.zhx_ad_ruins_{key}.GetValue": "0",
            })
            if key == selected:
                selected_index = i + 1
        w.effect("zhx_ad_open")
        w.root.variables.update(zhx_ad_selected=selected_index, zhx_ad_offset=offset)
        canvas = Image.new("RGBA", (690, 580))
        d = ImageDraw.Draw(canvas)

        def draw_text(value, xy, font_name, width, height, disabled=False, centered=False):
            value = re.sub(r'\[([^\]]+)\]', lambda m: values.get(m[1], m[0]), value).replace("\\n", "\n")
            font = fonts[font_name]
            x, y = xy
            if centered:
                clean = re.sub(r'§.', '', value)
                x += (width-d.textlength(clean, font=font))/2
                y += (height-font.size)/2-2
            start_x, start_y = x, y
            base = "#777e76" if disabled else colors[font_name]
            color = base
            i = 0
            while i < len(value):
                c = value[i]
                if c == "§" and i + 1 < len(value):
                    color = {"G": "#7bb986", "R": "#e08069", "Y": "#dcc078"}.get(value[i+1], base)
                    i += 2
                    continue
                step = d.textlength(c, font=font)
                if c == "\n" or x+step > start_x+width:
                    x, y = start_x, y + font.size + 3
                    if c == "\n":
                        i += 1
                        continue
                if y + font.size > start_y + height:
                    raise ValueError(f"preview text overflow: {value}")
                d.text((x, y), c, font=font, fill=color)
                x += step
                i += 1

        for kind, data in panel:
            if kind not in ("guiButtonType", "instantTextBoxType", "iconType"):
                continue
            obj = dict(data)
            name = obj["name"]
            bound = bindings[name]
            if not w.evaluate(bound["potential"], [w.root]):
                continue
            pos = dict(obj["position"])
            x, y = int(pos["x"]), int(pos["y"])
            if kind == "instantTextBoxType":
                draw_text(loc[name], (x, y), obj["font"], int(obj["maxWidth"]), int(obj["maxHeight"]))
                continue
            sprite = obj.get("spriteType", obj.get("quadTextureSprite"))
            if sprite.startswith("GFX_zhx_ad_"):
                im = assets[sprite.removeprefix("GFX_zhx_ad_")]
            else:
                school = sprite.removeprefix("GFX_zhx_doctrine_").removesuffix("_school")
                im = Image.open(MOD / f"gfx/interface/zhx_doctrine_{school}_school.tga").convert("RGBA")
                scale = float(obj.get("scale", 1))
                im = im.resize((round(im.width*scale), round(im.height*scale)), Image.Resampling.LANCZOS)
            canvas.alpha_composite(im, (x, y))
            if kind == "guiButtonType" and loc.get(name):
                draw_text(loc[name], (x, y), obj["buttonFont"], im.width, im.height,
                          not w.evaluate(bound["trigger"], [w.root]), True)
        canvas.convert("RGB").save(out / f"teal_{selected}.png")
    print(f"Production-layout previews (sample data, approximate glyphs): {out}")


if __name__ == "__main__":
    main()

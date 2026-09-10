#!/usr/bin/env python3
"""Generate a non-runtime preview for the Zhou Tianxia province emblem.

The preview deliberately stays under codex_preview/.  It does not replace any
runtime sprite until the artwork has been approved in conversation.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "codex_preview"
OUT = OUT_DIR / "gdd_tianxia_emblem_preview_v2.png"
RUNTIME_DIR = ROOT / "guangdong_independent_practice" / "gfx" / "interface"
HRE_SOURCE = Path(
    r"E:\Program Files (x86)\Steam\steamapps\common\Europa Universalis IV"
    r"\gfx\interface\hre_indicators.dds"
)
PROVINCE_BG_SOURCE = Path(
    r"E:\Program Files (x86)\Steam\steamapps\common\Europa Universalis IV"
    r"\gfx\interface\provinceview_bg.dds"
)
LIST_BUTTON_SOURCE = Path(
    r"E:\Program Files (x86)\Steam\steamapps\common\Europa Universalis IV"
    r"\gfx\interface\list_button.dds"
)
DIPLO_ARROW_SOURCE = Path(
    r"E:\Program Files (x86)\Steam\steamapps\common\Europa Universalis IV"
    r"\gfx\interface\diplo_expand_contract.dds"
)
CURRENT_SOURCE = (
    ROOT
    / "guangdong_independent_practice"
    / "gfx"
    / "interface"
    / "gdd_tianxia_province_status.tga"
)

S = 8
ICON = 42
# Native buttons start at x=20, but their passive icons start at x=32.
# Keep the approved 42px glyph and cover the union of both native controls.
SLOT_WIDTH = ICON + 12


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        Path(r"C:\Windows\Fonts\STKAITI.TTF"),
        Path(r"C:\Windows\Fonts\simkai.ttf"),
        Path(r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def draw_plus(draw: ImageDraw.ImageDraw, ox: int, oy: int) -> None:
    ox *= S
    oy *= S
    shadow = (13, 45, 33, 245)
    green_dark = (25, 133, 74, 255)
    green = (50, 224, 127, 255)
    draw.rounded_rectangle(
        (ox - 2 * S, oy + 3 * S, ox + 16 * S, oy + 9 * S),
        radius=2 * S,
        fill=shadow,
    )
    draw.rounded_rectangle(
        (ox + 4 * S, oy - 3 * S, ox + 10 * S, oy + 15 * S),
        radius=2 * S,
        fill=shadow,
    )
    draw.rounded_rectangle(
        (ox - S, oy + 4 * S, ox + 15 * S, oy + 8 * S),
        radius=S,
        fill=green_dark,
    )
    draw.rounded_rectangle(
        (ox + 5 * S, oy - 2 * S, ox + 9 * S, oy + 14 * S),
        radius=S,
        fill=green_dark,
    )
    draw.rectangle((ox, oy + 4 * S, ox + 14 * S, oy + 7 * S), fill=green)
    draw.rectangle((ox + 5 * S, oy - S, ox + 8 * S, oy + 13 * S), fill=green)


def draw_minus(draw: ImageDraw.ImageDraw, ox: int, oy: int) -> None:
    ox *= S
    oy *= S
    draw.rounded_rectangle(
        (ox - 2 * S, oy - 2 * S, ox + 15 * S, oy + 6 * S),
        radius=2 * S,
        fill=(59, 25, 22, 240),
    )
    draw.rounded_rectangle(
        (ox, oy, ox + 13 * S, oy + 4 * S),
        radius=S,
        fill=(115, 28, 25, 255),
    )
    draw.rectangle(
        (ox + S, oy, ox + 12 * S, oy + 2 * S),
        fill=(221, 52, 47, 255),
    )


def make_emblem(mode: str) -> Image.Image:
    size = ICON * S
    icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(icon)

    muted = mode == "add"
    if muted:
        gold = (169, 171, 164, 255)
        gold_shadow = (54, 57, 57, 255)
    else:
        gold = (230, 193, 92, 255)
        gold_shadow = (81, 48, 17, 255)

    # The emblem itself is deliberately only the character “周”: no plaque,
    # jade disc, ring, or background ornament.  A restrained dark outline keeps
    # it legible over arbitrary province-view artwork.
    glyph_font = font(34 * S, bold=True)
    bbox = draw.textbbox((0, 0), "周", font=glyph_font, stroke_width=0)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = 21 * S - tw // 2
    ty = 20 * S - th // 2 - bbox[1]
    draw.text(
        (tx + S, ty + 2 * S),
        "周",
        font=glyph_font,
        fill=(0, 0, 0, 150),
        stroke_width=2 * S,
        stroke_fill=(0, 0, 0, 110),
    )
    draw.text(
        (tx, ty),
        "周",
        font=glyph_font,
        fill=gold,
        stroke_width=S,
        stroke_fill=gold_shadow,
    )

    if mode == "add":
        draw_plus(draw, 27, 28)
    elif mode == "remove_hre":
        draw_minus(draw, 28, 32)

    return icon.resize((ICON, ICON), Image.Resampling.LANCZOS)


def panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=12, fill=(20, 31, 34, 245), outline=(120, 92, 45, 255), width=3)
    draw.line((x0 + 12, y0 + 8, x1 - 12, y0 + 8), fill=(210, 166, 71, 170), width=2)


def paste_scaled(canvas: Image.Image, icon: Image.Image, xy: tuple[int, int], factor: int) -> None:
    scaled = icon.resize((ICON * factor, ICON * factor), Image.Resampling.NEAREST)
    canvas.alpha_composite(scaled, xy)


def province_slot_background() -> Image.Image:
    """Return the native panel patch behind the complete imperial slot."""
    background = Image.open(PROVINCE_BG_SOURCE).convert("RGBA")
    return background.crop((20, 328, 20 + SLOT_WIDTH, 328 + ICON))


def button_strip(base: Image.Image, *, inert: bool = False) -> Image.Image:
    """Build an opaque-in-slot EU4 four-state button strip.

    The native HRE and trade-company controls are hard-coded. Painting the
    original panel pixels into each scripted frame prevents their borders from
    showing through, while the scripted control consumes their click target.
    """
    normal = base
    if inert:
        hover = pressed = disabled = base
    else:
        hover = ImageEnhance.Brightness(base).enhance(1.18)
        pressed = Image.new("RGBA", base.size, (0, 0, 0, 0))
        pressed.alpha_composite(ImageEnhance.Brightness(base).enhance(0.86), (0, 1))
        alpha = base.getchannel("A")
        disabled = ImageOps.grayscale(base).convert("RGBA")
        disabled.putalpha(alpha.point(lambda value: int(value * 0.72)))
    strip = Image.new("RGBA", (SLOT_WIDTH * 4, ICON), (0, 0, 0, 0))
    for index, frame in enumerate((normal, hover, pressed, disabled)):
        composed = province_slot_background()
        composed.alpha_composite(frame)
        strip.alpha_composite(composed, (SLOT_WIDTH * index, 0))
    return strip


def diplomacy_category_button(expanded: bool) -> Image.Image:
    """Bake the native minus/plus into a category button's own texture.

    Scripted icon visibility is not refreshed consistently by the diplomacy
    window.  Baking the mark into the two mutually-exclusive header buttons
    makes the visual state follow the same flag that controls the action row.
    """
    background = Image.open(LIST_BUTTON_SOURCE).convert("RGBA")
    arrows = Image.open(DIPLO_ARROW_SOURCE).convert("RGBA")
    frame_left = 15 if expanded else 0
    arrow = arrows.crop((frame_left, 0, frame_left + 15, 15))
    background.alpha_composite(arrow, (10, 9))
    return background


def write_runtime_assets() -> None:
    """Write the approved province and diplomacy runtime sprites."""
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {
        RUNTIME_DIR / "gdd_tianxia_province_status.tga": button_strip(
            make_emblem("member"), inert=True
        ),
        RUNTIME_DIR / "gdd_tianxia_province_add.tga": button_strip(make_emblem("add")),
        RUNTIME_DIR / "gdd_tianxia_province_remove.tga": button_strip(
            make_emblem("remove_hre")
        ),
        RUNTIME_DIR / "gdd_tianxia_actions_expanded.tga": diplomacy_category_button(
            expanded=True
        ),
        RUNTIME_DIR / "gdd_tianxia_actions_collapsed.tga": diplomacy_category_button(
            expanded=False
        ),
    }
    for path, artwork in outputs.items():
        artwork.save(path, format="TGA", compression=None)
        print(path)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    member = make_emblem("member")
    add = make_emblem("add")
    remove_hre = make_emblem("remove_hre")
    remove_gold = make_emblem("remove_gold")

    width, height = 1500, 940
    canvas = Image.new("RGBA", (width, height), (20, 23, 25, 255))
    # Subtle wine-red EoC background gradient.
    bg = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    bp = bg.load()
    for y in range(height):
        for x in range(width):
            distance = ((x - width * 0.52) ** 2 + (y - height * 0.48) ** 2) ** 0.5
            light = max(0.0, 1.0 - distance / 1050.0)
            bp[x, y] = (42 + int(25 * light), 24 + int(12 * light), 27 + int(12 * light), 255)
    canvas = Image.alpha_composite(canvas, bg)
    draw = ImageDraw.Draw(canvas)

    title_font = font(46, bold=True)
    subtitle_font = font(24)
    body_font = font(22)
    small_font = font(18)
    draw.text((60, 38), "周天下省份徽记 · 第 2 版", font=title_font, fill=(238, 205, 123, 255))
    draw.text(
        (62, 98),
        "设计基准：42×42 实机尺寸｜主体仅保留“周”字｜沿用神罗的状态语法",
        font=subtitle_font,
        fill=(211, 213, 204, 255),
    )

    panel(draw, (50, 145, 1450, 340))
    draw.text((78, 166), "原版与当前版本对照", font=subtitle_font, fill=(226, 193, 111, 255))
    if HRE_SOURCE.exists():
        hre = Image.open(HRE_SOURCE).convert("RGBA")
        canvas.alpha_composite(hre.resize((168 * 3, 42 * 3), Image.Resampling.NEAREST), (80, 205))
        draw.text((80, 310), "原版神罗：成员 / 灰态 / 加入 / 脱离", font=small_font, fill=(186, 190, 187, 255))
    if CURRENT_SOURCE.exists():
        current = Image.open(CURRENT_SOURCE).convert("RGBA")
        canvas.alpha_composite(current.resize((168 * 3, 42 * 3), Image.Resampling.NEAREST), (820, 205))
        draw.text((820, 310), "当前周天下：青铜鼎图案", font=small_font, fill=(186, 190, 187, 255))

    cards = [
        ("成员态", "静态图标，不可点击", member),
        ("加入态", "灰色“周”＋无底框绿色加号", add),
        ("脱离态 A", "真正仿神罗：小型无底框红减号", remove_hre),
        ("脱离态 B", "仅显示金色“周”，不附加减号", remove_gold),
    ]
    x_positions = [55, 415, 775, 1135]
    for (heading, desc, icon), x in zip(cards, x_positions):
        panel(draw, (x, 375, x + 310, 700))
        draw.text((x + 22, 397), heading, font=subtitle_font, fill=(235, 200, 111, 255))
        paste_scaled(canvas, icon, (x + 71, 448), 4)
        draw.text((x + 18, 632), desc, font=small_font, fill=(210, 212, 204, 255))

    panel(draw, (50, 735, 1450, 890))
    draw.text((78, 756), "实际尺寸预览（游戏中约为下列大小）", font=subtitle_font, fill=(226, 193, 111, 255))
    labels = ["成员", "可加入", "可脱离 A", "可脱离 B"]
    icons = [member, add, remove_hre, remove_gold]
    x = 470
    for label, icon in zip(labels, icons):
        canvas.alpha_composite(icon, (x, 803))
        draw.text((x - 12, 850), label, font=small_font, fill=(220, 221, 214, 255))
        x += 175

    draw.text(
        (60, 906),
        "说明：本图仅为美术确认稿，尚未替换任何 Mod 运行时资产。",
        font=small_font,
        fill=(174, 176, 170, 255),
    )
    canvas.convert("RGB").save(OUT, quality=95)
    print(OUT)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--runtime",
        action="store_true",
        help="also replace the three approved Mod runtime sprites",
    )
    args = parser.parse_args()
    main()
    if args.runtime:
        write_runtime_assets()

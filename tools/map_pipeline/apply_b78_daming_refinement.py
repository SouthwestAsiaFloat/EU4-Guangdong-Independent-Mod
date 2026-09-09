#!/usr/bin/env python3
"""Apply/check the reviewed B78 Daming three-province polity transaction.

The outer silhouette of province 2137 is immutable.  A reviewed run-length
mask divides only those 352 pixels into Weiyi, Daming and Yuancheng, then keeps
every map consumer, the new Bei polity and Zhou-system projections in sync.
"""

from __future__ import annotations

import argparse
import csv
from collections import deque
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zlib

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
HISTORY = MOD / "history/provinces"
COUNTRY_HISTORY = MOD / "history/countries"
COUNTRIES = MOD / "common/countries"
PLAN = ROOT / "planning/daming_refinement_b78"
MASKS = PLAN / "reviewed_masks.json.zlib"
BACKUP = PLAN / "pre_b78/map/provinces.bmp"
MANIFEST = PLAN / "batch_manifest.json"
PREPARED = PLAN / "review_manifest.json"
PREVIEW = PLAN / "b78_daming_refinement_preview.png"
SOURCE = MOD / "localisation_source/016_gdd_b78_daming_refinement_readable_utf8.txt"
TARGET = MOD / "localisation/replace/016_gdd_b78_daming_refinement_l_english.yml"
MARKER = "GDD_B78_DAMING_REFINEMENT"

PARENT = 2137
NEW = (5381, 5382)
ALL = (5381, 2137, 5382)
PARENT_RGB = (143, 75, 75)
RGB = {2137: PARENT_RGB, 5381: (45, 137, 169), 5382: (201, 137, 79)}
EN = {2137: "Daming", 5381: "Weiyi", 5382: "Yuancheng"}
ZH = {2137: "大名", 5381: "魏邑", 5382: "元城"}
DEV = {
    5381: (2, 3, 2),
    2137: (3, 2, 2),
    5382: (2, 2, 3),
}
GOODS = {province_id: "grain" for province_id in ALL}
OWNER = {5381: "DMG", 2137: "DMG", 5382: "GUN"}
COUNTRY_RGB = (91, 107, 76)


def block_bounds(text: str, key: str, start: int = 0) -> tuple[int, int]:
    match = re.search(rf"(?m)^[ \t]*{re.escape(key)}[ \t]*=[ \t]*\{{", text[start:])
    if not match:
        raise ValueError(f"missing block: {key}")
    begin = start + match.start()
    opening = start + match.end() - 1
    depth = 0
    quoted = False
    comment = False
    escaped = False
    for index in range(opening, len(text)):
        char = text[index]
        if comment:
            if char == "\n":
                comment = False
            continue
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == "#":
            comment = True
        elif char == '"':
            quoted = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return begin, index + 1
    raise ValueError(f"unclosed block: {key}")


def replace_block(text: str, key: str, replacement: str) -> str:
    try:
        begin, end = block_bounds(text, key)
    except ValueError:
        return text.rstrip() + "\n\n" + replacement.rstrip() + "\n"
    return text[:begin] + replacement.rstrip() + text[end:]


def remove_marker_lines(text: str) -> str:
    return re.sub(rf"(?m)^.*# {MARKER}\s*$\n?", "", text)


def remove_tokens(text: str, values: tuple[object, ...]) -> str:
    """Remove terminal B78 memberships before inserting the authoritative set.

    Older generators may already have projected the new IDs through an area.
    Removing the exact token from every sibling block keeps B49 -> B78 and
    other replay orders unique instead of relying on our own marker alone.
    """
    for value in values:
        token = re.escape(str(value))
        text = re.sub(rf"(?<![A-Za-z0-9_]){token}(?![A-Za-z0-9_])", "", text)
    return text


def add_ids(text: str, key: str, province_ids: tuple[int, ...]) -> str:
    text = remove_tokens(remove_marker_lines(text), province_ids)
    begin, end = block_bounds(text, key)
    block = text[begin:end]
    close = block.rfind("}")
    block = (
        block[:close].rstrip()
        + f"\n    {' '.join(map(str, province_ids))} # {MARKER}\n"
        + block[close:]
    )
    return text[:begin] + block + text[end:]


def add_nested_ids(
    text: str, outer: str, inner: str, province_ids: tuple[int, ...]
) -> str:
    text = remove_tokens(remove_marker_lines(text), province_ids)
    outer_begin, outer_end = block_bounds(text, outer)
    outer_block = text[outer_begin:outer_end]
    inner_begin, inner_end = block_bounds(outer_block, inner)
    inner_block = outer_block[inner_begin:inner_end]
    indent_match = re.search(
        rf"(?m)^([ \t]*){re.escape(inner)}[ \t]*=", inner_block
    )
    if indent_match is None:
        raise ValueError(f"cannot determine indentation for nested block: {inner}")
    nested_indent = indent_match.group(1)
    member_indent = nested_indent + "    "
    close = inner_block.rfind("}")
    inner_block = (
        inner_block[:close].rstrip()
        + f"\n{member_indent}{' '.join(map(str, province_ids))} # {MARKER}\n{nested_indent}"
        + inner_block[close:]
    )
    outer_block = outer_block[:inner_begin] + inner_block + outer_block[inner_end:]
    return text[:outer_begin] + outer_block + text[outer_end:]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def definitions() -> dict[int, tuple[int, int, int]]:
    result: dict[int, tuple[int, int, int]] = {}
    for line in (MAP / "definition.csv").read_text(encoding="cp1252").splitlines()[1:]:
        columns = line.split(";")
        if len(columns) >= 4 and columns[0].isdigit():
            result[int(columns[0])] = tuple(map(int, columns[1:4]))
    return result


def runs(points: set[tuple[int, int]]) -> list[list[int]]:
    rows: dict[int, list[int]] = {}
    for x, y in points:
        rows.setdefault(y, []).append(x)
    output: list[list[int]] = []
    for y, xs in sorted(rows.items()):
        xs.sort()
        start = previous = xs[0]
        for x in xs[1:]:
            if x != previous + 1:
                output.append([y, start, previous])
                start = x
            previous = x
        output.append([y, start, previous])
    return output


def cells() -> tuple[dict[str, object], dict[int, set[tuple[int, int]]]]:
    data = json.loads(zlib.decompress(MASKS.read_bytes()).decode("utf-8"))
    decoded = {
        int(province_id): {
            (x, y)
            for y, x0, x1 in record["runs"]
            for x in range(x0, x1 + 1)
        }
        for province_id, record in data["cells"].items()
    }
    return data, decoded


def connected(points: set[tuple[int, int]]) -> bool:
    if not points:
        return False
    seen = {next(iter(points))}
    queue = deque(seen)
    while queue:
        x, y = queue.popleft()
        for neighbour in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if neighbour in points and neighbour not in seen:
                seen.add(neighbour)
                queue.append(neighbour)
    return len(seen) == len(points)


def deep_point(points: set[tuple[int, int]]) -> tuple[int, int]:
    edge = {
        point
        for point in points
        if any(
            neighbour not in points
            for neighbour in (
                (point[0] - 1, point[1]),
                (point[0] + 1, point[1]),
                (point[0], point[1] - 1),
                (point[0], point[1] + 1),
            )
        )
    }
    distance = {point: 0 for point in edge}
    queue = deque(edge)
    while queue:
        point = queue.popleft()
        for neighbour in (
            (point[0] - 1, point[1]),
            (point[0] + 1, point[1]),
            (point[0], point[1] - 1),
            (point[0], point[1] + 1),
        ):
            if neighbour in points and neighbour not in distance:
                distance[neighbour] = distance[point] + 1
                queue.append(neighbour)
    return max(points, key=lambda point: (distance.get(point, 0), -point[1], -point[0]))


def build_reviewed_masks() -> dict[str, object]:
    bitmap = Image.open(MAP / "provinces.bmp").convert("RGB")
    points = {
        (x, y)
        for y in range(bitmap.height)
        for x in range(bitmap.width)
        if bitmap.getpixel((x, y)) == PARENT_RGB
    }
    if len(points) != 352:
        raise ValueError(f"expected the untouched 352-pixel Daming parent, found {len(points)}")
    x0 = min(x for x, _y in points)
    grouped: dict[int, set[tuple[int, int]]] = {province_id: set() for province_id in ALL}
    for x, y in points:
        north_cut = 796 + ((x - x0 + 2) // 7) - 1
        south_cut = 806 + ((x - x0 + 1) // 8) - 1
        if y <= north_cut:
            province_id = 5381
        elif y <= south_cut:
            province_id = 2137
        else:
            province_id = 5382
        grouped[province_id].add((x, y))
    if set().union(*grouped.values()) != points:
        raise ValueError("reviewed split does not cover the exact parent mask")
    if sum(map(len, grouped.values())) != len(points) or not all(
        connected(group) for group in grouped.values()
    ):
        raise ValueError("reviewed split overlaps or creates a disconnected province")
    data: dict[str, object] = {
        "schema_version": 1,
        "batch": "B78_daming_refinement",
        "source_province": PARENT,
        "source_rgb": list(PARENT_RGB),
        "scope_pixels": len(points),
        "bbox": [
            min(x for x, _y in points),
            min(y for _x, y in points),
            max(x for x, _y in points) + 1,
            max(y for _x, y in points) + 1,
        ],
        "cells": {
            str(province_id): {
                "name_zh": ZH[province_id],
                "rgb": list(RGB[province_id]),
                "pixel_count": len(grouped[province_id]),
                "runs": runs(grouped[province_id]),
            }
            for province_id in ALL
        },
    }
    PLAN.mkdir(parents=True, exist_ok=True)
    MASKS.write_bytes(zlib.compress(json.dumps(data, ensure_ascii=False).encode("utf-8"), 9))
    return data


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in (
        Path("/System/Library/Fonts/STHeiti Medium.ttc"),
        Path("/System/Library/Fonts/PingFang.ttc"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ):
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def render_preview(bitmap: Image.Image, output: Path) -> None:
    _data, grouped = cells()
    all_points = set().union(*grouped.values())
    x0 = max(0, min(x for x, _y in all_points) - 26)
    y0 = max(0, min(y for _x, y in all_points) - 26)
    x1 = min(bitmap.width, max(x for x, _y in all_points) + 27)
    y1 = min(bitmap.height, max(y for _x, y in all_points) + 27)
    crop = bitmap.crop((x0, y0, x1, y1)).resize(
        ((x1 - x0) * 8, (y1 - y0) * 8), Image.Resampling.NEAREST
    )
    canvas = Image.new("RGB", (crop.width + 390, max(crop.height, 650)), (238, 232, 215))
    canvas.paste(crop, (0, 0))
    draw = ImageDraw.Draw(canvas)
    title = font(30)
    body = font(22)
    small = font(18)
    draw.text((crop.width + 24, 24), "大名三省细化 · B78", fill=(41, 36, 30), font=title)
    draw.text((crop.width + 24, 70), "外边界锁定，仅重画内部省界", fill=(82, 73, 61), font=small)
    for row, province_id in enumerate(ALL):
        points = grouped[province_id]
        cx = sum(x for x, _y in points) / len(points)
        cy = sum(y for _x, y in points) / len(points)
        px = int((cx - x0) * 8)
        py = int((cy - y0) * 8)
        draw.ellipse((px - 20, py - 20, px + 20, py + 20), fill=(246, 238, 214), outline=(38, 31, 26), width=3)
        label = ZH[province_id]
        box = draw.textbbox((0, 0), label, font=small)
        draw.text((px - (box[2] - box[0]) / 2, py - 12), label, fill=(30, 26, 23), font=small)
        y = 125 + row * 90
        draw.rectangle((crop.width + 26, y, crop.width + 64, y + 38), fill=RGB[province_id], outline=(40, 35, 30), width=2)
        draw.text((crop.width + 78, y - 2), f"{province_id}  {label}", fill=(39, 34, 29), font=body)
        development = " / ".join(map(str, DEV[province_id]))
        draw.text((crop.width + 78, y + 40), f"{development} · 粮食 · {len(points)} 像素", fill=(86, 74, 61), font=small)
    draw.text((crop.width + 24, 430), "新区域：大名", fill=(39, 34, 29), font=body)
    draw.text((crop.width + 24, 470), "新国家：邶（DMG）", fill=(39, 34, 29), font=body)
    draw.text((crop.width + 24, 510), "礼教 · 法家 · 周天下普通成员", fill=(66, 58, 50), font=small)
    draw.text((crop.width + 24, 548), "邶有大名、魏邑；管有元城", fill=(66, 58, 50), font=small)
    draw.text((crop.width + 24, 584), "总发展 8 → 21；不新增贸易中心", fill=(66, 58, 50), font=small)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)


def prepare() -> None:
    data = build_reviewed_masks()
    bitmap = Image.open(MAP / "provinces.bmp").convert("RGB")
    _meta, grouped = cells()
    for province_id, points in grouped.items():
        for point in points:
            bitmap.putpixel(point, RGB[province_id])
    render_preview(bitmap, PLAN / "b78_daming_refinement_review.png")
    PREPARED.write_text(
        json.dumps(
            {
                "batch": "B78_daming_refinement",
                "status": "reviewed_geometry_frozen",
                "reviewed_masks_sha256": sha256(MASKS),
                "scope_pixels": data["scope_pixels"],
                "pixel_counts": {
                    province_id: record["pixel_count"]
                    for province_id, record in data["cells"].items()
                },
                "outer_boundary_policy": "exact parent mask; no exterior pixel changes",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"{MARKER}_PREPARED; {data['scope_pixels']} reviewed pixels")


def apply_bitmap() -> int:
    if not MASKS.exists():
        raise ValueError("reviewed mask archive is missing; run --prepare first")
    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    path = MAP / "provinces.bmp"
    if not BACKUP.exists():
        shutil.copy2(path, BACKUP)
    _data, grouped = cells()
    allowed = set(RGB.values())
    bitmap = Image.open(path).convert("RGB")
    changed = 0
    for province_id, points in grouped.items():
        for point in points:
            current = bitmap.getpixel(point)
            if current not in allowed:
                raise ValueError(f"guarded mask found unknown RGB {current} at {point}")
            if current != RGB[province_id]:
                bitmap.putpixel(point, RGB[province_id])
                changed += 1
    bitmap.save(path, format="BMP")
    return changed


def update_definitions() -> None:
    path = MAP / "definition.csv"
    lines = []
    for line in path.read_text(encoding="cp1252").splitlines():
        columns = line.split(";")
        if columns and columns[0].isdigit() and int(columns[0]) in NEW:
            continue
        lines.append(line)
    for province_id in NEW:
        red, green, blue = RGB[province_id]
        lines.append(f"{province_id};{red};{green};{blue};{EN[province_id]};x")
    path.write_text("\n".join(lines) + "\n", encoding="cp1252")
    path = MAP / "default.map"
    text, count = re.subn(
        r"(?m)^max_provinces\s*=\s*\d+", "max_provinces = 5383", path.read_text(encoding="cp1252"), count=1
    )
    if count != 1:
        raise ValueError("default.map is missing max_provinces")
    path.write_text(text, encoding="cp1252")


def dated_suffix(text: str) -> str:
    match = re.search(r"(?m)^\s*\d+\.\d+\.\d+\s*=\s*\{", text)
    return text[match.start():].strip() + "\n" if match else ""


def province_history(province_id: int, suffix: str = "") -> str:
    tax, production, manpower = DEV[province_id]
    owner = OWNER[province_id]
    body = f'''# {province_id} - {EN[province_id]} - {MARKER}

owner = {owner}
controller = {owner}
add_core = {owner}
culture = gdd_zhongyuan
religion = confucianism
capital = "{EN[province_id]}"
trade_goods = {GOODS[province_id]}
hre = no
base_tax = {tax}
base_production = {production}
base_manpower = {manpower}
is_city = yes
discovered_by = chinese
discovered_by = nomad_group
'''
    return body.rstrip() + ("\n\n" + suffix if suffix else "\n")


def update_histories() -> None:
    old_path = next(HISTORY.glob("2137 - *.txt"))
    suffix = dated_suffix(old_path.read_text(encoding="utf-8-sig"))
    desired = {
        2137: HISTORY / "2137 - Daming.txt",
        5381: HISTORY / "5381 - Weiyi.txt",
        5382: HISTORY / "5382 - Yuancheng.txt",
    }
    for province_id, path in desired.items():
        for old in HISTORY.glob(f"{province_id} - *.txt"):
            if old != path:
                old.unlink()
        path.write_text(
            province_history(province_id, suffix if province_id == 2137 else ""),
            encoding="utf-8",
        )


def position_block(province_id: int, x: int, y: int) -> str:
    points = " ".join(f"{x:.3f} {y:.3f}" for _index in range(7))
    return f'''#{EN[province_id]} - {MARKER}
{province_id}={{
    position={{
        {points}
    }}
    rotation={{
        0.000 0.000 0.000 0.000 0.000 0.000 0.000
    }}
    height={{
        0.000 0.000 1.000 0.000 0.000 0.000 0.000
    }}
}}'''


def update_positions() -> None:
    _data, grouped = cells()
    height = Image.open(MAP / "provinces.bmp").height
    path = MAP / "positions.txt"
    text = path.read_text(encoding="cp1252")
    text = re.sub(rf"(?m)^#.* - {MARKER}\n", "", text)
    for province_id in ALL:
        x, y = deep_point(grouped[province_id])
        block = position_block(province_id, x, height - y)
        try:
            begin, end = block_bounds(text, str(province_id))
            text = text[:begin] + block + text[end:]
        except ValueError:
            text = text.rstrip() + "\n\n" + block + "\n"
    path.write_text(text, encoding="cp1252")


def update_memberships() -> None:
    path = MAP / "area.txt"
    text = path.read_text(encoding="cp1252")
    text = replace_block(
        text,
        "south_hebei_area",
        "south_hebei_area = { # B31 Han land-contiguous area reorganisation\n    4195 5221 5220 5218 696\n}",
    )
    text = replace_block(
        text,
        "daming_area",
        f"daming_area = {{ # {MARKER}\n    5381 2137 5382\n}}",
    )
    path.write_text(text, encoding="cp1252")

    path = MAP / "region.txt"
    text = add_nested_ids(path.read_text(encoding="cp1252"), "north_china_region", "areas", ("daming_area",))
    path.write_text(text, encoding="cp1252")

    for relative, key in (("map/climate.txt", "mild_winter"), ("map/continent.txt", "asia")):
        path = MOD / relative
        path.write_text(add_ids(path.read_text(encoding="cp1252"), key, NEW), encoding="cp1252")

    path = MAP / "terrain.txt"
    path.write_text(
        add_nested_ids(path.read_text(encoding="cp1252"), "farmlands", "terrain_override", NEW),
        encoding="cp1252",
    )
    path = MOD / "common/tradenodes/00_tradenodes.txt"
    path.write_text(
        add_nested_ids(path.read_text(encoding="cp1252"), "beijing", "members", NEW),
        encoding="cp1252",
    )
    path = MOD / "common/trade_companies/00_trade_companies.txt"
    path.write_text(
        add_nested_ids(
            path.read_text(encoding="cp1252"),
            "trade_company_north_china",
            "provinces",
            NEW,
        ),
        encoding="cp1252",
    )


def update_country() -> None:
    tags = MOD / "common/country_tags/gdd_country_tags.txt"
    text = re.sub(
        rf"(?ms)^# {MARKER}_TAG_BEGIN\n.*?^# {MARKER}_TAG_END\n?",
        "",
        tags.read_text(encoding="utf-8-sig"),
    ).rstrip()
    text += (
        f'\n\n# {MARKER}_TAG_BEGIN\n'
        'DMG = "countries/B78_Bei.txt"\n'
        f'# {MARKER}_TAG_END\n'
    )
    tags.write_text(text, encoding="utf-8")

    if str(ROOT / "tools") not in sys.path:
        sys.path.insert(0, str(ROOT / "tools"))
    from country_name_pool_support import country_definition_bytes

    definition = (
        f"# B78 Bei polity definition.\n"
        "graphical_culture = asiangfx\n\n"
        f"color = {{ {' '.join(map(str, COUNTRY_RGB))} }}\n"
        "revolutionary_colors = { 4 7 2 }\n"
    )
    COUNTRIES.mkdir(parents=True, exist_ok=True)
    obsolete_definition = COUNTRIES / "B78_Daming.txt"
    if obsolete_definition.exists():
        obsolete_definition.unlink()
    (COUNTRIES / "B78_Bei.txt").write_bytes(
        country_definition_bytes(definition, "gdd_zhongyuan")
    )
    COUNTRY_HISTORY.mkdir(parents=True, exist_ok=True)
    obsolete_history = COUNTRY_HISTORY / "DMG - Daming.txt"
    if obsolete_history.exists():
        obsolete_history.unlink()
    (COUNTRY_HISTORY / "DMG - Bei.txt").write_text(
        """# B78 Bei polity history.
government = monarchy
add_government_reform = feudalism_reform
government_rank = 1
technology_group = chinese
religion = confucianism
primary_culture = gdd_zhongyuan
capital = 2137
fixed_capital = 2137
""",
        encoding="utf-8",
    )
    gun = COUNTRY_HISTORY / "GUN - Guan.txt"
    data = gun.read_bytes()
    for key in (b"capital", b"fixed_capital"):
        data, count = re.subn(
            rb"(?m)^(\s*" + key + rb"\s*=\s*)\d+",
            lambda match: match.group(1) + b"5382",
            data,
            count=1,
        )
        if count != 1:
            raise ValueError(f"GUN history is missing {key.decode()}")
    gun.write_bytes(data)


def update_localisation() -> None:
    SOURCE.write_text(
        """l_english:
 PROV5381:0 "魏邑"
 PROV_ADJ5381:0 "魏邑"
 PROV5382:0 "元城"
 PROV_ADJ5382:0 "元城"
 DMG:0 "邶"
 DMG_ADJ:0 "邶"
""",
        encoding="utf-8-sig",
    )
    subprocess.run(
        [sys.executable, str(ROOT / "tools/map_pipeline/apply_chunqiu_area_localisation.py")],
        cwd=ROOT,
        check=True,
    )
    if str(ROOT / "tools") not in sys.path:
        sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import encode_file, verify_file

    encode_file(SOURCE, TARGET)
    verify_file(SOURCE, TARGET)
    # The area-name transaction also updates the authoritative zzz source.
    subprocess.run(
        [sys.executable, str(ROOT / "tools/encode_eu4_chinese_localisation.py")],
        cwd=ROOT,
        check=True,
    )


def ensure_tag_after_anchor(path: Path, anchor: str, tag: str, expected: int) -> None:
    text = path.read_text(encoding="utf-8")
    text = re.sub(rf"(?m)^\s*tag\s*=\s*{re.escape(tag)}\s*$\n?", "", text)
    lines = text.splitlines()
    output: list[str] = []
    inserted = 0
    for line in lines:
        output.append(line)
        match = re.match(rf"^(\s*)tag\s*=\s*{re.escape(anchor)}\s*$", line)
        if match:
            output.append(f"{match.group(1)}tag = {tag}")
            inserted += 1
    if inserted != expected:
        raise ValueError(
            f"{path.name}: expected {expected} {anchor} anchors, found {inserted}"
        )
    path.write_text("\n".join(output) + "\n", encoding="utf-8")


def update_zhx_projections() -> None:
    """Make the new Zhou member and opening school part of the B78 transaction."""
    manifest_path = ROOT / "planning/religion_opening_schools/opening_schools_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    schools = manifest["schools"]
    for config in schools.values():
        config["tags"] = [tag for tag in config["tags"] if tag != "DMG"]
    legalist = schools["fa"]["tags"]
    insertion = legalist.index("GUN") + 1 if "GUN" in legalist else 0
    legalist.insert(insertion, "DMG")
    for config in schools.values():
        config["expected_count"] = len(config["tags"])
    manifest["expected_total"] = sum(len(config["tags"]) for config in schools.values())
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    ensure_tag_after_anchor(
        MOD / "events/zhx_opening_school_events.txt", "GUN", "DMG", expected=2
    )
    ensure_tag_after_anchor(
        MOD / "common/scripted_effects/zhx_system_effects.txt",
        "GUN",
        "DMG",
        expected=1,
    )


def update_culture_manifest() -> None:
    path = ROOT / "planning/culture_overhaul/approved_province_culture_assignments.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fields = list(rows[0])
    rows = [row for row in rows if int(row["province_id"]) not in NEW]
    for province_id in NEW:
        rows.append(
            {
                "province_id": str(province_id),
                "province_name": ZH[province_id],
                "document_group": "汉文化组",
                "document_culture": "中原文化",
                "document_entry": ZH[province_id],
                "target_culture": "gdd_zhongyuan",
                "source_rule": "B78",
                "decision_note": "继承大名母省；锁定外缘后的内部三分",
            }
        )
    rows.sort(key=lambda row: int(row["province_id"]))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def update_registry() -> None:
    path = ROOT / "docs/map/china_province_split_registry.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fields = list(rows[0])
    rows = [row for row in rows if row["draw_batch"] != "B78"]
    for index, province_id in enumerate(NEW, 1):
        row = {field: "" for field in fields}
        row.update(
            design_key=f"B78-{index:02d}",
            game_id=str(province_id),
            rgb_r=str(RGB[province_id][0]),
            rgb_g=str(RGB[province_id][1]),
            rgb_b=str(RGB[province_id][2]),
            macro_region="north_china",
            draw_batch="B78",
            new_name_zh=ZH[province_id],
            new_name_en=EN[province_id],
            internal_key_hint=f"gdd_b78_{province_id}",
            parent_id="2137",
            parent_definition_name="Daming",
            parent_history_name="Daming",
            parent_area="south_hebei_area",
            parent_tax="3",
            parent_production="3",
            parent_manpower="2",
            retained_name_zh="大名",
            retained_tax=str(DEV[2137][0]),
            retained_production=str(DEV[2137][1]),
            retained_manpower=str(DEV[2137][2]),
            new_tax=str(DEV[province_id][0]),
            new_production=str(DEV[province_id][1]),
            new_manpower=str(DEV[province_id][2]),
            split_group="b78-p2137",
            group_dev_delta="13" if index == 1 else "0",
            proposed_owner=OWNER[province_id],
            status="implemented",
            rationale="锁定原大名外缘，只以两条折线重画内部边界；大名、魏邑属邶，元城属管。",
        )
        rows.append(row)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)


def update_generated_system_views() -> None:
    update_zhx_projections()
    subprocess.run(
        [sys.executable, str(ROOT / "tools/generate_zhx_tianxia_roster.py")],
        cwd=ROOT,
        check=True,
    )
    mask_generator = ROOT / "tools/generate_dmg_bei_small_seal_mask.py"
    if mask_generator.exists():
        subprocess.run([sys.executable, str(mask_generator)], cwd=ROOT, check=True)
    subprocess.run(
        [sys.executable, str(ROOT / "tools/generate_zhuxia_seal_flags.py")],
        cwd=ROOT,
        check=True,
    )


def province_ids_in_block(path: Path, *keys: str) -> set[int]:
    text = path.read_text(encoding="cp1252")
    begin = 0
    end = len(text)
    block = text
    for key in keys:
        begin, end = block_bounds(block, key)
        block = block[begin:end]
    return {int(value) for value in re.findall(r"\b\d+\b", re.sub(r"#.*", "", block))}


def area_connected(province_ids: set[int]) -> bool:
    rows = definitions()
    colour_to_id = {colour: province_id for province_id, colour in rows.items()}
    bitmap = Image.open(MAP / "provinces.bmp").convert("RGB")
    adjacency = {province_id: set() for province_id in province_ids}
    pixels = bitmap.load()
    for y in range(bitmap.height):
        for x in range(bitmap.width):
            first = colour_to_id.get(pixels[x, y])
            if first not in province_ids:
                continue
            for nx, ny in ((x + 1, y), (x, y + 1)):
                if nx >= bitmap.width or ny >= bitmap.height:
                    continue
                second = colour_to_id.get(pixels[nx, ny])
                if second in province_ids and second != first:
                    adjacency[first].add(second)
                    adjacency[second].add(first)
    seen = {next(iter(province_ids))}
    queue = deque(seen)
    while queue:
        current = queue.popleft()
        for neighbour in adjacency[current] - seen:
            seen.add(neighbour)
            queue.append(neighbour)
    return seen == province_ids


def validate() -> dict[str, object]:
    data, grouped = cells()
    if data["scope_pixels"] != 352 or sum(map(len, grouped.values())) != 352:
        raise ValueError("Daming reviewed scope is not exactly 352 pixels")
    union = set().union(*grouped.values())
    if len(union) != sum(map(len, grouped.values())) or not all(
        connected(points) for points in grouped.values()
    ):
        raise ValueError("Daming provinces are not a clean connected partition")
    rows = definitions()
    bitmap = Image.open(MAP / "provinces.bmp").convert("RGB")
    for province_id, points in grouped.items():
        if rows.get(province_id) != RGB[province_id]:
            raise ValueError(f"province {province_id} has wrong definition RGB")
        collisions = [pid for pid, colour in rows.items() if colour == RGB[province_id]]
        if collisions != [province_id]:
            raise ValueError(f"province {province_id} RGB collision: {collisions}")
        if any(bitmap.getpixel(point) != RGB[province_id] for point in points):
            raise ValueError(f"province {province_id} bitmap mask drifted")
    if BACKUP.exists():
        before = Image.open(BACKUP).convert("RGB")
        x0, y0, x1, y1 = map(int, data["bbox"])
        scope = set().union(*grouped.values())
        exterior_changes = sum(
            before.getpixel((x, y)) != bitmap.getpixel((x, y))
            for y in range(y0, y1)
            for x in range(x0, x1)
            if (x, y) not in scope
        )
        if exterior_changes:
            raise ValueError(f"{exterior_changes} pixels changed outside the locked parent mask")
    if "max_provinces = 5383" not in (MAP / "default.map").read_text(encoding="cp1252"):
        raise ValueError("max_provinces is not the exclusive ceiling 5383")
    daming = province_ids_in_block(MAP / "area.txt", "daming_area")
    zhaodi = province_ids_in_block(MAP / "area.txt", "south_hebei_area")
    if daming != set(ALL) or zhaodi != {4195, 5221, 5220, 5218, 696}:
        raise ValueError(f"area drift: Daming={sorted(daming)}, Zhaodi={sorted(zhaodi)}")
    if not area_connected(daming) or not area_connected(zhaodi):
        raise ValueError("Daming or residual Zhaodi is disconnected")
    if "daming_area" not in (MAP / "region.txt").read_text(encoding="cp1252"):
        raise ValueError("Daming area is absent from north_china_region")
    for path, keys in (
        (MAP / "climate.txt", ("mild_winter",)),
        (MAP / "continent.txt", ("asia",)),
        (MAP / "terrain.txt", ("farmlands", "terrain_override")),
        (MOD / "common/tradenodes/00_tradenodes.txt", ("beijing", "members")),
        (
            MOD / "common/trade_companies/00_trade_companies.txt",
            ("trade_company_north_china", "provinces"),
        ),
    ):
        members = province_ids_in_block(path, *keys)
        if not set(NEW) <= members:
            raise ValueError(f"{path.name} is missing a new Daming province")
    # Every new playable ID must have exactly one assignment in each exclusive
    # membership family. This catches a province being quietly left in a stale
    # terrain, climate, continent, area, node or trade-company block.
    exclusive_membership_paths = (
        MAP / "area.txt",
        MAP / "climate.txt",
        MAP / "continent.txt",
        MAP / "terrain.txt",
        MOD / "common/tradenodes/00_tradenodes.txt",
        MOD / "common/trade_companies/00_trade_companies.txt",
    )
    for path in exclusive_membership_paths:
        cleaned = re.sub(r"#.*", "", path.read_text(encoding="cp1252"))
        for province_id in NEW:
            occurrences = len(re.findall(rf"\b{province_id}\b", cleaned))
            if occurrences != 1:
                raise ValueError(
                    f"{path.name}: province {province_id} occurs {occurrences} times, expected once"
                )
    positions = (MAP / "positions.txt").read_text(encoding="cp1252")
    for province_id in ALL:
        if len(re.findall(rf"(?m)^\s*{province_id}\s*=\s*\{{", positions)) != 1:
            raise ValueError(f"province {province_id} does not have exactly one position block")
        matches = list(HISTORY.glob(f"{province_id} - *.txt"))
        if len(matches) != 1:
            raise ValueError(f"province {province_id} has {len(matches)} history files")
        text = matches[0].read_text(encoding="utf-8-sig")
        owner = OWNER[province_id]
        required = (
            f"owner = {owner}",
            f"controller = {owner}",
            f"add_core = {owner}",
            "culture = gdd_zhongyuan",
            "religion = confucianism",
            "trade_goods = grain",
            f"base_tax = {DEV[province_id][0]}",
            f"base_production = {DEV[province_id][1]}",
            f"base_manpower = {DEV[province_id][2]}",
        )
        if not all(value in text for value in required) or "center_of_trade" in text:
            raise ValueError(f"province {province_id} history policy drifted")
    gun = (COUNTRY_HISTORY / "GUN - Guan.txt").read_text(encoding="utf-8-sig", errors="ignore")
    if "capital = 5382" not in gun or "fixed_capital = 5382" not in gun:
        raise ValueError("GUN did not retain its Daming-area seat at Yuancheng (5382)")
    dmg = (COUNTRY_HISTORY / "DMG - Bei.txt").read_text(encoding="utf-8")
    if "capital = 2137" not in dmg or "religion = confucianism" not in dmg:
        raise ValueError("DMG country history is incomplete")
    tags = (MOD / "common/country_tags/gdd_country_tags.txt").read_text(encoding="utf-8-sig")
    if tags.count('DMG = "countries/B78_Bei.txt"') != 1:
        raise ValueError("DMG tag declaration is missing")
    country_definition = COUNTRIES / "B78_Bei.txt"
    if not country_definition.exists() or not re.search(
        rb"(?m)^color\s*=\s*\{\s*91\s+107\s+76\s*\}\s*$",
        country_definition.read_bytes(),
    ):
        raise ValueError("DMG country definition or political-map color drifted")
    system = (MOD / "common/scripted_effects/zhx_system_effects.txt").read_text(encoding="utf-8")
    opening = (MOD / "events/zhx_opening_school_events.txt").read_text(encoding="utf-8")
    if system.count("tag = DMG") != 1 or opening.count("tag = DMG") != 2:
        raise ValueError("DMG Zhou membership or opening Legalist projection is incomplete")
    if sum(sum(DEV[province_id]) for province_id in ALL) != 21:
        raise ValueError("Daming development policy drifted")
    if not SOURCE.exists() or not TARGET.exists():
        raise ValueError("B78 readable or encoded localisation is missing")
    flag = MOD / "gfx/flags/DMG.tga"
    if not flag.exists() or flag.stat().st_size != 18 + 128 * 128 * 3:
        raise ValueError("DMG small-seal flag is missing or not a 128x128 24-bit TGA")
    return {
        "scope_pixels": 352,
        "pixel_counts": {str(pid): len(points) for pid, points in grouped.items()},
        "development": {"before": 8, "after": 21, "average": 7},
        "area": "daming_area",
        "country": "DMG (Bei)",
        "zhou_member": True,
        "opening_school": "fa",
    }


def write_plan_files(changed_pixels: int, validation: dict[str, object]) -> None:
    PLAN.mkdir(parents=True, exist_ok=True)
    (PLAN / "README.md").write_text(
        """# B78 大名三省细化与邶国

- 锁定原 `2137` 的 352 像素外缘，只重画内部两条折线。
- 北 `5381 魏邑`、中 `2137 大名`、南 `5382 元城`，组成 `daming_area`。
- 三省均为中原文化、礼教、农田、温和冬季与粮食；每省总发展均为 `7`，总发展 `8→21`，无贸易中心。
- 史实国号 `DMG 邶` 为独立的周天下普通成员，开局法家，占大名、魏邑；元城归管国并为管国国都。
- 邶国旗使用有出处的《说文》小篆“邶”，由仓库统一诸夏篆书旗生成器生成。
""",
        encoding="utf-8",
    )
    MANIFEST.write_text(
        json.dumps(
            {
                "batch": "B78_daming_refinement",
                "marker": MARKER,
                "reviewed_masks_sha256": sha256(MASKS),
                "backup_sha256": sha256(BACKUP),
                "canonical_bitmap_sha256": sha256(MAP / "provinces.bmp"),
                "reviewed_recolor_pixels": sum(
                    validation["pixel_counts"][str(province_id)] for province_id in NEW
                ),
                "changed_pixels_this_run": changed_pixels,
                "validation": validation,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def apply() -> None:
    changed = apply_bitmap()
    update_definitions()
    update_histories()
    update_positions()
    update_memberships()
    update_country()
    update_localisation()
    update_culture_manifest()
    update_registry()
    update_generated_system_views()
    render_preview(Image.open(MAP / "provinces.bmp").convert("RGB"), PREVIEW)
    result = validate()
    write_plan_files(changed, result)
    print(f"{MARKER}; PASS; CHANGED_PIXELS:{changed}; DEV:8->21")


def check() -> None:
    result = validate()
    subprocess.run(
        [sys.executable, str(ROOT / "tools/encode_eu4_chinese_localisation.py"), "--check"],
        cwd=ROOT,
        check=True,
    )
    subprocess.run([sys.executable, str(ROOT / "tools/validate_zhx_opening_schools.py")], cwd=ROOT, check=True)
    subprocess.run([sys.executable, str(ROOT / "tools/validate_gdd_eoc_layout.py")], cwd=ROOT, check=True)
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/map_pipeline/apply_b49_eight_node_trade_network.py"),
            "--check",
        ],
        cwd=ROOT,
        check=True,
    )
    mask_generator = ROOT / "tools/generate_dmg_bei_small_seal_mask.py"
    if mask_generator.exists():
        subprocess.run([sys.executable, str(mask_generator), "--check"], cwd=ROOT, check=True)
    subprocess.run(
        [sys.executable, str(ROOT / "tools/generate_zhuxia_seal_flags.py"), "--check"],
        cwd=ROOT,
        check=True,
    )
    print(f"{MARKER}_CHECK; PASS; {json.dumps(result, ensure_ascii=False)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.prepare:
        prepare()
    elif args.check:
        check()
    else:
        apply()


if __name__ == "__main__":
    main()

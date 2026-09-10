#!/usr/bin/env python3
"""Create a 220px version of EU4's native 149px HRE action button."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path(
    r"E:\Program Files (x86)\Steam\steamapps\common\Europa Universalis IV"
    r"\gfx\interface\button_type_1.dds"
)
OUTPUT = (
    ROOT
    / "guangdong_independent_practice"
    / "gfx"
    / "interface"
    / "gdd_eoc_button_type_1_220.tga"
)
SOURCE_SIZE = (149, 31)
OUTPUT_SIZE = (220, 31)
EDGE = 42


def render(source_path: Path) -> Image.Image:
    source = Image.open(source_path).convert("RGBA")
    if source.size != SOURCE_SIZE:
        raise SystemExit(f"unexpected native HRE button size: {source.size}")
    output = Image.new("RGBA", OUTPUT_SIZE, (0, 0, 0, 0))
    output.alpha_composite(source.crop((0, 0, EDGE, 31)), (0, 0))
    middle = source.crop((EDGE, 0, SOURCE_SIZE[0] - EDGE, 31)).resize(
        (OUTPUT_SIZE[0] - 2 * EDGE, 31), Image.Resampling.BILINEAR
    )
    output.alpha_composite(middle, (EDGE, 0))
    output.alpha_composite(
        source.crop((SOURCE_SIZE[0] - EDGE, 0, SOURCE_SIZE[0], 31)),
        (OUTPUT_SIZE[0] - EDGE, 0),
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = render(args.source)
    if args.check:
        if not OUTPUT.exists() or Image.open(OUTPUT).convert("RGBA").tobytes() != expected.tobytes():
            raise SystemExit(f"outdated generated asset: {OUTPUT}")
        print(f"ok: {OUTPUT}")
        return
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    expected.save(OUTPUT, format="TGA", compression=None)
    print(OUTPUT)


if __name__ == "__main__":
    main()

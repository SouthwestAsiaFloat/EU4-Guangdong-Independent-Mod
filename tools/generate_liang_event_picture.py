#!/usr/bin/env python3
"""Render the Liang audience source art as an EU4 event-picture DDS."""

from __future__ import annotations

import argparse
import io
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools/assets/event_pictures/gdd_liang_audience_source.png"
TARGET = (
    ROOT
    / "guangdong_independent_practice/gfx/event_pictures/"
    "gdd_liang_restoration/gdd_liang_audience_eventPicture.dds"
)
SOURCE_SIZE = (2016, 520)
TARGET_SIZE = (512, 132)


def render() -> Image.Image:
    source = Image.open(SOURCE).convert("RGB")
    if source.size != SOURCE_SIZE:
        raise ValueError(
            f"unexpected Liang audience source dimensions: {source.size}; "
            f"expected {SOURCE_SIZE}"
        )
    picture = source.resize(TARGET_SIZE, Image.Resampling.LANCZOS).convert("RGBA")
    picture.putalpha(255)
    return picture


def dds_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="DDS")
    return buffer.getvalue()


def run(check: bool) -> None:
    data = dds_bytes(render())
    if check:
        if not TARGET.is_file() or TARGET.read_bytes() != data:
            raise ValueError(f"{TARGET.name}: stale Liang audience event picture")
        action = "checked"
    else:
        TARGET.parent.mkdir(parents=True, exist_ok=True)
        TARGET.write_bytes(data)
        action = "generated"
    print(f"{action} {TARGET_SIZE[0]}x{TARGET_SIZE[1]} Liang audience DDS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    run(args.check)


if __name__ == "__main__":
    main()

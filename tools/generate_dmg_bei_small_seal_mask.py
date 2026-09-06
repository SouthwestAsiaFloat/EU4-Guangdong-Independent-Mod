#!/usr/bin/env python3
"""Extract and register the documented small-seal 邶 mask for DMG."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import zlib
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "tools/assets/zhuxia_seal_masks.json.zlib"
REFERENCE = ROOT / "tools/assets/bei_flag/bei_small_seal_reference.jpg"
SOURCE_MASK = ROOT / "tools/assets/bei_flag/bei_small_seal_mask.png"
PREVIEW = ROOT / "planning/daming_refinement_b78/bei_small_seal_flag_preview.png"

SIZE = 128
GLYPH_WIDTH = 82
GLYPH_HEIGHT = 108
BACKGROUND = (91, 107, 76)
INK = (232, 218, 164)
REFERENCE_SHA256 = "ae6830a4ae890f27ed827caee4a1c6c12d49a64cd6e04a627dd1af7605449184"


def build_mask() -> Image.Image:
    """Turn the cited black-on-white small-seal form into a centred mask."""
    if not REFERENCE.exists():
        raise FileNotFoundError(f"missing documented DMG glyph reference: {REFERENCE}")
    digest = hashlib.sha256(REFERENCE.read_bytes()).hexdigest()
    if digest != REFERENCE_SHA256:
        raise ValueError(f"documented DMG glyph reference hash drifted: {digest}")
    reference = Image.open(REFERENCE).convert("L")
    # White becomes transparent and black becomes opaque. Clear the pale JPEG
    # halo, then lift the original stroke opacity for legibility at 32 pixels.
    ink = ImageOps.invert(reference).point(
        lambda value: 0 if value < 40 else min(255, round(value * 1.5))
    )
    bounds = ink.getbbox()
    if not bounds:
        raise ValueError("documented DMG glyph reference contains no visible ink")
    glyph = ink.crop(bounds)
    scale = min(GLYPH_WIDTH / glyph.width, GLYPH_HEIGHT / glyph.height)
    glyph = glyph.resize(
        (max(1, round(glyph.width * scale)), max(1, round(glyph.height * scale))),
        Image.Resampling.LANCZOS,
    )
    mask = Image.new("L", (SIZE, SIZE), 0)
    x = (SIZE - glyph.width) // 2
    y = (SIZE - glyph.height) // 2
    mask.paste(glyph, (x, y))
    return mask


def png_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def preview_bytes(mask: Image.Image) -> bytes:
    flag = Image.new("RGB", (SIZE, SIZE), BACKGROUND)
    flag.paste(Image.new("RGB", flag.size, INK), (0, 0), mask)
    return png_bytes(flag)


def archive_bytes(mask: Image.Image) -> bytes:
    content = json.loads(zlib.decompress(ARCHIVE.read_bytes()))
    content["DMG"] = base64.b64encode(mask.tobytes()).decode("ascii")
    raw = json.dumps(
        content,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return zlib.compress(raw, level=9)


def run(check: bool = False) -> None:
    mask = build_mask()
    outputs = {
        SOURCE_MASK: png_bytes(mask),
        PREVIEW: preview_bytes(mask),
        ARCHIVE: archive_bytes(mask),
    }
    changed: list[str] = []
    for path, data in outputs.items():
        if check:
            if not path.exists() or path.read_bytes() != data:
                raise ValueError(f"stale DMG small-seal asset: {path}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            previous = path.read_bytes() if path.exists() else None
            if previous != data:
                path.write_bytes(data)
                changed.append(str(path.relative_to(ROOT)))
    print(f"{'checked' if check else 'generated'} DMG small-seal mask; changed={changed}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    run(args.check)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Deterministically extract, resize and export the approved v02 generated sprites.

No art is drawn or recoloured. The generated RGB sheet has an unwanted pale
checkerboard, so edge-connected neutral pale pixels become transparent. A one
source-pixel alpha inset removes the baked antialias fringe before downsampling.
Pillow writes legacy uncompressed A8R8G8B8 DDS with no mipmaps.
"""
from collections import deque
import hashlib
import json
from pathlib import Path
import struct

from PIL import Image, ImageFilter
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / "planning/chaozhou_government_art"
OUT = Path(__file__).resolve().parent / "production"
DDS = ROOT / "guangdong_independent_practice/gfx/interface/gdd_czc_government"
SOURCE = ART / "chaozhou_government_art_v02.source.png"
SPECS = {
    "frame": ((120, 145, 1420, 370), (280, 50)),
    "gentry": ((70, 475, 440, 845), (32, 32)),
    "ruler": ((460, 480, 805, 845), (32, 32)),
    "pointer": ((870, 530, 1040, 800), (16, 24)),
    "government_reform": ((1090, 480, 1465, 845), (64, 64)),
}


def extract(piece):
    rgb = np.asarray(piece.convert("RGB"), dtype=np.int16)
    height, width = rgb.shape[:2]
    # Only the pale neutral backdrop may be removed; enclosed foreground details
    # never participate, even if they have the same brightness as the backdrop.
    candidate = (rgb.min(axis=2) >= 175) & (np.ptp(rgb, axis=2) <= 40)
    background = np.zeros((height, width), dtype=bool)
    queue = deque()
    for x in range(width):
        queue.extend(((x, 0), (x, height - 1)))
    for y in range(height):
        queue.extend(((0, y), (width - 1, y)))
    while queue:
        x, y = queue.popleft()
        if x < 0 or y < 0 or x >= width or y >= height:
            continue
        if background[y, x] or not candidate[y, x]:
            continue
        background[y, x] = True
        queue.extend(((x-1, y), (x+1, y), (x, y-1), (x, y+1)))
    alpha = Image.fromarray(np.where(background, 0, 255).astype("uint8"))
    alpha = alpha.filter(ImageFilter.MinFilter(3))
    rgba = piece.convert("RGBA")
    rgba.putalpha(alpha)
    box = rgba.getbbox()
    assert box, "Empty sprite"
    return rgba, box


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    DDS.mkdir(parents=True, exist_ok=True)
    source = Image.open(SOURCE)
    assert source.size == (1536, 1024)
    sheet = Image.new("RGBA", source.size)
    manifest = {
        "source": str(SOURCE.relative_to(ROOT)),
        "source_sha256": sha256(SOURCE),
        "mode": "built-in imagegen; mechanical edge-connected alpha extraction",
        "dds_format": "legacy uncompressed A8R8G8B8, no mipmaps",
        "sprites": {},
    }
    singles = {}
    for name, (window, size) in SPECS.items():
        extracted, box = extract(source.crop(window))
        sheet.alpha_composite(extracted, (window[0], window[1]))
        cropped = extracted.crop(box)
        cropped.save(OUT / f"{name}.source_rgba.png")
        sprite = cropped.resize(size, Image.Resampling.LANCZOS)
        singles[name] = sprite
        frames = 2 if name in {"gentry", "ruler"} else 1
        result = Image.new("RGBA", (size[0] * frames, size[1]))
        for frame in range(frames):
            result.alpha_composite(sprite, (size[0] * frame, 0))
        png = OUT / f"{name}.png"
        dds = DDS / f"{name}.dds"
        result.save(png)
        result.save(dds)
        roundtrip = Image.open(dds).convert("RGBA")
        assert roundtrip.size == result.size
        assert roundtrip.tobytes() == result.tobytes(), name
        assert result.getchannel("A").getextrema() == (0, 255), name
        header = struct.unpack("<31I", dds.read_bytes()[4:128])
        assert header[21] == 32 and header[20] == 0  # 32bpp, no FourCC
        manifest["sprites"][name] = {
            "window": window,
            "trim_box_within_window": box,
            "size": result.size,
            "frames": frames,
            "png": str(png.relative_to(ROOT)),
            "dds": str(dds.relative_to(ROOT)),
            "png_sha256": sha256(png),
            "dds_sha256": sha256(dds),
            "transparent_pixels": int((np.asarray(result.getchannel("A")) == 0).sum()),
        }

    # Native statists_vs_orangists -1..1 maps to frames 1..21. Each frame is a
    # transparent 280x50 canvas with the unchanged 16x24 production pointer.
    pointer_source = OUT / "pointer.png"
    pointer = Image.open(pointer_source).convert("RGBA")
    track = Image.new("RGBA", (280 * 21, 50))
    positions = []
    for index in range(21):
        center_x = 40 + index * 10
        left = center_x - pointer.width // 2
        track.alpha_composite(pointer, (index * 280 + left, 13))
        positions.append({"frame": index + 1, "native_value": round(-1 + index / 10, 1),
                          "center_x": center_x, "pointer_top_left": [left, 13]})
        frame = track.crop((index * 280, 0, (index + 1) * 280, 50))
        expected = Image.new("RGBA", (280, 50))
        expected.alpha_composite(pointer, (left, 13))
        assert frame.tobytes() == expected.tobytes(), index
    track_png = OUT / "pointer_track.png"
    track_dds = DDS / "pointer_track.dds"
    track.save(track_png)
    track.save(track_dds)
    track_roundtrip = Image.open(track_dds).convert("RGBA")
    assert track_roundtrip.size == (5880, 50)
    assert track_roundtrip.tobytes() == track.tobytes()
    assert track.getchannel("A").getextrema() == (0, 255)
    track_header = struct.unpack("<31I", track_dds.read_bytes()[4:128])
    assert track_header[21] == 32 and track_header[20] == 0
    manifest["sprites"]["pointer_track"] = {
        "source_png": str(pointer_source.relative_to(ROOT)),
        "source_png_sha256": sha256(pointer_source),
        "size": track.size, "frame_size": [280, 50], "frames": 21,
        "png": str(track_png.relative_to(ROOT)),
        "dds": str(track_dds.relative_to(ROOT)),
        "png_sha256": sha256(track_png), "dds_sha256": sha256(track_dds),
        "transparent_pixels": int((np.asarray(track.getchannel("A")) == 0).sum()),
        "frame_positions": positions,
    }
    sheet.save(ART / "chaozhou_government_art_v02.png")
    # Actual runtime dimensions; no labels or decorative material are added.
    previews = []
    for position, label in ((55, "gentry"), (132, "balanced"), (209, "ruler")):
        preview = singles["frame"].copy()
        preview.alpha_composite(singles["gentry"], (0, 9))
        preview.alpha_composite(singles["ruler"], (248, 9))
        preview.alpha_composite(singles["pointer"], (position, 13))
        preview.save(ART / f"chaozhou_government_v02_280x50_{label}.png")
        previews.append(preview)
    previews[1].resize((1120, 200), Image.Resampling.NEAREST).save(
        ART / "chaozhou_government_v02_preview_4x.png")
    manifest["recommended_ui_placement_within_280x50"] = {
        "frame": [0, 0], "gentry": [0, 9], "ruler": [248, 9],
        "pointer_centered": [132, 13],
    }
    (OUT.parent / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({k: v["size"] for k, v in manifest["sprites"].items()}))


if __name__ == "__main__":
    main()

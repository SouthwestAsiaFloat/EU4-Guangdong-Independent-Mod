#!/usr/bin/env python3
"""Generate the final 1180x900 Empire-of-China UI layers.

The approved layout keeps the left member/decree column fixed, shifts the
central authority/feudatory column 80 pixels right, and shifts the reform
column 160 pixels right.  Both inserted bands use an unobtrusive existing
wine-red texture below the title bar; the title bar itself is interpolated at
the cut so its jade and gold trim remains continuous.
"""

from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path

from PIL import Image

import generate_gdd_eoc_reform_groups as reform_groups
import generate_gdd_eoc_wide_background as authority_background


ROOT = Path(__file__).resolve().parents[1]
GFX = ROOT / "guangdong_independent_practice/gfx/interface"
BACKGROUND_OUTPUT = GFX / "gdd_eoc_bg_authority_wide_v2.tga"
OVERLAY_OUTPUT = GFX / "gdd_eoc_reform_groups_wide.tga"

SOURCE_SIZE = (1020, 900)
OUTPUT_SIZE = (1180, 900)
INSERT_WIDTH = 80
TITLE_HEIGHT = 100
FIRST_CUT = 260
SECOND_CUT = 730
TITLE_FIRST_CUT = 280
TITLE_SECOND_CUT = 730
TITLE_BRIDGE_SAMPLE_WIDTH = 24
TEXTURE_SAMPLE = (750, TITLE_HEIGHT, 830, 900)


def widen(source: Image.Image, *, textured_insert: bool) -> Image.Image:
    source = source.convert("RGBA")
    if source.size != SOURCE_SIZE:
        raise SystemExit(f"unexpected intermediate size: {source.size}")

    output = Image.new("RGBA", OUTPUT_SIZE, (0, 0, 0, 0))

    def paste_segments(top: int, bottom: int, first: int, second: int) -> None:
        output.paste(source.crop((0, top, first, bottom)), (0, top))
        output.paste(
            source.crop((first, top, second, bottom)),
            (first + INSERT_WIDTH, top),
        )
        output.paste(
            source.crop((second, top, SOURCE_SIZE[0], bottom)),
            (second + 2 * INSERT_WIDTH, top),
        )

    if not textured_insert:
        paste_segments(0, 900, FIRST_CUT, SECOND_CUT)
        return output

    # Below the title bar, preserve the two approved column cuts exactly.
    paste_segments(TITLE_HEIGHT, 900, FIRST_CUT, SECOND_CUT)
    for destination_x in (FIRST_CUT, SECOND_CUT + INSERT_WIDTH):
        output.paste(source.crop(TEXTURE_SAMPLE), (destination_x, TITLE_HEIGHT))

    # The old two-pixel interpolation cut through the left jade decree ribbon
    # and magnified it into a corrupt 80-pixel smear. Use ornament-free title
    # cuts and a real 24-pixel sample for each bridge instead.
    paste_segments(0, TITLE_HEIGHT, TITLE_FIRST_CUT, TITLE_SECOND_CUT)
    half_sample = TITLE_BRIDGE_SAMPLE_WIDTH // 2
    for cut, destination_x in (
        (TITLE_FIRST_CUT, TITLE_FIRST_CUT),
        (TITLE_SECOND_CUT, TITLE_SECOND_CUT + INSERT_WIDTH),
    ):
        title_bridge = source.crop(
            (cut - half_sample, 0, cut + half_sample, TITLE_HEIGHT)
        ).resize((INSERT_WIDTH, TITLE_HEIGHT), Image.Resampling.BILINEAR)
        output.paste(title_bridge, (destination_x, 0))

    return output


def encode_tga(image: Image.Image) -> bytes:
    buffer = BytesIO()
    # Keep this uncompressed: EU4's interface loader handles the resulting
    # 32-bit RGBA TGA consistently and the output is byte-for-byte stable.
    image.save(buffer, format="TGA")
    return buffer.getvalue()


def render_background() -> bytes:
    intermediate = Image.open(BytesIO(authority_background.render()))
    return encode_tga(widen(intermediate, textured_insert=True))


def render_overlay() -> bytes:
    intermediate = Image.open(BytesIO(reform_groups.render()))
    return encode_tga(widen(intermediate, textured_insert=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when either checked-in final UI layer is stale",
    )
    args = parser.parse_args()

    outputs = {
        BACKGROUND_OUTPUT: render_background(),
        OVERLAY_OUTPUT: render_overlay(),
    }
    if args.check:
        stale = [path for path, data in outputs.items() if not path.exists() or path.read_bytes() != data]
        if stale:
            raise SystemExit("outdated generated asset: " + ", ".join(map(str, stale)))
        for path in outputs:
            print(f"ok: {path}")
        return

    for path, data in outputs.items():
        path.write_bytes(data)
        print(path)


if __name__ == "__main__":
    main()

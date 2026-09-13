# Zhou province bronze seal v1

User approved the bronze seal concept and requested implementation on 2026-09-12.
Generated using the built-in ImageGen tool from the approved concept.

Source: `states.png`, a 3 by 3 atlas. Rows: registered, admission, removal.
Columns: normal, pressed, hover. The packager reorders these to EU4 normal,
hover, pressed, disabled; disabled reuses the dark pressed artwork.

Build: `python3 tools/package_zhou_province_seal.py` (Pillow required).
Check: add `--check`. Runtime remains 4 frames of 54x42; the seal is square 42x42.
The old emblem generator delegates province assets to this packager.
No gameplay actions, tooltips, or visibility conditions changed for this artwork.

ImageGen prompt: Preserve the approved bronze small-seal Zhou glyph and thin
bronze frame. Exact uniform 3x3 atlas, identical square seals, fully opaque dark
teal backgrounds, no labels. Columns normal / pressed darker / hover brighter.
Rows plain registered / small emerald green plus at bottom right / small
vermilion minus at bottom right. Badges must not obscure the central glyph.
No perspective or extra text. Split atlas on precise thirds.

Validation: asset reproducibility, territory validator, EoC layout validator,
and 9 province panel tests passed. Game AX inspection timed out, so runtime
rendering and hover verification remain outstanding. No crash fix is claimed.

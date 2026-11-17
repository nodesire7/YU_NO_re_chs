#!/usr/bin/env python3
"""Use the dialogue font for all text, retaining only game-specific private glyphs.

The MAGES font atlas uses 48x48 cells, 64 columns per row. The first 10 rows (640 cells)
keep their original character indices, not their original artwork. Punctuation,
Latin letters, numbers, kana and mathematical symbols all use the generated font.
Private-use cells are game-specific glyphs that the text font cannot supply.
Generated text in the first 640 cells fits the original horizontal slots because
the engine crops these proportional characters using fixed source metrics.

Usage: python make_font.py --generated FONT_A.png --original font.png --charset charset.utf8 --outdir DIR
"""
import argparse
import os
from pathlib import Path
import sys
import unicodedata

from PIL import Image

CELL = 48
COLS = 64
FIXED_METRIC_CELLS = 640


def fit_fixed_cell(glyph, original):
    """Fit generated ink to the original horizontal slot; keep its new baseline/height.

    YU-NO clips proportional symbols to fixed widths. A CJK opening bracket's
    right-side bearing cannot be copied directly into that narrow texture slot.
    """
    bounds = glyph.getchannel("A").getbbox()
    old_bounds = original.getchannel("A").getbbox()
    if bounds is None or old_bounds is None:
        return glyph
    left, top, right, bottom = bounds
    target_left = old_bounds[0]
    width = min(right - left, old_bounds[2] - target_left)
    ink = glyph.crop(bounds)
    if ink.width != width:
        ink = ink.resize((width, ink.height), Image.Resampling.LANCZOS)
    result = Image.new("RGBA", glyph.size)
    result.paste(ink, (target_left, top))
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generated", required=True)
    ap.add_argument("--original", required=True)
    ap.add_argument("--charset", type=Path, default=Path(__file__).resolve().parent.parent / "work/charset_new.utf8")
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()

    gen = Image.open(args.generated).convert("RGBA")
    orig = Image.open(args.original).convert("RGBA")
    if gen.width != COLS * CELL or orig.width != gen.width:
        ap.error(f"unexpected font atlas sizes: generated {gen.size}, original {orig.size}")
    charset = args.charset.read_text(encoding="utf-8")
    if gen.height < ((len(charset) + COLS - 1) // COLS) * CELL:
        ap.error("generated atlas does not contain the entire charset")
    out = gen.copy()
    private_cells = 0
    for index, character in enumerate(charset):
        x = index % COLS * CELL
        y = index // COLS * CELL
        if unicodedata.category(character) == "Co":
            if y + CELL > orig.height:
                ap.error(f"private glyph U+{ord(character):04X} has no original cell")
            out.paste(orig.crop((x, y, x + CELL, y + CELL)), (x, y))
            private_cells += 1
            continue
        glyph = gen.crop((x, y, x + CELL, y + CELL))
        if (not character.isspace() and not unicodedata.category(character).startswith("C")
                and glyph.getchannel("A").getbbox() is None):
            ap.error(f"generated character U+{ord(character):04X} has no ink at cell {index}")
        if index < FIXED_METRIC_CELLS and not character.isspace():
            glyph = fit_fixed_cell(glyph, orig.crop((x, y, x + CELL, y + CELL)))
            out.paste(glyph, (x, y))
    os.makedirs(args.outdir, exist_ok=True)
    for name in ("font.png", "font2.png"):
        out.save(os.path.join(args.outdir, name))
    print(f"wrote font.png/font2.png {out.width}x{out.height}: "
          f"{len(charset) - private_cells} dialogue-font cells, {private_cells} original private cells -> {args.outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

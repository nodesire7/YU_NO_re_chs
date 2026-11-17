#!/usr/bin/env python3
"""Use the dialogue font for all text, retaining only game-specific private glyphs.

The MAGES font atlas uses 48x48 cells, 64 columns per row. The first 10 rows (640 cells)
keep their original character indices, not their original artwork. Punctuation,
Latin letters, numbers, kana and mathematical symbols all use the generated font.
Private-use cells are game-specific glyphs that the text font cannot supply.

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
    os.makedirs(args.outdir, exist_ok=True)
    for name in ("font.png", "font2.png"):
        out.save(os.path.join(args.outdir, name))
    print(f"wrote font.png/font2.png {out.width}x{out.height}: "
          f"{len(charset) - private_cells} dialogue-font cells, {private_cells} original private cells -> {args.outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

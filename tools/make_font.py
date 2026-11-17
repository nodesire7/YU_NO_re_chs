#!/usr/bin/env python3
"""Merge the generated Chinese font atlas with the original Japanese glyph rows.

The MAGES font atlas uses 48x48 cells, 64 columns per row. The first 10 rows (640 cells)
hold the original ASCII/symbol/kana glyphs. Use the generated dialogue-font glyphs for
both half-width and full-width decimal digits, keeping the other original glyphs there.

Usage: python make_font.py --generated FONT_A.png --original font.png --charset charset.utf8 --outdir DIR
"""
import argparse
import os
from pathlib import Path
import sys

from PIL import Image

CELL = 48
COLS = 64
KEEP_ROWS = 10
DIGITS = frozenset("0123456789０１２３４５６７８９")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generated", required=True)
    ap.add_argument("--original", required=True)
    ap.add_argument("--charset", type=Path, default=Path(__file__).resolve().parent.parent / "work/charset_new.utf8")
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()

    gen = Image.open(args.generated).convert("RGBA")
    orig = Image.open(args.original).convert("RGBA")
    cut = KEEP_ROWS * CELL
    if gen.width != COLS * CELL or orig.width != gen.width or min(orig.height, gen.height) < cut:
        ap.error(f"unexpected font atlas sizes: generated {gen.size}, original {orig.size}")
    charset = args.charset.read_text(encoding="utf-8")
    digit_cells = [(index, character) for index, character in enumerate(charset[:KEEP_ROWS * COLS])
                   if character in DIGITS]
    if len(digit_cells) != len(DIGITS) or {character for _, character in digit_cells} != DIGITS:
        ap.error("charset does not contain the 20 expected digit cells in the original rows")
    out = gen.copy()
    out.paste(orig.crop((0, 0, orig.width, cut)), (0, 0))
    for index, character in digit_cells:
        x = index % COLS * CELL
        y = index // COLS * CELL
        glyph = gen.crop((x, y, x + CELL, y + CELL))
        if glyph.getchannel("A").getbbox() is None:
            ap.error(f"generated digit {character} has no ink at cell {index}")
        out.paste(glyph, (x, y))
    os.makedirs(args.outdir, exist_ok=True)
    for name in ("font.png", "font2.png"):
        out.save(os.path.join(args.outdir, name))
    print(f"wrote font.png/font2.png {out.width}x{out.height} with {len(digit_cells)} dialogue-font digits -> {args.outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

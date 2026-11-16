#!/usr/bin/env python3
"""Merge the generated Chinese font atlas with the original Japanese glyph rows.

The MAGES font atlas uses 48x48 cells, 64 columns per row. The first 10 rows (640 cells)
hold the original ASCII/symbol/kana glyphs; we keep those from the shipped game font and
take everything after that from the freshly generated atlas.

Usage: python make_font.py --generated FONT_A.png --original font.png --outdir DIR
"""
import argparse
import os
import shutil
import sys

from PIL import Image

CELL = 48
COLS = 64
KEEP_ROWS = 10


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generated", required=True)
    ap.add_argument("--original", required=True)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()

    gen = Image.open(args.generated).convert("RGBA")
    orig = Image.open(args.original).convert("RGBA")
    if gen.width != orig.width:
        print("width mismatch: %d vs %d" % (gen.width, orig.width), file=sys.stderr)
        return 2
    cut = min(KEEP_ROWS * CELL, orig.height, gen.height)
    out = gen.copy()
    out.paste(orig.crop((0, 0, orig.width, cut)), (0, 0))
    os.makedirs(args.outdir, exist_ok=True)
    for name in ("font.png", "font2.png"):
        out.save(os.path.join(args.outdir, name))
    print("wrote font.png/font2.png %dx%d (kept %d original rows) -> %s"
          % (out.width, out.height, KEEP_ROWS, args.outdir))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Apply text replacements to UI spritesheets.

Input is a JSON spec (list of operations) and an output path. Each operation:
  {
    "rect": [x, y, w, h],          # area to clear
    "fill": "#2b2b2b" | null,      # fill colour; null = leave background untouched
    "text": "新游戏",
    "font": "C:/Windows/Fonts/NotoSerifSC-VF.ttf",
    "size": 56,
    "variation": "Bold",           # optional variable-font instance
    "color": "#f0f0f0",
    "align": "left|center|right",
    "valign": "center|top|bottom",
    "dx": 0, "dy": 0,              # pixel offsets after alignment
    "stroke_width": 0, "stroke_fill": "#000000"
  }

Usage:
  python ui_edit.py --image in.png --spec spec.json --out out.png
"""
import argparse
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

FONT_CACHE = {}


def load_font(path, size, variation=None):
    key = (path, size, variation)
    if key in FONT_CACHE:
        return FONT_CACHE[key]
    font = ImageFont.truetype(path, size)
    if variation:
        try:
            font.set_variation_by_name(variation)
        except Exception as exc:  # pragma: no cover - depends on font
            print("warning: variation %r failed: %s" % (variation, exc), file=sys.stderr)
    FONT_CACHE[key] = font
    return font


def anchor_for(align, valign):
    h = {"left": "l", "center": "m", "right": "r"}[align]
    v = {"top": "a", "center": "m", "bottom": "d"}[valign]
    return h + v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    im = Image.open(args.image).convert("RGBA")
    draw = ImageDraw.Draw(im)
    with open(args.spec, encoding="utf-8") as fh:
        spec = json.load(fh)

    for i, op in enumerate(spec):
        x, y, w, h = [int(v) for v in op["rect"]]
        if op.get("clear"):
            im.paste((0, 0, 0, 0), (x, y, x + w, y + h))
            draw = ImageDraw.Draw(im)
        if op.get("erase_text"):
            # remove only the bright glyph pixels, keeping button plates/background
            thr = int(op["erase_text"].get("threshold", 110)) if isinstance(op["erase_text"], dict) else 110
            px = im.load()
            for yy in range(y, y + h):
                for xx in range(x, x + w):
                    r, g, b, a = px[xx, yy]
                    if a and (r + g + b) / 3.0 > thr:
                        px[xx, yy] = (0, 0, 0, 0)
            draw = ImageDraw.Draw(im)
        if op.get("fill"):
            draw.rectangle([x, y, x + w - 1, y + h - 1], fill=op["fill"])
        text = op.get("text", "")
        if not text:
            continue
        font = load_font(op["font"], int(op.get("size", 48)), op.get("variation"))
        align = op.get("align", "center")
        valign = op.get("valign", "center")
        anchor = anchor_for(align, valign)
        if align == "left":
            px = x + int(op.get("dx", 0))
        elif align == "right":
            px = x + w + int(op.get("dx", 0))
        else:
            px = x + w // 2 + int(op.get("dx", 0))
        if valign == "top":
            py = y + int(op.get("dy", 0))
        elif valign == "bottom":
            py = y + h + int(op.get("dy", 0))
        else:
            py = y + h // 2 + int(op.get("dy", 0))
        draw.text((px, py), text, font=font, fill=op.get("color", "#ffffff"),
                  anchor=anchor, stroke_width=int(op.get("stroke_width", 0)),
                  stroke_fill=op.get("stroke_fill", "#000000"))

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    im.save(args.out)
    print("applied %d ops -> %s" % (len(spec), args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())

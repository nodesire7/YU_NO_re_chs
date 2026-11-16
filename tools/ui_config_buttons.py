#!/usr/bin/env python3
"""Detect the pill-shaped option buttons in the config sheet.

Pills are either blue gradient (selected) or near-black (unselected) rounded rectangles
with light text. We detect their fill regions, group them by row and dump a labelled
overlay so the texts can be read off and matched to Chinese replacements.

Usage: python ui_config_buttons.py [--sheet ...] [--out overlay.png] [--json pills.json]
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def detect(im, x0=2450, x1=3500, y0=900, y1=2166):
    a = np.array(im).astype(int)
    r, g, b, al = a[:, :, 0], a[:, :, 1], a[:, :, 2], a[:, :, 3]
    lum = (r + g + b) / 3.0
    blue = (al > 100) & (b - r > 30) & (b > 100)
    dark = (al > 150) & (lum < 40)
    mask = np.zeros_like(blue)
    mask[y0:y1, x0:x1] = (blue | dark)[y0:y1, x0:x1]
    mask = ndimage.binary_closing(mask, structure=np.ones((5, 9)))
    lab, n = ndimage.label(mask)
    boxes = []
    for sl in ndimage.find_objects(lab):
        if sl is None:
            continue
        h = sl[0].stop - sl[0].start
        w = sl[1].stop - sl[1].start
        if 90 <= w <= 260 and 28 <= h <= 70:
            boxes.append([sl[1].start, sl[0].start, w, h])
    # group into rows by vertical centre
    boxes.sort(key=lambda b: (b[1] + b[3] // 2, b[0]))
    rows = []
    for bx in boxes:
        cy = bx[1] + bx[3] / 2
        for row in rows:
            if abs(row["cy"] - cy) < 14:
                row["items"].append(bx)
                row["cy"] = (row["cy"] * (len(row["items"]) - 1) + cy) / len(row["items"])
                break
        else:
            rows.append({"cy": cy, "items": [bx]})
    for row in rows:
        row["items"].sort(key=lambda b: b[0])
    rows.sort(key=lambda r: r["cy"])
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", default=os.path.join(ROOT, "work", "extract", "system", "config.png"))
    ap.add_argument("--out", default=os.path.join(ROOT, "work", "ui", "config_pills.png"))
    ap.add_argument("--json", default=os.path.join(ROOT, "work", "ui", "config_pills.json"))
    args = ap.parse_args()

    im = Image.open(args.sheet).convert("RGBA")
    rows = detect(im)
    print("rows:", len(rows), [len(r["items"]) for r in rows])

    prev = im.crop((2500, 1100, 3350, 2010)).convert("RGB")
    d = ImageDraw.Draw(prev)
    out = []
    for ri, row in enumerate(rows):
        for ci, (x, y, w, h) in enumerate(row["items"]):
            d.rectangle([x - 2500, y - 1100, x + w - 2500, y + h - 1100], outline=(255, 0, 0), width=2)
            d.text((x - 2500 + 4, y - 1100 + 2), "%d-%d" % (ri, ci), fill=(255, 255, 0))
            out.append({"row": ri, "col": ci, "x": x, "y": y, "w": w, "h": h})
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    prev.save(args.out)
    with open(args.json, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Detect line-shaped text bands inside a UI region using projection profiles.

Unlike find_text.py this does not dilate across the whole image, so it is reliable for
regular menus on a dark strip. Output: JSON list of boxes (absolute coordinates) plus a
preview with the boxes drawn.

Usage:
  python detect_bands.py --image titlechip.png --region 0,1090,420,1830 --thr 95 \
      --out preview.png --json boxes.json
"""
import argparse
import json
import os

import numpy as np
from PIL import Image, ImageDraw


def bands(mask, min_pixels, max_gap):
    prof = mask.sum(axis=1)
    on = prof > min_pixels
    out = []
    start = None
    gap = 0
    for y, v in enumerate(on):
        if v:
            if start is None:
                start = y
            gap = 0
        else:
            if start is not None:
                gap += 1
                if gap > max_gap:
                    out.append((start, y - gap))
                    start = None
    if start is not None:
        out.append((start, len(on) - 1 - gap))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--region", required=True, help="x0,y0,x1,y1")
    ap.add_argument("--thr", type=int, default=95)
    ap.add_argument("--mode", choices=["light", "dark"], default="light")
    ap.add_argument("--min-pixels", type=int, default=3)
    ap.add_argument("--max-gap", type=int, default=8)
    ap.add_argument("--pad", type=int, default=6)
    ap.add_argument("--out", required=True)
    ap.add_argument("--json", required=True)
    args = ap.parse_args()

    x0, y0, x1, y1 = [int(v) for v in args.region.split(",")]
    im = Image.open(args.image).convert("RGBA").crop((x0, y0, x1, y1))
    arr = np.array(im).astype(np.int16)
    lum = arr[:, :, :3].mean(axis=2)
    alpha = arr[:, :, 3]
    mask = ((lum > args.thr) if args.mode == "light" else (lum < args.thr)) & (alpha > 40)
    bs = bands(mask, args.min_pixels, args.max_gap)

    boxes = []
    for (a, b) in bs:
        sub = mask[a:b + 1]
        cols = np.where(sub.sum(axis=0) > 0)[0]
        if not len(cols):
            continue
        bx0, bx1 = int(cols.min()), int(cols.max())
        pad = args.pad
        boxes.append({"x": x0 + max(0, bx0 - pad), "y": y0 + max(0, a - pad),
                      "w": min(x1 - x0, bx1 - bx0 + 1 + pad * 2),
                      "h": b - a + 1 + pad * 2})

    prev = Image.open(args.image).convert("RGB").crop((x0, y0, x1, y1))
    d = ImageDraw.Draw(prev)
    for i, bx in enumerate(boxes):
        rx, ry, rw, rh = bx["x"] - x0, bx["y"] - y0, bx["w"], bx["h"]
        d.rectangle([rx, ry, rx + rw, ry + rh], outline=(255, 0, 0), width=2)
        d.text((rx + 2, ry + 2), str(i), fill=(0, 255, 0))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    prev.save(args.out)
    with open(args.json, "w", encoding="utf-8") as fh:
        json.dump(boxes, fh, indent=1)
    print("%d bands -> %s" % (len(boxes), args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

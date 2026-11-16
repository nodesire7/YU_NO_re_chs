#!/usr/bin/env python3
"""Find text-like regions in a UI spritesheet and (optionally) produce a preview.

The MAGES UI sheets are flat images with text drawn in a single colour on a fairly
uniform background. We threshold, dilate to merge glyphs into words/lines, and report
bounding boxes. Results are meant to be reviewed by eye (preview PNG) and then fed to
`ui_edit.py` as replacement specs.

Usage:
  python find_text.py --image config.png --mode light --crop 0,0,2000,1200 \
      --out work/ui/config_boxes.png
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw


def boxes_from_mask(mask, min_area, merge_dx, merge_dy):
    try:
        import cv2
    except ImportError:
        cv2 = None
    if cv2 is not None:
        kernel = np.ones((3, 15), np.uint8)
        m = cv2.dilate(mask, kernel, iterations=2)
        n, labels, stats, _ = cv2.connectedComponentsWithStats(m, 8)
        boxes = []
        for i in range(1, n):
            x, y, w, h, area = stats[i]
            if area >= min_area:
                boxes.append([int(x), int(y), int(w), int(h)])
    else:
        # crude fallback: project profiles
        boxes = []
        cols = mask.sum(axis=0)
        rows = mask.sum(axis=1)
        xs = np.where(cols > 0)[0]
        ys = np.where(rows > 0)[0]
        if len(xs) and len(ys):
            boxes.append([int(xs.min()), int(ys.min()),
                          int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)])
    # merge boxes whose vertical ranges overlap and are horizontally close
    merged = True
    while merged:
        merged = False
        out = []
        used = [False] * len(boxes)
        for i, a in enumerate(boxes):
            if used[i]:
                continue
            ax, ay, aw, ah = a
            for j in range(i + 1, len(boxes)):
                if used[j]:
                    continue
                bx, by, bw, bh = boxes[j]
                overlap_y = min(ay + ah, by + bh) - max(ay, by)
                gap_x = max(ax, bx) - min(ax + aw, bx + bw)
                if overlap_y > 0.5 * min(ah, bh) and gap_x < merge_dx:
                    nx, ny = min(ax, bx), min(ay, by)
                    ax, ay = nx, ny
                    aw = max(ax + aw, bx + bw) - nx
                    ah = max(ay + ah, by + bh) - ny
                    used[j] = True
                    merged = True
            out.append([ax, ay, aw, ah])
        boxes = out
    # merge lines that are vertically close (same label split in two rows)
    boxes.sort(key=lambda b: (b[1] // merge_dy, b[0]))
    return boxes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--mode", choices=["light", "dark"], default="light")
    ap.add_argument("--crop", default=None, help="x0,y0,x1,y1")
    ap.add_argument("--threshold", type=int, default=None)
    ap.add_argument("--min-area", type=int, default=40)
    ap.add_argument("--merge-dx", type=int, default=25)
    ap.add_argument("--merge-dy", type=int, default=30)
    ap.add_argument("--out", required=True, help="preview png")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    im = Image.open(args.image).convert("RGBA")
    if args.crop:
        x0, y0, x1, y1 = [int(v) for v in args.crop.split(",")]
        im = im.crop((x0, y0, x1, y1))
    arr = np.array(im).astype(np.int16)
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3]
    lum = rgb.mean(axis=2)
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    if args.threshold is not None:
        thr = args.threshold
    else:
        thr = 160 if args.mode == "light" else 110
    if args.mode == "light":
        mask = ((lum > thr) & (sat < 80) & (alpha > 40)).astype(np.uint8)
    else:
        mask = ((lum < thr) & (alpha > 40)).astype(np.uint8)

    boxes = boxes_from_mask(mask, args.min_area, args.merge_dx, args.merge_dy)
    # filter noise: text boxes are wider than tall-ish and not tiny
    boxes = [b for b in boxes if b[2] > 8 and b[3] > 6]

    prev = im.convert("RGB").copy()
    d = ImageDraw.Draw(prev)
    for i, (x, y, w, h) in enumerate(boxes):
        d.rectangle([x, y, x + w, y + h], outline=(255, 0, 0), width=3)
        d.text((x + 3, max(0, y - 18)), "%d" % i, fill=(255, 255, 0))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    prev.save(args.out)

    offset = (0, 0)
    if args.crop:
        offset = (int(args.crop.split(",")[0]), int(args.crop.split(",")[1]))
    abs_boxes = [{"i": i, "x": b[0] + offset[0], "y": b[1] + offset[1], "w": b[2], "h": b[3]}
                 for i, b in enumerate(boxes)]
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(abs_boxes, fh, ensure_ascii=False, indent=1)
    print("found %d boxes -> %s" % (len(boxes), args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())

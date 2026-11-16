#!/usr/bin/env python3
"""Cluster the option-pill texts in the config sheet by their pixel shape.

The same Japanese option word (する / しない / 普通 …) is drawn identically in every pill,
so we can group pills by a normalised bitmap hash, identify each group once, and then
replace every member with the same Chinese string.

Usage:
  python ui_pill_clusters.py [--sheet ...] [--pills work/ui/config_pills.json] \
      [--out work/ui/pill_groups.png] [--json work/ui/pill_groups.json]
"""
import argparse
import hashlib
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def text_mask(crop, thr=200):
    a = np.array(crop).astype(int)
    lum = a[:, :, :3].mean(2)
    al = a[:, :, 3]
    return (lum > thr) & (al > 60)


def signature(mask):
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return None
    sub = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    im = Image.fromarray((sub * 255).astype(np.uint8)).resize((48, 16), Image.BILINEAR)
    arr = (np.array(im) > 110).astype(np.uint8)
    return arr, len(xs)


def hamming(a, b):
    return int((a != b).sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", default=os.path.join(ROOT, "work", "extract", "system", "config.png"))
    ap.add_argument("--pills", default=os.path.join(ROOT, "work", "ui", "config_pills.json"))
    ap.add_argument("--out", default=os.path.join(ROOT, "work", "ui", "pill_groups.png"))
    ap.add_argument("--json", default=os.path.join(ROOT, "work", "ui", "pill_groups.json"))
    args = ap.parse_args()

    im = Image.open(args.sheet).convert("RGBA")
    pills = json.load(open(args.pills, encoding="utf-8"))

    entries = []
    for p in pills:
        crop = im.crop((p["x"] + 10, p["y"] + 6, p["x"] + p["w"] - 10, p["y"] + p["h"] - 6))
        m = text_mask(crop)
        sig = signature(m)
        if sig is None:
            continue
        entries.append((p, sig[0], sig[1]))

    groups = []  # list of dicts {sig, members}
    for p, sig, area in entries:
        for g in groups:
            if hamming(g["sig"], sig) < 90:
                g["members"].append(p)
                break
        else:
            groups.append({"sig": sig, "members": [p]})
    groups.sort(key=lambda g: len(g["members"]), reverse=True)
    for i, g in enumerate(groups):
        for p in g["members"]:
            p["group"] = i
    print("pills:", len(entries), "groups:", len(groups), "sizes:", [len(g["members"]) for g in groups])

    # contact sheet: one representative per group
    reps = []
    for gi, g in enumerate(groups):
        p = g["members"][0]
        reps.append((gi, p))
    cw, ch = 240, 60
    sheet = Image.new("RGB", (cw * 3, ch * ((len(reps) + 2) // 3)), (30, 30, 30))
    d = ImageDraw.Draw(sheet)
    for idx, (gi, p) in enumerate(reps):
        crop = im.crop((p["x"], p["y"], p["x"] + p["w"], p["y"] + p["h"])).convert("RGBA")
        bg = Image.new("RGBA", crop.size, (30, 30, 30, 255))
        bg.alpha_composite(crop)
        sheet.paste(bg.convert("RGB"), ((idx % 3) * cw + 8, (idx // 3) * ch + 20))
        d.text(((idx % 3) * cw + 8, (idx // 3) * ch + 4), "g%d (%d)" % (gi, len(g["members"])),
               fill=(255, 255, 0))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    sheet.save(args.out)
    with open(args.json, "w", encoding="utf-8") as fh:
        json.dump(pills, fh, indent=1)
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Translate the in-game menu chip sheet (menuchip.png).

Layout: 3 columns (normal / selected / disabled) x 6 entries. Labels sit under icons on
a transparent background; the EXIT GAME entries have a button plate that must be kept.

Usage: python ui_menu.py [--sheet ...] [--out ...]
"""
import argparse
import json
import os
import subprocess
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "NotoSerifSC-VF.ttf")

# (x, y, w, h) of column 1 labels; columns are 220px apart
ROWS = [
    (335, 146, 128, 26, "历史记录"),
    (338, 328, 108, 26, "设置"),
    (342, 506, 108, 28, "帮助"),
    (342, 681, 108, 26, "存档"),
    (335, 852, 112, 46, "返回标题"),
    (335, 980, 112, 54, "退出游戏"),
]
COL_DX = [0, 224, 425]
COL_COLORS = ["#3b2c1a", "#8a4a0e", "#8d8579"]


def build_spec(sheet):
    im = Image.open(sheet).convert("RGBA")
    spec = []
    for ci, dx in enumerate(COL_DX):
        for (x, y, w, h, text) in ROWS:
            rect = [x + dx - 6, y - 6, w + 12, h + 12]
            op = {"rect": rect, "text": text, "font": FONT,
                  "size": 22 if len(text) <= 2 else 20, "variation": "Bold",
                  "color": COL_COLORS[ci], "align": "center", "valign": "center"}
            if text == "退出游戏":
                # the plate has text-shaped transparent holes; refill the interior
                op["fill"] = "#050505"
                op["rect"] = [352 + dx, 972, 90, 64]
                op["color"] = "#f0e8d2"
            else:
                op["clear"] = True
            spec.append(op)
    return spec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", default=os.path.join(ROOT, "work", "extract", "system", "menuchip.png"))
    ap.add_argument("--out", default=os.path.join(ROOT, "work", "ui_out", "menuchip.png"))
    ap.add_argument("--preview", default=os.path.join(ROOT, "work", "ui_out", "menuchip_preview.png"))
    args = ap.parse_args()

    spec_path = os.path.join(ROOT, "work", "ui", "menu_spec.json")
    spec = build_spec(args.sheet)
    with open(spec_path, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=1)
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "ui_edit.py"),
                    "--image", args.sheet, "--spec", spec_path, "--out", args.out], check=True)

    im = Image.open(args.out).convert("RGBA")
    bg = Image.new("RGBA", im.size, (238, 236, 230, 255))
    bg.alpha_composite(im)
    bg.convert("RGB").save(args.preview)
    print("menuchip ->", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

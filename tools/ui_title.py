#!/usr/bin/env python3
"""Build and apply the title-screen text replacement spec.

The title sheet (titlechip.png) holds the menu labels three times: normal (white),
selected (gold) and disabled (grey). Each label is a separate transparent sprite, so we
just clear the old glyphs and draw Chinese in the same place.

Usage: python ui_title.py [--sheet ...] [--out ...] [--preview ...]
"""
import argparse
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "NotoSerifSC-VF.ttf")

# rows detected in the sheet: (x, y, w, h) for the normal (white) column
ROWS = [
    (7, 1092, 173, 61),
    (7, 1164, 177, 61),
    (7, 1236, 177, 61),
    (7, 1308, 195, 61),
    (8, 1380, 121, 61),      # A.D.M.S. kept as-is
    (9, 1452, 296, 61),
    (8, 1524, 247, 61),
    (9, 1596, 120, 61),
    (7, 1668, 84, 61),
]
TEXTS = ["开始游戏", "读取存档", "复制存档", "删除存档", None,
         "图像鉴赏", "音乐鉴赏", "设置", "帮助"]
DEBUG = (440, 1738, 400, 64, "调试开始")

COL_OFFSETS = [0, 448, 896]
COL_COLORS = ["#f4f1e8", "#ffd200", "#8b8b8b"]
EXIT_BOXES = [(1062, 2570, 220, 56), (1508, 2570, 225, 56), (1918, 2570, 210, 56)]
EXIT_TEXTS = ["退出游戏", "退出游戏", "退出游戏"]


def build_spec():
    spec = []
    for ci, off in enumerate(COL_OFFSETS):
        for (x, y, w, h), text in zip(ROWS, TEXTS):
            if not text:
                continue
            spec.append({
                "rect": [x + off - 10, y - 3, 470, h + 6],
                "clear": True,
                "text": text,
                "font": FONT,
                "size": 54,
                "variation": "Bold",
                "color": COL_COLORS[ci],
                "align": "left",
                "valign": "center",
                "dx": 6,
            })
    # debug-only entry (gold column)
    x, y, w, h, text = DEBUG
    spec.append({"rect": [x - 10, y - 3, 470, h + 6], "clear": True, "text": text,
                 "font": FONT, "size": 50, "variation": "Bold",
                 "color": COL_COLORS[1], "align": "left", "valign": "center", "dx": 6})
    # the actual title-menu EXIT sprites (white / gold), near the sheet bottom
    for (x, y, w, h), color in (((1060, 2682, 190, 66), "#f4f1e8"),
                                ((1494, 2682, 190, 66), "#ffd200"),
                                ((1925, 2676, 190, 70), "#8b8b8b")):
        spec.append({"rect": [x, y, w, h], "clear": True, "text": "退出游戏",
                     "font": FONT, "size": 40, "variation": "Bold",
                     "color": color, "align": "center", "valign": "center"})
    for (x, y, w, h), text in zip(EXIT_BOXES, EXIT_TEXTS):
        spec.append({"rect": [x - 6, y - 3, w + 30, h + 6], "erase_text": {"threshold": 105}, "text": text,
                     "font": FONT, "size": 40, "variation": "Bold",
                     "color": "#e8e8e8", "align": "left", "valign": "center", "dx": 4})
    return spec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", default=os.path.join(ROOT, "work", "extract", "system", "titlechip.png"))
    ap.add_argument("--out", default=os.path.join(ROOT, "work", "ui_out", "titlechip.png"))
    ap.add_argument("--preview", default=os.path.join(ROOT, "work", "ui_out", "titlechip_preview.png"))
    args = ap.parse_args()

    spec_path = os.path.join(ROOT, "work", "ui", "title_spec.json")
    spec = build_spec()
    with open(spec_path, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=1)
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "ui_edit.py"),
                    "--image", args.sheet, "--spec", spec_path, "--out", args.out], check=True)

    # apply the GBT branding plate so the sheet is complete in one step
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "ui_brand.py"),
                    "--image", args.out, "--out", args.out], check=True)

    # preview: crop menu area composited over a dark background
    im = Image.open(args.out).convert("RGBA")
    bg = Image.new("RGBA", (1450, 800), (40, 38, 34, 255))
    bg.alpha_composite(im.crop((0, 1050, 1450, 1850)))
    bg.convert("RGB").save(args.preview)
    # bottom strip (exit labels)
    bg2 = Image.new("RGBA", (1200, 120), (40, 38, 34, 255))
    bg2.alpha_composite(im.crop((1000, 2540, 2200, 2660)))
    bg2.convert("RGB").save(args.preview.replace(".png", "_exit.png"))
    print("title sheet ->", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

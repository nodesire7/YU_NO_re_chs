#!/usr/bin/env python3
"""Translate the in-game menu chip sheet (menuchip.png).

Labels are centred on the measured centres of the original Japanese glyphs, so all three
states (normal / highlighted / disabled) line up exactly and do not ghost when the engine
draws the normal and highlighted sprites overlapping. The highlighted column also gets a
soft orange glow to match the original effect.

Usage: python ui_menu.py [--sheet ...] [--out ...]
"""
import argparse
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "NotoSerifSC-VF.ttf")

# (cx, cy, size) measured per state column for each entry
ROWS = [
    [(401, 157, 30), (614, 160, 30), (820, 165, 30), "历史记录"],
    [(395, 336, 30), (602, 340, 30), (815, 336, 30), "设置"],
    [(394, 510, 30), (608, 516, 30), (815, 510, 30), "帮助"],
    [(399, 685, 30), (610, 690, 30), (819, 685, 30), "存档"],
    [(401, 871, 28), (612, 871, 28), (821, 871, 28), "返回标题"],
]
EXIT = [(395, 1005, 26), (605, 1004, 26), (815, 1005, 26), "退出游戏"]
COL_COLORS = ["#3b2c1a", "#8a4a0e", "#8d8579"]
GLOW_COLOR = "#e08a2a"


def draw_with_glow(im, center, text, font, color, glow=None):
    if glow:
        mask = Image.new("L", im.size, 0)
        ImageDraw.Draw(mask).text(center, text, font=font, fill=255, anchor="mm")
        glow_layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
        glow_img = Image.new("RGBA", im.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow_img)
        gd.text(center, text, font=font, fill=glow, anchor="mm")
        glow_layer = Image.composite(glow_img, glow_layer, mask)
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(3))
        im.alpha_composite(glow_layer)
    ImageDraw.Draw(im).text(center, text, font=font, fill=color, anchor="mm")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", default=os.path.join(ROOT, "work", "extract", "system", "menuchip.png"))
    ap.add_argument("--out", default=os.path.join(ROOT, "work", "ui_out", "menuchip.png"))
    ap.add_argument("--preview", default=os.path.join(ROOT, "work", "ui_out", "menuchip_preview.png"))
    args = ap.parse_args()

    im = Image.open(args.sheet).convert("RGBA")

    for ci in range(3):
        color = COL_COLORS[ci]
        for row in ROWS:
            cx, cy, size = row[ci]
            text = row[3]
            box = [cx - 95, cy - size - 10, cx + 95, cy + size + 12]
            im.paste((0, 0, 0, 0), (box[0], box[1], box[2], box[3]))
            font = ImageFont.truetype(FONT, size)
            try:
                font.set_variation_by_name("Bold")
            except Exception:
                pass
            draw_with_glow(im, (cx, cy + 1), text, font, color,
                           GLOW_COLOR if ci == 1 else None)

    # EXIT GAME plates: keep the plate, refill the glyph band with its dark colour
    for ci in range(3):
        cx, cy, size = EXIT[ci]
        text = EXIT[3]
        px = im.load()
        for yy in range(cy - 22, cy + 22):
            for xx in range(cx - 78, cx + 72):
                r, g, b, a = px[xx, yy]
                if a > 100 and (r + g + b) / 3.0 > 95:
                    px[xx, yy] = (18, 18, 18, a)
        font = ImageFont.truetype(FONT, size)
        try:
            font.set_variation_by_name("Bold")
        except Exception:
            pass
        ImageDraw.Draw(im).text((cx, cy), text, font=font, fill=(240, 232, 210, 255), anchor="mm")

    im.save(args.out)
    bg = Image.new("RGBA", im.size, (238, 236, 230, 255))
    bg.alpha_composite(im)
    bg.convert("RGB").save(args.preview)
    print("menuchip ->", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

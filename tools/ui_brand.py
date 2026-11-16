#!/usr/bin/env python3
"""Add the GBT branding (logo plate + author line) to the title sheet.

The GBT logo is dark artwork, so it is placed on a translucent parchment plate that
matches the sheet's aged-paper look.

Usage: python ui_brand.py --image work/ui_out/titlechip.png --out work/ui_out/titlechip_branded.png
"""
import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "NotoSerifSC-VF.ttf")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--logo", default=r"F:\封包目录\GBT_Small_logo.png")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    im = Image.open(args.image).convert("RGBA")
    logo = Image.open(args.logo).convert("RGBA")

    plate_w, plate_h = 1010, 116
    px, py = 2410, 2712
    plate = Image.new("RGBA", (plate_w, plate_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(plate)
    d.rounded_rectangle([0, 0, plate_w - 1, plate_h - 1], radius=12,
                        fill=(226, 218, 198, 210), outline=(120, 106, 82, 220), width=3)

    lw = int(logo.width * 2.0)
    lh = int(logo.height * 2.0)
    logo = logo.resize((lw, lh), Image.LANCZOS)
    plate.alpha_composite(logo, (18, (plate_h - lh) // 2))

    font_big = ImageFont.truetype(FONT, 42)
    font_small = ImageFont.truetype(FONT, 30)
    for f in (font_big, font_small):
        try:
            f.set_variation_by_name("Bold")
        except Exception:
            pass
    tx = 18 + lw + 26
    d.text((tx, 30), "A-FEI- 汉化", font=font_big, fill=(40, 32, 22, 255), anchor="lm")
    d.text((tx, 78), "BBS.GBTGAME.ME", font=font_small, fill=(70, 52, 30, 255), anchor="lm")

    im.alpha_composite(plate, (px, py))
    im.save(args.out)
    print("branded ->", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

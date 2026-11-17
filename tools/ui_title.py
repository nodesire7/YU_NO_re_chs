#!/usr/bin/env python3
"""Localize the title sprites within their original states and atlas slots."""
import argparse
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image, ImageFilter

from ui_edit import glyph_mask, load_font, text_sprite
from ui_config import FONT

ROOT = Path(__file__).resolve().parent.parent
MENU_TEXT = (
    "开始游戏", "读取存档", "复制存档", "删除存档", None,
    "图像鉴赏", "音乐鉴赏", "设置", "帮助",
)
# Original RGB and median halo alpha at successive distances from the ink.
NEUTRAL = (255, 249, 207, 132, 58, 14, 4, 0)
GOLD = (255, 228, 176, 132, 86, 51, 35, 20, 10, 4, 0)
PRESS = (255, 167, 115, 88, 64, 42, 25, 14, 7, 2, 0)
STYLES = (
    ((255, 255, 255), (110, 103, 88), NEUTRAL),
    ((255, 255, 255), (255, 210, 0), GOLD),
    ((0, 0, 0), (110, 103, 88), NEUTRAL),
)


def replace(original, output, box, text, font, style, centered=False, height=None):
    pixels = np.asarray(original.crop(box))
    ink, glow, profile = style
    opaque = pixels[:, :, 3] >= 245
    rgb = pixels[:, :, :3]
    foreground = rgb.min(axis=2) > 245 if ink[0] else rgb.max(axis=2) < 10
    top, left = np.argwhere(opaque & foreground).min(axis=0)
    bottom, right = np.argwhere(opaque & foreground).max(axis=0) + 1
    mask = glyph_mask(text, font, right - left, height or bottom - top)
    if style in STYLES:
        # Match the weight of the original condensed serif ink before applying
        # its halo. The same mask is used in all three menu states.
        mask = Image.blend(mask, mask.filter(ImageFilter.MaxFilter(3)), 0.9)
    sprite = text_sprite(mask, ink, glow, profile)
    x = (left + right - sprite.width) // 2 if centered else left - (len(profile) - 1)
    y = (top + bottom - sprite.height) // 2
    layer = Image.new("RGBA", (box[2] - box[0], box[3] - box[1]))
    layer.alpha_composite(sprite, (x, y))
    output.paste(layer, box[:2])


def localize(original, font_path):
    output = original.copy()
    font = load_font(str(font_path), 80, "Black")
    for col, style in enumerate(STYLES):
        x = 432 * col
        for i, text in enumerate(MENU_TEXT):
            if text is not None:
                y = 1088 + 72 * i
                replace(original, output, (x, y, x + 412, y + 70), text, font, style)
        exit_x = 1049 + 432 * col
        replace(original, output, (exit_x, 2681, exit_x + 220, 2751), "退出游戏", font, style)
    replace(original, output, (432, 1736, 844, 1806), "调试开始", font, STYLES[1])
    replace(original, output, (1310, 1590, 1928, 1710), "按任意键开始", font,
            ((0, 0, 0), (227, 224, 177), PRESS), centered=True, height=61)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sheet", type=Path, default=ROOT / "work/extract/system/titlechip.png")
    parser.add_argument("--out", type=Path, default=ROOT / "work/ui_out/titlechip.png")
    parser.add_argument("--preview", type=Path)
    parser.add_argument("--font", type=Path, default=FONT)
    parser.add_argument("--logo", type=Path)
    args = parser.parse_args()

    with Image.open(args.sheet) as sheet:
        output = localize(sheet.convert("RGBA"), args.font)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    output.save(args.out)
    bundled_logo = ROOT / "dist/GBT_logo.png"
    logo = args.logo if args.logo is not None else bundled_logo if bundled_logo.is_file() else None
    if logo is not None:
        subprocess.run([sys.executable, str(ROOT / "tools/ui_brand.py"), "--image", str(args.out),
                        "--out", str(args.out), "--logo", str(logo)], check=True)
    if args.preview is not None:
        box = (0, 1088, 1300, 1807)
        preview = Image.new("RGBA", (box[2], box[3] - box[1]), (65, 55, 49, 255))
        preview.alpha_composite(output.crop(box))
        preview.convert("RGB").save(args.preview)


if __name__ == "__main__":
    main()

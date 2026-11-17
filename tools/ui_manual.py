#!/usr/bin/env python3
"""Translate the two Steam manual pages while preserving their printed artwork."""
import argparse
import os
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation, convolve, distance_transform_edt, gaussian_filter, label

from ui_edit import glyph_mask, load_font

FONTS = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"

# Bounds on a 1450 px reference view, in original line order. Right-anchored
# labels end at a leader line, so their Chinese text keeps that alignment.
KEYBOARD = (
    ((987, 44, 1217, 74), "帮助 · 键盘与鼠标", "center"),
    ((331, 127, 447, 151), "跳过模式", "right"),
    ((296, 150, 403, 174), "自动模式", "right"),
    ((269, 173, 357, 196), "历史记录", "right"),
    ((225, 196, 308, 219), "操作说明", "right"),
    ((150, 218, 257, 242), "退出游戏", "right"),
    ((518, 148, 638, 174), "道具模式", "right"),
    ((500, 174, 591, 195), "宝玉存档", "right"),
    ((501, 197, 592, 219), "读取宝玉存档", "right"),
    ((484, 220, 539, 242), "存档", "center"),
    ((715, 149, 805, 175), "设置", "left"),
    ((762, 174, 879, 196), "返回标题", "left"),
    ((804, 196, 950, 219), "切换全屏", "left"),
    ((899, 219, 985, 242), "历史记录", "center"),
    ((999, 199, 1114, 221), "取消／", "left"),
    ((999, 221, 1137, 244), "隐藏窗口", "left"),
    ((1066, 269, 1242, 292), "确定／推进对话", "left"),
    ((1251, 367, 1337, 391), "历史记录", "left"),
    ((1251, 391, 1350, 415), "／缩放", "left"),
    ((1157, 507, 1249, 530), "取消", "left"),
    ((1157, 530, 1308, 551), "／系统菜单", "left"),
    ((74, 410, 234, 435), "强制跳过（按住）", "right"),
    ((102, 435, 231, 457), "／向左翻页", "right"),
    ((106, 618, 266, 643), "强制跳过（按住）", "right"),
    ((248, 646, 361, 672), "跳过模式", "right"),
    ((420, 619, 526, 642), "自动模式", "center"),
    ((536, 619, 670, 642), "系统菜单", "center"),
    ((716, 618, 891, 642), "确定／推进对话", "center"),
    ((912, 618, 993, 642), "选择项目", "center"),
    ((631, 669, 757, 692), "切换操作模式", "center"),
    ((530, 692, 855, 712), "（选择行动 → 道具 → 宝玉 → 选择行动，循环）", "center"),
    ((636, 713, 746, 734), "／向右翻页", "center"),
)

CONTROLLER = (
    ((1068, 44, 1219, 74), "帮助 · 手柄", "center"),
    ((489, 167, 707, 198), "方向键／摇杆", "left"),
)
CONTROLLER_ROWS = (
    "选择项目", "确定／推进对话", "取消／隐藏窗口", None, "历史记录",
    "强制跳过／向左翻页", "切换操作模式／向右翻页", "跳过模式", "自动模式",
    "宝玉存档", "系统菜单", "设置",
)
# The manual is a 1920x1080 Steam asset, not the legacy help.png.
MANUAL_SIZE = (1920, 1080)
REFERENCE_WIDTH = 1450
TABLE_TOPS = (166, 208, 250, 292, 334, 377, 418, 461, 503, 545, 588, 630)


def replace_ink(image, region, translation, anchor, font):
    box = tuple(round(value * MANUAL_SIZE[0] / REFERENCE_WIDTH) for value in region)
    tile = image.crop(box)
    pixels = np.array(tile)
    rgb = pixels[:, :, :3]
    white = (rgb.min(axis=2) >= 161) & ((rgb.max(axis=2) - rgb.min(axis=2)) <= 34)
    components, count = label(white)
    sizes = np.bincount(components.ravel(), minlength=count + 1)
    sizes[0] = 0
    ink = sizes[components] >= 3
    ys, xs = np.where(ink)
    if not xs.size:
        raise ValueError(f"No source lettering for {translation} in {region}")

    # Patch the letter strokes and their antialiasing, leaving the gold lines,
    # surrounding grain, guides, and control art in the source pixels.
    repair = binary_dilation(ink, iterations=2)
    yy, xx = distance_transform_edt(repair, return_distances=False, return_indices=True)
    smooth = rgb.astype(float)
    smooth[repair] = smooth[yy[repair], xx[repair]]
    kernel = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], dtype=float) / 4
    for _ in range(24):
        for channel in range(3):
            plane = smooth[:, :, channel]
            plane[repair] = convolve(plane, kernel, mode="nearest")[repair]
    # Use nearby paper grain after estimating the low-frequency color. This
    # avoids polished patches on the original distressed texture.
    residual = smooth - gaussian_filter(smooth, (0.85, 0.85, 0))
    grain = np.roll(residual, (5, 7), axis=(0, 1))
    donor_is_clean = ~np.roll(repair, (5, 7), axis=(0, 1))
    grain[~donor_is_clean] = 0
    restored = np.clip(smooth[repair] + np.clip(grain[repair], -22, 22), 0, 255)
    rgb[repair] = np.rint(restored)
    tile = Image.fromarray(pixels)

    left, right = xs.min(), xs.max() + 1
    top, bottom = ys.min(), ys.max() + 1
    mask = glyph_mask(translation, font, tile.width - 5, bottom - top)
    if anchor == "left":
        x = min(left, tile.width - mask.width - 1)
    elif anchor == "right":
        x = max(0, right - mask.width)
    else:
        x = max(0, min((left + right - mask.width) // 2, tile.width - mask.width))
    y = (top + bottom - mask.height) // 2
    text = Image.new("RGBA", mask.size, (255, 255, 255))
    text.putalpha(mask)
    tile.alpha_composite(text, (x, y))
    image.paste(tile, box[:2])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    body = load_font(str(FONTS / "NotoSansSC-VF.ttf"), 64, "Bold")
    heading = load_font(str(FONTS / "NotoSerifSC-VF.ttf"), 64, "Medium")
    controller_rows = [
        ((148, top, 463, top + 31), text, "left")
        for top, text in zip(TABLE_TOPS, CONTROLLER_ROWS, strict=True) if text
    ]
    args.out.mkdir(parents=True, exist_ok=True)
    for name, captions in (("001.png", KEYBOARD), ("002.png", CONTROLLER + tuple(controller_rows))):
        with Image.open(args.source / name) as original:
            page = original.convert("RGBA")
        if page.size != MANUAL_SIZE:
            raise ValueError(f"Unexpected size for {name}: {page.size}")
        for i, (region, translation, anchor) in enumerate(captions):
            replace_ink(page, region, translation, anchor, heading if i == 0 else body)
        page.save(args.out / name)
        print(f"{name}: localized {len(captions)} labels")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Localize the settings atlas while preserving the original sprite geometry."""
import argparse
from pathlib import Path
import os

import numpy as np
from PIL import Image, ImageFilter

from ui_edit import glyph_mask, load_font

ROOT = Path(__file__).resolve().parent.parent
FONT = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "NotoSerifSC-VF.ttf"
ATLAS_SIZE = (4096, 2166)

# The three rows share a strip with art and unrelated sprites. Limit each
# heading to its own slot on either side of the decorative line.
HEADINGS = (
    ((1922, 1086, 2098, 1122), "信息", (2512, 1086, 2675, 1122), "文本设置"),
    ((1922, 1122, 2063, 1158), "声音", (2476, 1122, 2632, 1158), "声音设置"),
    ((1922, 1158, 2062, 1194), "其他", (2479, 1158, 2632, 1194), "其他设置"),
)
LABELS = (
    "文本显示速度", "自动模式推进速度", "保持自动模式",
    "跳过模式的对象", "保持跳过模式", "语音与文本同步",
    "BGM 设置", "跳过语音", None, "音效", "系统音效", "角色语音",
    "提示功能", "面板答案显示", "手柄按键标识", "全屏切换", "画质",
)
NAMES = (
    "有马 拓也", "有马 亚由美", "一条 美月", "武田 绘里子", "结城 正胜", "岛津 澪",
    "波多乃 神奈", "朝仓 香织", "龙藏寺 幸三", "丰富 秀夫", "优诺", "阿曼达",
    "塞蕾丝", "其他（男性）", "其他（女性）", "北条 笃",
)
# None means the original glyph is already used in Simplified Chinese.
PILL_GROUPS = (
    (1129, (2688, 2832, 2976, 3120), (115, 116), ("即时", "快", None, "慢")),
    (1261, (2687, 2903, 3119, 3335), (188, 189), ("开启", "关闭", "仅已读", "全部")),
    (1393, (2687, 2903, 3119, 3335), (188, 189), ("重制版", "原版", "有", "无")),
    (1657, (2687, 2903), (188, 189), ("全屏", "窗口")),
)
BLANK_ROW = (1921, 1987)
WHITE = (255, 255, 255)
SHADOW = (16, 14, 14)
SELECTED_SHADOW = (35, 63, 85)


def composite_glyph(sprite, mask, x, y, shadow_color):
    if shadow_color is not None:
        shadow = Image.new("L", sprite.size)
        shadow.paste(mask, (x + 1, y + 2))
        shade = Image.new("RGBA", sprite.size, shadow_color)
        shade.putalpha(shadow.filter(ImageFilter.GaussianBlur(1.35)))
        sprite.alpha_composite(shade)
    glyph = Image.new("RGBA", mask.size, WHITE)
    glyph.putalpha(mask)
    sprite.alpha_composite(glyph, (x, y))


def replace_label(original, output, slot, text, font, shadow_color=SHADOW):
    src = original.crop(slot)
    alpha = src.getchannel("A")
    bounds = alpha.getbbox()
    core = alpha.point(lambda value: 255 if value > 170 else 0).getbbox()
    if bounds is None or core is None:
        raise ValueError(f"Missing original label in {slot}")
    output.paste((0, 0, 0, 0), (slot[0] + bounds[0], slot[1] + bounds[1],
                                   slot[0] + bounds[2], slot[1] + bounds[3]))
    mask = glyph_mask(text, font, src.width - core[0] - 4, core[3] - core[1])
    sprite = output.crop(slot)
    y = (core[1] + core[3] - mask.height) // 2
    composite_glyph(sprite, mask, core[0], y, shadow_color)
    output.paste(sprite, slot[:2])


def replace_pill(original, output, x, y, width, height, text, font, selected):
    # The button border lives outside this band. The center of a blank
    # button supplies each row's exact fill, including the selected gradient.
    margin = 10 if width > 120 else 18
    top, bottom = y + 4, y + height - 3
    band = (x + margin, top, x + width - margin, bottom)
    pixels = np.array(original.crop(band))
    blank_y = BLANK_ROW[selected]
    if width > 120:
        fill = np.asarray(original.crop((2687 + margin, blank_y + 4,
                                         2687 + width - margin, blank_y + height - 3)))
    else:
        profile = np.asarray(original.crop((2780, blank_y + 4, 2781, blank_y + height - 3)))
        fill = np.broadcast_to(profile, pixels.shape)

    foreground = pixels[:, :, 0].astype(np.int16) - fill[:, :, 0] > 85
    rows = np.where(np.any(foreground, axis=1))[0]
    if not len(rows):
        raise ValueError(f"Missing original button text at {(x, y)}")
    # Frame pixels and feathered outer edges stay identical to the original.
    opaque = (pixels[:, :, 3] == 255) & (fill[:, :, 3] == 255)
    pixels[opaque] = fill[opaque]
    interior = Image.fromarray(pixels)
    glyph = glyph_mask(text, font, interior.width - 8, rows[-1] - rows[0] + 1)
    text_x = (interior.width - glyph.width) // 2
    text_y = (rows[0] + rows[-1] + 1 - glyph.height) // 2
    composite_glyph(interior, glyph, text_x, text_y, SELECTED_SHADOW if selected else None)
    interior.putalpha(Image.fromarray(pixels[:, :, 3]))
    output.paste(interior, band[:2])


def localize(original, font_path):
    if original.size != ATLAS_SIZE:
        raise ValueError(f"Expected settings atlas {ATLAS_SIZE}, got {original.size}")
    output = original.copy()
    font = load_font(str(font_path), 64, "Medium")
    for left, title, right, subtitle in HEADINGS:
        replace_label(original, output, left, title, font, shadow_color=None)
        replace_label(original, output, right, subtitle, font, shadow_color=None)
    for i, text in enumerate(LABELS):
        if text is not None:
            top = 1194 + 48 * i
            replace_label(original, output, (1921, top, 2424, top + 48), text, font)
    for i, text in enumerate(NAMES):
        top = 1194 + 48 * i
        replace_label(original, output, (2425, top, 2674, top + 48), text, font)

    for y, columns, widths, texts in PILL_GROUPS:
        for selected in (False, True):
            for x, text in zip(columns, texts, strict=True):
                if text is None:
                    continue
                width = widths[selected]
                height = 43 if selected and width > 120 else 42
                replace_pill(original, output, x, y + 66 * selected, width, height, text, font, selected)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sheet", type=Path, default=ROOT / "work/extract/system/config.png")
    parser.add_argument("--out", type=Path, default=ROOT / "work/ui_out/config.png")
    parser.add_argument("--preview", type=Path)
    parser.add_argument("--font", type=Path, default=FONT)
    args = parser.parse_args()

    with Image.open(args.sheet) as sheet:
        output = localize(sheet.convert("RGBA"), args.font)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    output.save(args.out)
    if args.preview is not None:
        box = (1921, 1085, 3540, 2032)
        preview = Image.new("RGBA", (box[2] - box[0], box[3] - box[1]), (50, 47, 45, 255))
        preview.alpha_composite(output.crop(box))
        preview.convert("RGB").save(args.preview)
    print(f"config -> {args.out}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Localise the button-hint sheet (system/guide.png) into Chinese.

The game samples each label from a fixed atlas rectangle. Keep the original slots,
plate, highlight and controller/key symbols; fit Chinese ink inside each slot.

Usage: python tools/ui_guide.py [--sheet ...] [--out ...] [--recon-dir ...]
"""
import argparse
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont
from ui_edit import glyph_mask

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WINDIR = os.environ.get("WINDIR", r"C:\Windows")
FONT = os.path.join(WINDIR, "Fonts", "NotoSerifSC-VF.ttf")

SHEET = os.path.join(ROOT, "work", "extract", "system", "guide.png")
OUT = os.path.join(ROOT, "work", "ui_out", "guide.png")
SPEC = os.path.join(ROOT, "work", "ui", "guide_spec.json")

# The sheet is 84 px per bar: a plate starts every 84 px at y=94, the white text band
# is y 108..142 inside the bar, the 3 px highlight sits at y 95..97.
BAR_STEP, BAR_FIRST = 84, 94

# (bar index, plate width, original text ink x0..x1, words)
BARS = [
    (0, 1122, 5, 1090, ["确定", "返回", "播放", "关闭播放", "恢复默认", "停止", "模式切换", "标签切换"]),
    (1, 940, 5, 909, ["切换页面", "下个CG", "隐藏指南", "放大缩小", "关闭", "面板"]),
    (2, 881, 4, 849, ["A.D.M.S.", "道具", "宝玉", "切换", "菜单", "HC显示", "选择", "删除"]),
]
# Japanese originals, kept for the report / spec readability
ORIGINALS = [
    ["決定", "戻る", "再生", "再生オフ", "デフォルトに戻す", "停止", "モード切替", "タブ切替"],
    ["ページ切替", "次のCG", "ガイド非表示", "拡大縮小", "閉じる", "パネル"],
    ["A.D.M.S.", "アイテム", "宝玉", "切替", "メニュー", "HC表示", "選択", "削除"],
]

TEXT_SIZE = 39
TEXT_VARIATION = "Medium"
_FONTS = {}


def font(size=TEXT_SIZE, variation=TEXT_VARIATION):
    key = (size, variation)
    if key not in _FONTS:
        f = ImageFont.truetype(FONT, size)
        if variation:
            try:
                f.set_variation_by_name(variation)
            except Exception as exc:  # pragma: no cover
                print("warning: variation %r failed: %s" % (variation, exc), file=sys.stderr)
        _FONTS[key] = f
    return _FONTS[key]



# Original Japanese label slots, measured on the source atlas (x0 inclusive, x1 exclusive).
SLOTS = [
    [(2, 80), (82, 157), (160, 237), (240, 449), (452, 723), (726, 797), (800, 961), (964, 1095)],
    [(2, 183), (186, 322), (325, 545), (548, 704), (707, 806), (809, 913)],
    [(2, 122), (125, 251), (254, 330), (333, 412), (415, 549), (552, 688), (691, 773), (776, 853)],
]


def build_sheet(source):
    image = Image.open(source).convert("RGBA")
    operations = []
    for (bar, plate_w, _, _, words), slots in zip(BARS, SLOTS, strict=True):
        top = BAR_FIRST + BAR_STEP * bar
        ImageDraw.Draw(image).rectangle((2, top + 5, plate_w - 3, top + 58), fill=(0, 0, 0, 255))
        for text, (left, right) in zip(words, slots, strict=True):
            mask = glyph_mask(text, font(), right - left - 4, 35)
            x = left + (right - left - mask.width) // 2
            y = top + 14
            image.paste((255, 255, 255, 255), (x, y, x + mask.width, y + mask.height), mask)
            operations.append(dict(text=text, rect=[x, y, mask.width, mask.height], slot=[left, right]))
    return image, operations


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", default=SHEET)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--spec", default=SPEC)
    ap.add_argument("--recon-dir", default=os.path.join(ROOT, "_recon"))
    args = ap.parse_args()

    image, spec = build_sheet(args.sheet)
    os.makedirs(os.path.dirname(args.spec), exist_ok=True)
    with open(args.spec, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=1)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    image.save(args.out)
    print("guide -> %s (%d fixed label slots)" % (args.out, len(spec)))

    recon(args.out, args.sheet, args.recon_dir)
    return 0


def recon(out_path, sheet_path, recon_dir):
    os.makedirs(recon_dir, exist_ok=True)
    new = Image.open(out_path).convert("RGBA")
    old = Image.open(sheet_path).convert("RGBA")
    # each text bar side by side with the original, on dark and light backdrops
    for name, bg in (("dark", (24, 24, 24)), ("light", (236, 236, 232))):
        box = (0, 84, 1130, 336)
        w, h = box[2] - box[0], box[3] - box[1]
        canvas = Image.new("RGBA", (w, h * 2 + 6), bg + (255,))
        for k, src in enumerate((old, new)):
            tile = Image.new("RGBA", (w, h), bg + (255,))
            tile.alpha_composite(src.crop(box))
            canvas.paste(tile, (0, k * (h + 6)))
        canvas.convert("RGB").save(os.path.join(recon_dir, "guide_check_%s.png" % name))
    # whole sheet on both backdrops
    for name, bg in (("dark", (24, 24, 24)), ("light", (236, 236, 232))):
        canvas = Image.new("RGBA", new.size, bg + (255,))
        canvas.alpha_composite(new)
        canvas.convert("RGB").save(os.path.join(recon_dir, "guide_check_full_%s.png" % name))
    print("recon crops ->", recon_dir)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Localise the button-hint sheet (system/guide.png) into Chinese.

guide.png is an atlas of dark hint bars: three bars carry Japanese labels, the other
four carry PS / Xbox / keyboard glyphs (kept as they are - they are hardware symbols).
Each bar is one complete image, so the labels of a bar stay on the same line, keep the
original total width and get evenly distributed spacing; the bar plate and its top
highlight are untouched (the text band itself is pure black, so it can simply be
refilled with black).

Usage: python tools/ui_guide.py [--sheet ...] [--out ...] [--recon-dir ...]
"""
import argparse
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

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
INK_DY = 0           # ink centre offset from the bar centre
_FONTS = {}
_MEASURE = ImageDraw.Draw(Image.new("RGBA", (8, 8)))


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


def ink_box(text, fnt):
    return _MEASURE.textbbox((0, 0), text, font=fnt, anchor="la")


def text_op(text, x, y_center, size, color="#ffffff"):
    fnt = font(size)
    b = ink_box(text, fnt)
    pen_x = x - b[0]
    pen_y = y_center - (b[1] + b[3]) / 2.0
    return {
        "rect": [int(round(pen_x)), int(round(pen_y)), int(b[2] - b[0]), int(b[3] - b[1])],
        "text": text,
        "font": FONT,
        "size": int(size),
        "variation": TEXT_VARIATION,
        "color": color,
        "align": "left",
        "valign": "top",
        "dx": 0,
        "dy": 0,
    }


def layout(words, x0, x1, size):
    """Evenly spread the words over [x0, x1] (ink edges)."""
    fnt = font(size)
    widths = [ink_box(w, fnt)[2] - ink_box(w, fnt)[0] for w in words]
    total = sum(widths)
    span = x1 - x0
    gap = (span - total) / float(len(words) - 1)
    if gap < 6:
        raise SystemExit("words do not fit in bar (gap %.1f)" % gap)
    pos = []
    cursor = float(x0)
    for w in widths:
        pos.append(cursor)
        cursor += w + gap
    return pos, gap


def build_spec():
    spec = []
    for (bar, plate_w, x0, x1, words) in BARS:
        top = BAR_FIRST + BAR_STEP * bar
        # clear the old label row: the band inside the plate is plain black
        spec.append({"rect": [2, top + 5, plate_w - 4, 54], "fill": "#000000"})
        y_center = top + 31.5 + INK_DY
        for (pos, word) in zip(layout(words, x0, x1, TEXT_SIZE)[0], words):
            spec.append(text_op(word, pos, y_center, TEXT_SIZE))
    return spec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", default=SHEET)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--spec", default=SPEC)
    ap.add_argument("--recon-dir", default=os.path.join(ROOT, "_recon"))
    args = ap.parse_args()

    spec = build_spec()
    os.makedirs(os.path.dirname(args.spec), exist_ok=True)
    with open(args.spec, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=1)
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "ui_edit.py"),
                    "--image", args.sheet, "--spec", args.spec, "--out", args.out], check=True)
    print("guide -> %s (%d ops)" % (args.out, len(spec)))

    for (bar, plate_w, x0, x1, words) in BARS:
        pos, gap = layout(words, x0, x1, TEXT_SIZE)
        print("  bar %d: %s" % (bar, "  ".join("%s@%d" % (w, round(p)) for w, p in zip(words, pos))))
        print("          gap %.1f px, line %.0f..%.0f (was %d..%d)"
              % (gap, pos[0], pos[-1] + 0, x0, x1))

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

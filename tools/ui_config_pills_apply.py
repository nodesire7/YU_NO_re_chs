#!/usr/bin/env python3
"""Replace the Japanese option texts inside the config pills with Chinese.

Text pixels are removed by horizontal interpolation from the surrounding pill fill, so the
button gloss/gradient stays intact, then the Chinese label is drawn on top.

Usage: python ui_config_pills_apply.py [--sheet work/ui_out/config.png] [--out ...]
"""
import argparse
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "NotoSerifSC-VF.ttf")

TEXTS = {
    0: "全部", 1: "快", 2: "普通", 3: "慢",
    4: "全部", 5: "快", 6: "普通", 7: "慢",
    8: "开启", 9: "关闭", 10: "仅已读", 11: "全部",
    12: "开启", 13: "关闭", 14: "仅已读", 15: "全部",
    16: "重制版", 17: "原版", 18: "有", 19: "无",
    20: "重制版", 21: "原版", 22: "有", 23: "无",
    24: "低", 25: "中", 26: "高",
    27: "低", 28: "中", 29: "高",
    30: "全屏", 31: "窗口",
    33: "全屏", 34: "窗口",
    36: "数字", 37: "○×",
    39: "数字", 40: "○×",
}


def inpaint_row(px, y, x0, x1, thr):
    """Replace bright text pixels in [x0,x1) by linear interpolation along the row."""
    bright = []
    for x in range(x0, x1):
        r, g, b, a = px[x, y]
        if a > 60 and (r + g + b) / 3.0 > thr:
            bright.append(x)
    if not bright:
        return 0
    # group consecutive runs
    runs = []
    start = prev = bright[0]
    for x in bright[1:]:
        if x == prev + 1:
            prev = x
            continue
        runs.append((start, prev))
        start = prev = x
    runs.append((start, prev))
    for (a0, a1) in runs:
        left = None
        for x in range(a0 - 1, x0 - 1, -1):
            if (px[x, y][3] > 60) and (sum(px[x, y][:3]) / 3.0 <= thr):
                left = px[x, y]
                break
        right = None
        for x in range(a1 + 1, x1):
            if (px[x, y][3] > 60) and (sum(px[x, y][:3]) / 3.0 <= thr):
                right = px[x, y]
                break
        if left is None and right is None:
            continue
        left = left or right
        right = right or left
        span = (a1 - a0 + 1)
        for i, x in enumerate(range(a0, a1 + 1)):
            t = (i + 1) / (span + 1)
            col = tuple(int(round(left[c] * (1 - t) + right[c] * t)) for c in range(4))
            px[x, y] = col
    return len(bright)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", default=os.path.join(ROOT, "work", "ui_out", "config.png"))
    ap.add_argument("--pills", default=os.path.join(ROOT, "work", "ui", "config_pills.json"))
    ap.add_argument("--out", default=os.path.join(ROOT, "work", "ui_out", "config.png"))
    ap.add_argument("--preview", default=os.path.join(ROOT, "work", "ui_out", "config_buttons_preview.png"))
    args = ap.parse_args()

    im = Image.open(args.sheet).convert("RGBA")
    pills = json.load(open(args.pills, encoding="utf-8"))
    px = im.load()
    draw = ImageDraw.Draw(im)
    n = 0
    for i, p in enumerate(pills):
        if i not in TEXTS:
            continue
        x, y, w, h = p["x"], p["y"], p["w"], p["h"]
        # wipe the glyph band using a per-row fill sampled from the clean pill edges
        last = None
        for yy in range(y + 5, y + h - 5):
            cand = []
            for xx in range(x + 17, x + 25):
                p = px[xx, yy]
                if p[3] > 120:
                    cand.append(p)
            if cand:
                cand.sort(key=lambda c: sum(c[:3]))
                cur = cand[len(cand) // 2]
                if last is None:
                    last = cur
                else:
                    last = tuple(int(round((last[i] * 2 + cur[i]) / 3)) for i in range(4))
            col = last or (20, 22, 28, 255)
            for xx in range(x + 9, x + w - 8):
                px[xx, yy] = col
        cn = TEXTS[i]
        size = 30 if len(cn) <= 2 else 26
        font = ImageFont.truetype(FONT, size)
        try:
            font.set_variation_by_name("Bold")
        except Exception:
            pass
        draw.text((x + w // 2, y + h // 2 + 1), cn, font=font, fill=(246, 246, 246, 255),
                  anchor="mm", stroke_width=1, stroke_fill=(18, 22, 38, 255))
        n += 1
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    im.save(args.out)
    prev = Image.new("RGBA", (900, 900), (30, 28, 26, 255))
    prev.alpha_composite(im.crop((2450, 1080, 3350, 1980)))
    prev.convert("RGB").save(args.preview)
    print("replaced %d pills -> %s" % (n, args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())

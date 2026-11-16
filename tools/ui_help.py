#!/usr/bin/env python3
"""Localise the HELP screen sheet (system/help.png) into Chinese.

Three text groups are rewritten:
  * the heading          "HELP / 操作説明"                -> 帮助 / 操作说明
  * 13 controller call-outs  方向ボタン / Lスティック ...   -> 方向键 / 左摇杆 ...
  * the 15 x 2 table     button name | what the button does

The table cells have flat backgrounds, so plain `fill` + `text` operations (handled by
tools/ui_edit.py) are enough.  The heading and the call-outs are printed on the grunge
paper, where a flat fill would leave a visible patch, so their pixels are replaced by a
feather-blended copy of a text-free patch of the same paper; that cleaned plate is
written to work/ui/help_prep.png and tools/ui_edit.py then stamps the text over it.
Controller artwork, button icons and the Nintendo Switch logo are left untouched.

Usage: python tools/ui_help.py [--sheet ...] [--out ...] [--spec ...] [--prep ...]
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WINDIR = os.environ.get("WINDIR", r"C:\Windows")
FONT_SANS = os.path.join(WINDIR, "Fonts", "NotoSansSC-VF.ttf")
FONT_SERIF = os.path.join(WINDIR, "Fonts", "NotoSerifSC-VF.ttf")
# The Japanese sheet prints the table and the call-outs in a gothic face, but every
# other UI sheet of this patch is drawn with Noto Serif SC (see tools/ui_menu.py,
# tools/ui_config.py), so the same family is used here too.  Point this at FONT_SANS
# to get the gothic look of the original instead.
BODY_FONT = FONT_SERIF
BODY_LEFT_VAR, BODY_LEFT_SIZE = "Bold", 23
BODY_RIGHT_VAR, BODY_RIGHT_SIZE = "SemiBold", 23
CALLOUT_VAR, CALLOUT_SIZE = "Bold", 27

SHEET = os.path.join(ROOT, "work", "extract", "system", "help.png")
OUT = os.path.join(ROOT, "work", "ui_out", "help.png")
SPEC = os.path.join(ROOT, "work", "ui", "help_spec.json")
PREP = os.path.join(ROOT, "work", "ui", "help_prep.png")

# --- table geometry (measured on the original sheet) -------------------------------
TABLE_L, TABLE_R = 999, 1797          # outer bounds of the two cell columns
DIVIDER = (1199, 1201)                # thin rule between the columns, keep it
ROW_TOP, ROW_H, NROWS = 271, 45, 15   # zebra rows, black first
LEFT_INK, RIGHT_INK = 1020, 1224      # ink left edge of the text in each cell
ICON_RIGHT = 1041                     # right edge of the little button icons

# --- translations ------------------------------------------------------------------
# left cell: (chinese, has_icon); an icon occupies x 1012..1039 and is kept as is
LEFT = [
    ("方向键", False),
    ("右摇杆", False),
    ("左摇杆", False),
    ("键", True),      # L
    ("键", True),      # ZL
    ("键", True),      # R
    ("键", True),      # ZR
    ("键", True),      # +
    ("键", True),      # X
    ("键", True),      # A
    ("键", True),      # B
    ("键", True),      # Y
    ("左摇杆按下", False),
    ("右摇杆按下", False),
    ("键", True),      # -
]

# right cell: (chinese, size) or (chinese, size) tuples; row 5 is split into a main
# sentence plus a smaller parenthetical, exactly like the original.  Size None means
# BODY_RIGHT_SIZE; the trailing "baseline" flag keeps a shrunken part on the same line.
RIGHT = [
    [("光标移动", None)],
    [("同方向键", None)],
    [("同方向键", None)],
    [("强制跳过（按住时）", None)],
    [("跳过模式开关", None)],
    [("切换操作模式", None), ("（选择画面⇒道具⇒宝玉⇒选择画面 循环）", 16, "baseline")],
    [("自动模式开关", None)],
    [("打开系统菜单", None)],
    [("打开历史记录", None)],
    [("推进文本·确定选项", None)],
    [("停止自动／跳过·取消", None)],
    [("打开 A.D.M.S.", None)],
    [("不使用", None)],
    [("不使用", None)],
    [("不使用", None)],
]

# --- call-outs around the controller drawings --------------------------------------
# (key, ink bbox x0,y0,x1,y1, icon right edge or None, chinese, anchor)
#   anchor: "icon" -> draw behind the kept icon, "left"/"right" -> align the new text
#   to the leader line that connects the label with the controller
CALLOUTS = [
    ("minus", 416, 237, 518, 262, 441, "键", "icon"),
    ("plus", 601, 237, 703, 262, 627, "键", "icon"),
    ("Lstick", 138, 368, 269, 392, None, "左摇杆", "right"),
    ("dpad", 141, 467, 269, 492, None, "方向键", "right"),
    ("Y", 842, 299, 947, 325, 870, "键", "icon"),
    ("X", 842, 334, 947, 359, 870, "键", "icon"),
    ("A", 842, 368, 947, 393, 870, "键", "icon"),
    ("B", 842, 402, 947, 428, 870, "键", "icon"),
    ("Rstick", 845, 468, 977, 492, None, "右摇杆", "left"),
    ("ZL", 162, 760, 270, 786, 191, "键", "icon"),
    ("L", 162, 799, 270, 825, 191, "键", "icon"),
    ("ZR", 841, 760, 947, 787, 870, "键", "icon"),
    ("R", 842, 799, 949, 825, 871, "键", "icon"),
]

# heading: ink boxes measured on the original sheet
TITLE_BOX = (84, 58, 328, 122)                 # "HELP"
TITLE_X, TITLE_SIZE, TITLE_PITCH = 84, 68, 93  # 帮助: first glyph, size, tracking
SUBTITLE_SLOTS = (281, 333, 385, 437)          # centres of 操 / 作 / 说 / 明
TITLE_CLEAN = (78, 52, 338, 136)               # "HELP" box incl. its shadow
SUBTITLE_CLEAN = (366, 96, 554, 128)           # 操作説明 box

_FONTS = {}


def font(path, size, variation=None):
    key = (path, int(size), variation)
    if key not in _FONTS:
        f = ImageFont.truetype(path, int(size))
        if variation:
            try:
                f.set_variation_by_name(variation)
            except Exception as exc:  # pragma: no cover
                print("warning: variation %r failed: %s" % (variation, exc), file=sys.stderr)
        _FONTS[key] = f
    return _FONTS[key]


_MEASURE = ImageDraw.Draw(Image.new("RGBA", (8, 8)))


def ink_bbox(text, fnt):
    return _MEASURE.textbbox((0, 0), text, font=fnt, anchor="la")


def text_op(text, *, x=None, x_right=None, x_center=None, y_center=None, y_top=None,
            font_path=FONT_SANS, size=23, variation="Bold", color="#ffffff",
            stroke_width=0, stroke_fill="#000000"):
    """Build a ui_edit text op positioned by its *ink* box."""
    fnt = font(font_path, size, variation)
    b = ink_bbox(text, fnt)
    w, h = b[2] - b[0], b[3] - b[1]
    if x is not None:
        pen_x = x - b[0]
    elif x_right is not None:
        pen_x = x_right - b[2]
    else:
        pen_x = x_center - (b[0] + b[2]) / 2.0
    if y_top is not None:
        pen_y = y_top - b[1]
    else:
        pen_y = y_center - (b[1] + b[3]) / 2.0
    return {
        "rect": [int(round(pen_x)), int(round(pen_y)), int(w), int(h)],
        "text": text,
        "font": font_path,
        "size": int(size),
        "variation": variation,
        "color": color,
        "align": "left",
        "valign": "top",
        "dx": 0,
        "dy": 0,
        "stroke_width": int(stroke_width),
        "stroke_fill": stroke_fill,
    }


# ---------------------------------------------------------------------------------
# texture patching for the paper background
# ---------------------------------------------------------------------------------
def _ring_mask(shape, pad, core):
    h, w = core
    m = np.zeros(shape[:2], bool)
    m[pad:pad + h, pad:pad + w] = True
    return m


def patch_fill(arr, x0, y0, x1, y1, pad=6, feather=4.0, dx_range=(-360, 360, 18),
               dy_range=(-140, 140, 7), max_inner_std=26.0, tag=""):
    """Replace a text patch of textured background with a similar, text free patch.

    The donor is searched on the same image: the ring of paper around the text is
    compared with the ring of every candidate offset, the best match wins, and the
    donor is brightness matched to the surroundings and blended with a soft mask.
    """
    h, w = y1 - y0, x1 - x0
    rx0, ry0, rx1, ry1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    rgb = arr[:, :, :3].astype(float)          # alpha is left untouched
    target = rgb[ry0:ry1, rx0:rx1]
    ring = ~_ring_mask(target.shape, pad, (h, w))
    t_ring = target[ring]
    t_mean = t_ring.mean(0)
    t_std = t_ring.std(0)

    best = None
    for dy in range(dy_range[0], dy_range[1] + 1, dy_range[2]):
        for dx in range(dx_range[0], dx_range[1] + 1, dx_range[2]):
            if dx == 0 and dy == 0:
                continue
            sx0, sy0 = rx0 + dx, ry0 + dy
            if sx0 < 0 or sy0 < 0 or sx0 + target.shape[1] > arr.shape[1] or sy0 + target.shape[0] > arr.shape[0]:
                continue
            # never take the donor from the very area that is being replaced: it still
            # holds the original glyphs and copying it back would leave fragments
            if sx0 < rx1 and sx0 + target.shape[1] > rx0 and sy0 < ry1 and sy0 + target.shape[0] > ry0:
                continue
            donor = rgb[sy0:sy0 + target.shape[0], sx0:sx0 + target.shape[1]]
            d_ring = donor[ring]
            inner = donor[pad:pad + h, pad:pad + w]
            # reject donors that overlap other artwork / text
            if inner.reshape(-1, 3).std(0).mean() > max_inner_std:
                continue
            if np.abs(inner.reshape(-1, 3).mean(0) - t_mean).max() > 60:
                continue
            score = (np.abs(d_ring.mean(0) - t_mean).sum()
                     + 2.0 * np.abs(d_ring.std(0) - t_std).sum()
                     + 0.02 * (abs(dx) + abs(dy)))
            if best is None or score < best[0]:
                best = (score, dx, dy)
    if best is None:
        raise RuntimeError("no clean donor patch found for %s" % (tag or (x0, y0)))
    _, dx, dy = best
    donor = rgb[ry0 + dy:ry0 + dy + target.shape[0], rx0 + dx:rx0 + dx + target.shape[1]].copy()
    d_ring = donor[ring]
    donor += (t_mean - d_ring.mean(0))            # match the local paper brightness

    mask = np.zeros((target.shape[0], target.shape[1]))
    yy = np.arange(mask.shape[0])[:, None]
    xx = np.arange(mask.shape[1])[None, :]
    # distance outside the core rectangle (0 while still inside it)
    d = np.maximum(np.maximum(pad - yy, yy - (pad + h - 1)), 0)
    d = np.maximum(d, np.maximum(np.maximum(pad - xx, xx - (pad + w - 1)), 0))
    t = np.clip(1.0 - d / float(feather), 0.0, 1.0)
    m = (t * t * (3.0 - 2.0 * t))[:, :, None]

    blended = target * (1.0 - m) + donor * m
    arr[ry0:ry1, rx0:rx1, :3] = np.clip(blended, 0, 255).astype(arr.dtype)
    print("  patch %-8s <- offset (%+d,%+d) score %.1f" % (tag, dx, dy, best[0]))
    return arr


def clean_background(arr):
    """Remove the heading and the call-out labels from the paper background."""
    # the caption is cleaned first so that its (now empty) paper can serve as a donor
    # for the big title patch
    x0, y0, x1, y1 = SUBTITLE_CLEAN
    arr = patch_fill(arr, x0, y0, x1, y1, pad=10, feather=7.0,
                     dx_range=(-320, 560, 12), dy_range=(-84, 40, 6),
                     max_inner_std=22.0, tag="subtitle")
    x0, y0, x1, y1 = TITLE_CLEAN
    arr = patch_fill(arr, x0, y0, x1, y1, pad=11, feather=8.0,
                     dx_range=(-70, 700, 12), dy_range=(-40, 8, 6),
                     max_inner_std=24.0, tag="title")
    for key, bx0, by0, bx1, by1, icon_right, _text, anchor in CALLOUTS:
        if anchor == "icon":
            ex0 = icon_right + 1
        else:
            ex0 = bx0 - 2
        arr = patch_fill(arr, ex0 - 1, by0 - 1, bx1 + 1, by1 + 1, pad=9, feather=5.0,
                         dx_range=(-300, 300, 15), dy_range=(-120, 120, 6), tag=key)
    return arr


# ---------------------------------------------------------------------------------
# spec building
# ---------------------------------------------------------------------------------
def light_row_color(arr, i):
    y0 = ROW_TOP + ROW_H * i
    sub = arr[y0 + 8:y0 + 37, 1760:1794, :3].reshape(-1, 3)
    mean = sub.mean(0)
    return "#%02x%02x%02x" % tuple(int(round(v)) for v in mean)


def build_spec(arr):
    spec = []

    # heading -----------------------------------------------------------------
    # the original is a wide italic serif "HELP" plus a spaced 操作説明 caption,
    # so the Chinese title gets a little tracking and a soft drop shadow
    title_center = (TITLE_BOX[1] + TITLE_BOX[3]) / 2.0
    for dx, color in ((4, "#14110c"), (2, "#1b1712"), (0, "#ffffff")):
        for cx, ch in ((TITLE_X, "帮"), (TITLE_X + TITLE_PITCH, "助")):
            spec.append(text_op(ch, x=cx + dx, y_center=title_center + dx * 0.8,
                                font_path=FONT_SERIF, size=TITLE_SIZE,
                                variation="SemiBold", color=color))
    sub_center = (98 + 124) / 2.0
    for slot, ch in zip(SUBTITLE_SLOTS, "操作说明"):
        spec.append(text_op(ch, x_center=slot, y_center=sub_center, font_path=FONT_SERIF,
                            size=27, variation="Black", color="#ffffff"))

    # call-outs ---------------------------------------------------------------
    for key, bx0, by0, bx1, by1, icon_right, text, anchor in CALLOUTS:
        cy = (by0 + by1) / 2.0
        kw = dict(font_path=BODY_FONT, size=CALLOUT_SIZE, variation=CALLOUT_VAR,
                  color="#111111")
        if anchor == "icon":
            spec.append(text_op(text, x=icon_right + 4, y_center=cy, **kw))
        elif anchor == "left":
            spec.append(text_op(text, x=bx0, y_center=cy, **kw))
        else:
            spec.append(text_op(text, x_right=bx1, y_center=cy, **kw))

    # table -------------------------------------------------------------------
    for i in range(NROWS):
        y0 = ROW_TOP + ROW_H * i
        black = (i % 2) == 0
        bg = "#000000" if black else light_row_color(arr, i)
        ink = "#ffffff" if black else "#0a0a0a"
        left, has_icon = LEFT[i]
        left_fill_x = ICON_RIGHT + 2 if has_icon else TABLE_L + 4
        spec.append({"rect": [left_fill_x, y0 + 3, DIVIDER[0] - left_fill_x - 5, ROW_H - 7],
                     "fill": bg})
        spec.append({"rect": [DIVIDER[1] + 5, y0 + 3, TABLE_R - DIVIDER[1] - 9, ROW_H - 7],
                     "fill": bg})
        cy = y0 + ROW_H / 2.0 - 0.5
        spec.append(text_op(left, x=(ICON_RIGHT + 2) if has_icon else LEFT_INK,
                            y_center=cy, font_path=BODY_FONT, size=BODY_LEFT_SIZE,
                            variation=BODY_LEFT_VAR, color=ink))
        pen = RIGHT_INK
        base = None
        for part in RIGHT[i]:
            text, size = part[0], part[1]
            size = BODY_RIGHT_SIZE if size is None else size
            fnt = font(BODY_FONT, size, BODY_RIGHT_VAR)
            if part[2:] and part[2] == "baseline" and base is not None:
                h = ink_bbox(text, fnt)[3]
                op = text_op(text, x=pen, y_top=base - h, font_path=BODY_FONT,
                             size=size, variation=BODY_RIGHT_VAR, color=ink)
            else:
                op = text_op(text, x=pen, y_center=cy, font_path=BODY_FONT,
                             size=size, variation=BODY_RIGHT_VAR, color=ink)
            spec.append(op)
            if base is None:
                b = ink_bbox(text, fnt)
                base = cy + (b[1] + b[3]) / 2.0
            pen += int(_MEASURE.textlength(text, font=fnt))
    return spec


# ---------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", default=SHEET)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--spec", default=SPEC)
    ap.add_argument("--prep", default=PREP)
    ap.add_argument("--recon-dir", default=os.path.join(ROOT, "_recon"))
    args = ap.parse_args()

    im = Image.open(args.sheet).convert("RGBA")
    arr = np.array(im)

    print("cleaning paper background")
    arr = clean_background(arr)
    Image.fromarray(arr).save(args.prep)

    spec = build_spec(arr)
    os.makedirs(os.path.dirname(args.spec), exist_ok=True)
    with open(args.spec, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=1)

    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "ui_edit.py"),
                    "--image", args.prep, "--spec", args.spec, "--out", args.out], check=True)
    # the sheet is a plain RGB texture in the original archive: keep it RGB
    Image.open(args.out).convert("RGB").save(args.out)
    print("help -> %s (%d ops)" % (args.out, len(spec)))

    os.makedirs(args.recon_dir, exist_ok=True)
    recon(args.out, args.sheet, args.recon_dir)
    return 0


def recon(out_path, sheet_path, recon_dir):
    """Compose crops of the result on light / dark backgrounds for inspection."""
    new = Image.open(out_path).convert("RGB")
    old = Image.open(sheet_path).convert("RGB")
    crops = {
        "title": (40, 20, 620, 160, 2.0),
        "labels": (100, 200, 1010, 860, 1.0),
        "table_top": (985, 220, 1810, 620, 1.0),
        "table_bottom": (985, 600, 1810, 960, 1.0),
    }
    for name, (x0, y0, x1, y1, scale) in crops.items():
        w, h = int((x1 - x0) * scale), int((y1 - y0) * scale)
        pair = Image.new("RGB", (w * 2 + 8, h), (255, 0, 255))
        for k, src in enumerate((old, new)):
            patch = src.crop((x0, y0, x1, y1)).resize((w, h), Image.LANCZOS)
            pair.paste(patch, (k * (w + 8), 0))
        pair.save(os.path.join(recon_dir, "help_check_%s.png" % name))
    for name, bg in (("dark", (24, 24, 24)), ("light", (238, 238, 232))):
        canvas = Image.new("RGBA", new.size, bg + (255,))
        canvas.alpha_composite(new.convert("RGBA"))
        canvas.convert("RGB").resize((1280, 720), Image.LANCZOS).save(
            os.path.join(recon_dir, "help_check_%s.png" % name))
    print("recon crops ->", recon_dir)


if __name__ == "__main__":
    sys.exit(main())

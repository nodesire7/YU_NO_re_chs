#!/usr/bin/env python3
"""Translate the labels in the system UI sheet (data01.png) into Simplified Chinese.

The sheet is an RGBA sprite sheet: six key-hint plates (black and white variants),
PS controller button labels on transparency, a CAUTION dialog frame, an install
progress label on a translucent plate, and four AUTO/SKIP badge animation strips
(seven frames each), plus a few decorative gears that carry no text.

`scan` / `cc` are small helpers used while localising the text; `build` writes
work/ui/data01_spec.json, applies it with tools/ui_edit.py and exports the check
crops (composited over dark grey) to _recon/.

Usage:
  python tools/ui_data01.py build
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "work", "extract", "system", "data01.png")
OUT = os.path.join(ROOT, "work", "ui_out", "data01.png")
SPEC = os.path.join(ROOT, "work", "ui", "data01_spec.json")
RECON = os.path.join(ROOT, "_recon")
FONT = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "NotoSerifSC-VF.ttf")

FONT_CACHE = {}


def load_font(size, variation="Bold"):
    key = (size, variation)
    if key not in FONT_CACHE:
        f = ImageFont.truetype(FONT, size)
        if variation:
            try:
                f.set_variation_by_name(variation)
            except Exception as exc:  # pragma: no cover
                print("warning: variation %r failed: %s" % (variation, exc), file=sys.stderr)
        FONT_CACHE[key] = f
    return FONT_CACHE[key]


ANCHOR = {"left": "l", "center": "m", "right": "r"}


def text_op(rect, text, size, color, align="center", valign="center", target=None,
            stroke_width=0, stroke_fill="#000000", **extra):
    """Build a ui_edit op whose ink box lands on `target` (ink left/centre, ink centre/bottom)."""
    x, y, w, h = rect
    font = load_font(size)
    probe = ImageDraw.Draw(Image.new("L", (8, 8)))
    anchor = ANCHOR[align] + {"top": "a", "center": "m", "bottom": "d"}[valign]
    bb = probe.textbbox((0, 0), text, font=font, anchor=anchor, stroke_width=stroke_width)
    if align == "left":
        px = x
    elif align == "right":
        px = x + w
    else:
        px = x + w // 2
    py = {"top": y, "center": y + h // 2, "bottom": y + h}[valign]
    tx, ty = target
    if align == "left":
        dx = tx - bb[0] - px
    elif align == "right":
        dx = tx - bb[2] - px
    else:
        dx = tx - (bb[0] + bb[2]) / 2.0 - px
    if valign == "center":
        dy = ty - (bb[1] + bb[3]) / 2.0 - py
    elif valign == "bottom":
        dy = ty - bb[3] - py
    else:
        dy = ty - bb[1] - py
    op = {
        "rect": [int(v) for v in rect],
        "text": text,
        "font": FONT,
        "size": int(size),
        "variation": "Bold",
        "color": color,
        "align": align,
        "valign": valign,
        "dx": int(round(dx)),
        "dy": int(round(dy)),
    }
    if stroke_width:
        op["stroke_width"] = int(stroke_width)
        op["stroke_fill"] = stroke_fill
    op.update(extra)
    ink = (px + op["dx"] + bb[0], py + op["dy"] + bb[1],
           px + op["dx"] + bb[2], py + op["dy"] + bb[3])
    OPS_INFO.append({"op": op, "ink": ink})
    return op


OPS_INFO = []


# ---------------------------------------------------------------------------
# 1. key hint plates: 96x36 rounded plates, black fill + white glyphs or the
#    reverse.  The plate interior is a flat colour, so repainting the text box
#    with that colour is invisible and removes the glyphs without halos.
#    (x, y, chinese, plate colour, original glyph centre)
# ---------------------------------------------------------------------------
KEY_PLATES = [
    (1074, 58, "取消", "dark", 1120.5, 74.5),
    (1174, 58, "取消", "light", 1220.5, 74.5),
    (674, 98, "跳过", "dark", 720.0, 115.5),
    (774, 98, "道具", "dark", 821.5, 115.5),
    (874, 98, "跳过", "light", 920.0, 115.5),
    (974, 98, "道具", "light", 1021.5, 115.5),
    (674, 138, "自动", "dark", 719.5, 155.5),
    (874, 138, "自动", "light", 919.5, 155.5),
    (1074, 138, "确定", "dark", 1120.5, 155.5),
    (1174, 138, "确定", "light", 1220.5, 155.5),
]
# "A.DMS." cells at (774,138) and (974,138) keep the original art.

CAUTION = "注意"
# Rows 61-69 carry a full width dark band (14,5,11) whose alpha ramps 3 -> 139;
# the old glyphs sit on top of it down to y=69, so the band has to be repainted
# row by row after clearing, otherwise the strip gets a hole.
CAUTION_BAND = [(61, 0x03), (62, 0x09), (63, 0x13), (64, 0x1f), (65, 0x2f),
                (66, 0x42), (67, 0x58), (68, 0x71), (69, 0x8b)]
CAUTION_RECT = [2259, 31, 192, 39]

# ---------------------------------------------------------------------------
# 2. PS controller labels (white serif on transparency, black soft shadow).
#    x, ink-y-centre, chinese, size
# ---------------------------------------------------------------------------
PAD_LABELS = [
    # ink x0, ink x1, ink y centre, chinese, size
    (18, 154, 597, "L肩键", 28),
    (312, 452, 597, "R肩键", 28),
    (606, 739, 597, "L扳机", 28),
    (900, 1037, 597, "R扳机", 28),
    (18, 272, 639, "L摇杆按键", 29),
    (312, 570, 639, "R摇杆按键", 29),
    (605, 718, 639, "开始", 27),
    (900, 993, 639, "返回", 27),
    (17, 135, 891, "分享", 27),
    (311, 468, 890, "选项", 27),
    (607, 747, 890, "PS按键", 29),
    (899, 1160, 890, "触摸板按键", 29),
]

# ---------------------------------------------------------------------------
# 3. AUTO / SKIP badge strips: 7 frames per row, cell pitch 120, first cell at
#    x=1471.  Rows 524/584 are AUTO (fade in / fade out), 644/704 are SKIP.
#    Frame alpha is baked into the sprite, so the replacement keeps it.
# ---------------------------------------------------------------------------
BADGE_X0 = 1471
BADGE_PITCH = 120
BADGE_ROWS = [
    (524, "自动", [0, 52, 103, 154, 205, 255, 255]),
    (584, "自动", [255, 255, 255, 255, 205, 154, 103]),
    (644, "跳过", [0, 52, 103, 154, 205, 255, 255]),
    (704, "跳过", [255, 255, 255, 255, 205, 154, 103]),
]


def build_spec():
    spec = []

    # --- key plates -------------------------------------------------------
    for x, y, text, plate, cx, cy in KEY_PLATES:
        dark = plate == "dark"
        spec.append(text_op(
            [x + 3, y + 3, 90, 30], text, 28,
            "#ffffff" if dark else "#0a0a0a",
            target=(cx, cy),
            fill="#000000" if dark else "#ffffff",
        ))

    # --- CAUTION title ----------------------------------------------------
    # the glyphs float on a soft dark glow and their feet reach into the band
    # above the rule, so clear the block, re-lay the band rows, rebuild a soft
    # glow around the new title and then draw it.
    spec.append({"rect": CAUTION_RECT, "clear": True})
    for y, a in CAUTION_BAND:
        spec.append({"rect": [CAUTION_RECT[0], y, CAUTION_RECT[2], 1],
                     "fill": "#0e050b%02x" % a})
    title_target = (2354, 46)
    # stepped rings emulate the soft drop shadow the Latin title had
    for sw, a in ((6, 0x18), (5, 0x20), (4, 0x2a), (3, 0x36), (2, 0x44), (1, 0x54)):
        spec.append(text_op(CAUTION_RECT, CAUTION, 34, "#0e050b00",
                            stroke_width=sw, stroke_fill="#0e050b%02x" % a,
                            target=title_target))
    # the feet of the old glyphs also sit on the dark AA row of the rule, which
    # is a flat 91 grey - repaint it over the glow spill.
    spec.append({"rect": [CAUTION_RECT[0], 70, CAUTION_RECT[2], 1], "fill": "#5b5b5b"})
    spec.append(text_op(CAUTION_RECT, CAUTION, 34, "#ecf0f0", target=title_target))

    # --- install progress label ------------------------------------------
    # translucent plate (5,1,1,179): repaint the label box (incl. its AA rows
    # 181/197) with the same colour, then draw the new caption
    spec.append(text_op([1466, 181, 124, 17], "安装中", 16, "#ffffff",
                        target=(1528, 189), fill="#050101b3"))

    # --- PS controller labels --------------------------------------------
    for x0, x1, cy, text, size in PAD_LABELS:
        spec.append(text_op([x0 - 5, cy - 18, x1 - x0 + 11, 36], text, size,
                            "#f0f2f2", align="left", target=(x0, cy), clear=True))

    # --- AUTO / SKIP badges ----------------------------------------------
    for y, text, alphas in BADGE_ROWS:
        for c, a in enumerate(alphas):
            if not a:
                continue
            cell = BADGE_X0 + BADGE_PITCH * c
            color = "#dddddd" if a >= 255 else "#dddddd%02x" % a
            spec.append(text_op([cell + 45, y + 2, 70, 40], text, 33, color,
                                align="left", target=(cell + 47, y + 21.5),
                                clear=True))
    return spec


def verify(path):
    """Check cleared/repainted boxes: nothing but the new glyph ink may survive."""
    from PIL import ImageColor
    im = Image.open(path).convert("RGBA")
    arr = np.array(im).astype(int)
    by_rect = {}
    for info in OPS_INFO:
        by_rect.setdefault(tuple(info["op"]["rect"]), []).append(info)
    bad_total = 0
    for rect, infos in sorted(by_rect.items()):
        x, y, w, h = rect
        clear = any(i["op"].get("clear") for i in infos)
        fills = [i["op"]["fill"] for i in infos if i["op"].get("fill")]
        if not clear and not fills:
            continue
        x0 = min(i["ink"][0] for i in infos) - 1
        y0 = min(i["ink"][1] for i in infos) - 1
        x1 = max(i["ink"][2] for i in infos) + 1
        y1 = max(i["ink"][3] for i in infos) + 1
        mask = np.ones((h, w), bool)
        xa, xb = max(0, int(x0 - x)), min(w, int(x1 - x + 1))
        ya, yb = max(0, int(y0 - y)), min(h, int(y1 - y + 1))
        mask[ya:yb, xa:xb] = False
        sub = arr[y:y + h, x:x + w]
        if clear:
            bad = mask & (sub[:, :, 3] > 8)
        else:
            col = ImageColor.getrgb(fills[-1])
            exp = np.array(col + ((255,) if len(col) == 3 else ()))
            diff = np.abs(sub - exp).max(axis=2)
            bad = mask & (diff > 8)
        n = int(bad.sum())
        if n:
            bad_total += n
            ys, xs = np.where(bad)
            print("  residue in %s: %d px, bbox x %d..%d y %d..%d" % (
                rect, n, xs.min() + x, xs.max() + x, ys.min() + y, ys.max() + y))
    print("verify: %d stray pixels" % bad_total)
    return bad_total


def cmd_build(args):
    OPS_INFO.clear()
    spec = build_spec()
    os.makedirs(os.path.dirname(SPEC), exist_ok=True)
    with open(SPEC, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=1)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "ui_edit.py"),
                    "--image", SRC, "--spec", SPEC, "--out", OUT], check=True)
    print("spec -> %s (%d ops)" % (SPEC, len(spec)))
    verify(OUT)
    return 0


def composite(im, box, bg=(38, 36, 34, 255), scale=1.0):
    crop = im.crop(box)
    base = Image.new("RGBA", crop.size, bg)
    base.alpha_composite(crop)
    out = base.convert("RGB")
    if scale != 1.0:
        out = out.resize((int(out.width * scale), int(out.height * scale)), Image.LANCZOS)
    return out


def cmd_check(args):
    im = Image.open(OUT).convert("RGBA")
    os.makedirs(RECON, exist_ok=True)
    boxes = [
        ("keys", (640, 0, 1290, 200), 1.6),
        ("pad", (0, 500, 1300, 960), 1.2),
        ("caution", (2180, 10, 2540, 110), 2.6),
        ("install", (1400, 150, 1660, 300), 2.6),
        ("badges", (1440, 490, 2320, 770), 1.4),
    ]
    for name, box, scale in boxes:
        p = os.path.join(RECON, "data01_check_%s.png" % name)
        composite(im, box, scale=scale).save(p)
        print("check ->", p)
    # light background variant of the title, to judge the cleared glow
    composite(im, (2180, 10, 2540, 110), bg=(220, 215, 205, 255), scale=2.6).save(
        os.path.join(RECON, "data01_check_caution_light.png"))
    return 0


# ---------------------------------------------------------------------------
# localisation helpers
# ---------------------------------------------------------------------------
def mask_of(arr, mode):
    alpha = arr[:, :, 3]
    lum = arr[:, :, :3].mean(axis=2)
    if mode == "a":
        return alpha > 30
    if mode == "l":
        return (alpha > 30) & (lum > 110)
    return (alpha > 30) & (lum < 110)


def runs(flags, gap):
    out, start, miss = [], None, 0
    for i, f in enumerate(flags):
        if f:
            if start is None:
                start = i
            miss = 0
        elif start is not None:
            miss += 1
            if miss > gap:
                out.append((start, i - miss))
                start, miss = None, 0
    if start is not None:
        out.append((start, len(flags) - 1 - miss))
    return out


def cmd_scan(args):
    x0, y0, x1, y1 = [int(v) for v in args.rect.split(",")]
    arr = np.array(Image.open(args.image).convert("RGBA"))[y0:y1, x0:x1]
    m = mask_of(arr, args.mode)
    rows = m.sum(axis=1)
    print("row bands:")
    for a, b in runs(rows > 0, args.gap):
        print("  %5d %5d  h=%d" % (a + y0, b + y0, b - a + 1))
    if args.lines:
        for ya, yb in runs(rows > 0, args.gap):
            cols = m[ya:yb + 1].sum(axis=0)
            print(" line y=%d..%d:" % (ya + y0, yb + y0))
            for a, b in runs(cols > 0, args.gapx):
                print("   x %5d..%5d  w=%d" % (a + x0, b + x0, b - a + 1))
    return 0


def cmd_cc(args):
    x0, y0, x1, y1 = [int(v) for v in args.rect.split(",")]
    arr = np.array(Image.open(args.image).convert("RGBA"))[y0:y1, x0:x1]
    m = mask_of(arr, args.mode)
    from scipy import ndimage
    lab, n = ndimage.label(m, structure=np.ones((3, 3)))
    boxes = []
    for i in range(1, n + 1):
        ys, xs = np.where(lab == i)
        if len(xs) < args.min_area:
            continue
        boxes.append([int(xs.min()) + x0, int(ys.min()) + y0,
                      int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1), len(xs)])
    boxes.sort(key=lambda b: (b[1], b[0]))
    for b in boxes:
        print("  x=%4d y=%4d w=%3d h=%3d area=%5d" % tuple(b))
    print("%d components" % len(boxes))
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("build", cmd_build), ("check", cmd_check)):
        sub.add_parser(name).set_defaults(func=fn)
    sp = sub.add_parser("scan")
    sp.add_argument("--image", default=SRC)
    sp.add_argument("--rect", required=True)
    sp.add_argument("--mode", default="a", choices=["a", "l", "d"])
    sp.add_argument("--gap", type=int, default=4)
    sp.add_argument("--gapx", type=int, default=6)
    sp.add_argument("--lines", action="store_true")
    sp.set_defaults(func=cmd_scan)
    cp = sub.add_parser("cc")
    cp.add_argument("--image", default=SRC)
    cp.add_argument("--rect", required=True)
    cp.add_argument("--mode", default="a", choices=["a", "l", "d"])
    cp.add_argument("--min-area", type=int, default=8)
    cp.set_defaults(func=cmd_cc)
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

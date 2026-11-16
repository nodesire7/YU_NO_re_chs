#!/usr/bin/env python3
"""Localise the music-room sheet (system/music.png) into Chinese.

The sheet is 1920x3474 and holds:

  y    0..1079   header: calligraphic 音楽室 + the SOUND LIBRARY plaque
  y 2179..2273   tab row 1: selected REMAKE (left) / ORIGINAL (right)
  y 2280..2370   tab row 2: REMAKE (left) / selected ORIGINAL (right)
  y 2280..3455   song list frame, transport bar and the two 戻る / BACK buttons
  x 1400..1610   the オリジナル / リメイク source labels next to the toggle pills

The glyphs are baked into textured plates, so they are removed with masks:

  * calligraphy  - warm beige ink segmented by tint and healed with a Laplace
    diffusion plus grain matched to the surrounding stone;
  * plaque       - pure black base, repainted as an anti-aliased black pill;
  * tab labels   - white / grey serif on parchment or dark wood plates, removed
    with a median background model and refilled by diffusion (the plates are
    soft watercolour, so no patch seams show);
  * オリジナル / リメイク - sit on transparent pixels, so the rectangles are
    simply cleared;
  * 戻る          - removed from the watercolour discs by diffusion.

Chinese strings are described in work/ui/music_spec.json and drawn by
tools/ui_edit.py; the condensed calligraphy is composited by this script because
ui_edit.py cannot scale glyphs.

Usage:
  python tools/ui_music.py [--sheet ...] [--out ...] [--recon-dir ...]
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WINDIR = os.environ.get("WINDIR", r"C:\Windows")
NOTO = os.path.join(WINDIR, "Fonts", "NotoSerifSC-VF.ttf")
SIMKAI = os.path.join(WINDIR, "Fonts", "simkai.ttf")
LXGW = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows",
                    "Fonts", "LXGWWenKai-Regular.ttf")

SHEET = os.path.join(ROOT, "work", "extract", "system", "music.png")
OUT = os.path.join(ROOT, "work", "ui_out", "music.png")
SPEC = os.path.join(ROOT, "work", "ui", "music_spec.json")
RECON = os.path.join(ROOT, "_recon")

TITLE_FONT = SIMKAI if os.path.exists(SIMKAI) else LXGW
TITLE_COLOR = (150, 130, 92, 238)
TITLE_STROKE = 3
TITLE_XSCALE = 0.85
PLAQUE_COLOR = "#807a6d"
TITLE = [("音", 215, 95, 100), ("乐", 215, 290, 102), ("室", 190, 470, 80)]
TITLE_BOX = (0, 0, 570, 340)

PLAQUE = (376, 170, 176, 29)
PLAQUE_TEXT = "音乐鉴赏"
PLAQUE_SIZE = 22
PLAQUE_PITCH = 37

# tab labels: (rect, ink centre, selected?, text)
TABS = [
    ((410, 2192, 162, 44), (493.5, 2214.5), True, "重制版"),
    ((1065, 2194, 182, 42), (1155.5, 2215.0), False, "原版"),
    ((414, 2304, 156, 40), (493.5, 2323.0), False, "重制版"),
    ((1065, 2302, 182, 44), (1155.5, 2323.5), True, "原版"),
]
TAB_SIZE = 36
TAB_ON = "#f4f1e8"       # selected (light) tab: white text
TAB_OFF = "#a5a199"      # unselected (dark) tab: grey text

# オリジナル / リメイク labels on transparent background
SOURCE_LABELS = [
    ((1406, 3166, 206, 54), (1598, 3196.5), "原版"),
    ((1432, 3234, 160, 52), (1598, 3262.5), "重制版"),
]
SOURCE_SIZE = 40
SOURCE_COLOR = "#f2efe8"

# 戻る circle buttons: (rect, ink centre, text colour)
BACK_BUTTONS = [
    ((30, 3348, 120, 50), (92, 3376), "#221f1b"),
    ((216, 3348, 120, 50), (278, 3376), "#f4f2ea"),
]
BACK_TEXT = "返回"
BACK_SIZE = 35


# ---------------------------------------------------------------------------
# helpers (same technique as tools/ui_album.py)
# ---------------------------------------------------------------------------
def warm_ink_mask(rgb, box, min_tint=28, min_r=70):
    x0, y0, x1, y1 = box
    sub = rgb[y0:y1, x0:x1].astype(np.int32)
    r, b = sub[:, :, 0], sub[:, :, 2]
    m = ((r - b) > min_tint) & (r > min_r)
    m = ndimage.binary_opening(m, np.ones((2, 2)))
    m = ndimage.binary_closing(m, np.ones((5, 5)))
    m = ndimage.binary_dilation(m, np.ones((6, 6)))
    return m


def glyph_mask(lum, box, mode, delta=24, size=41, dilate=2):
    x0, y0, x1, y1 = box
    sub = lum[y0:y1, x0:x1]
    bg = ndimage.median_filter(sub, size=size, mode="nearest")
    if mode == "dark":
        m = sub < bg - delta
    elif mode == "bright":
        m = sub > bg + delta
    else:
        m = np.abs(sub - bg) > delta
    if dilate:
        m = ndimage.binary_dilation(m, np.ones((dilate, dilate)))
    return m


def diffuse_fill(rgba, box, m, iterations=240):
    x0, y0, x1, y1 = box
    sub = rgba[y0:y1, x0:x1].astype(np.float32)
    work = sub.copy()
    dist, (iy, ix) = ndimage.distance_transform_edt(m, return_indices=True)
    work[m] = sub[iy[m], ix[m]]
    for _ in range(iterations):
        blur = ndimage.uniform_filter(work, size=(3, 3, 1), mode="nearest")
        work[m] = blur[m]
    rgba[y0:y1, x0:x1] = np.clip(work, 0, 255).round().astype(np.uint8)
    return int(m.sum())


def pill_distance(shape, px, py, pw, ph):
    """Signed distance to the plaque pill surface (negative inside)."""
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    r = ph / 2.0
    cy = py + r
    x0, x1 = px + r, px + pw - r
    dx = np.clip(xx, x0, x1) - xx
    dy = cy - yy
    return np.sqrt(dx * dx + dy * dy) - r


# ---------------------------------------------------------------------------
# erasing passes
# ---------------------------------------------------------------------------
def heal_title(rgba, rng):
    """Remove the calligraphy and refill the stone behind it (see ui_album.py)."""
    box = TITLE_BOX
    x0, y0, x1, y1 = box
    m = warm_ink_mask(rgba[:, :, :3], box)
    px, py, pw, ph = PLAQUE
    m[max(0, py - 4):py + ph + 4, max(0, px - 4):px + pw + 4] = True
    sub = rgba[y0:y1, x0:x1].astype(np.float32)
    work = sub.copy()
    dist, (iy, ix) = ndimage.distance_transform_edt(m, return_indices=True)
    work[m] = sub[iy[m], ix[m]]
    for _ in range(320):
        blur = ndimage.uniform_filter(work, size=(3, 3, 1), mode="nearest")
        work[m] = blur[m]
    full = np.zeros(rgba.shape[:2], bool)
    full[y0:y1, x0:x1] = m
    ring = (ndimage.binary_dilation(full, np.ones((31, 31)))
            & ~ndimage.binary_dilation(full, np.ones((11, 11))))
    ring &= rgba[:, :, :3].mean(2) < 85
    ring_std = rgba[ring][:, :3].astype(np.float32).std(0).mean()
    h, w = y1 - y0, x1 - x0
    fine = ndimage.gaussian_filter(rng.normal(0.0, 1.0, (h, w)), 1.1)
    coarse = ndimage.gaussian_filter(rng.normal(0.0, 1.0, (h, w)), 4.0)
    tex = fine / max(fine.std(), 1e-6) * (ring_std * 0.45)
    tex += coarse / max(coarse.std(), 1e-6) * (ring_std * 0.45)
    hidden = work[m]
    hidden[:, :3] += tex[m][:, None]
    work[m] = hidden
    out = sub.copy()
    out[m] = work[m]
    out[:, :, 3] = sub[:, :, 3]
    rgba[y0:y1, x0:x1] = np.clip(out, 0, 255).round().astype(np.uint8)
    print("  calligraphy healed: %d px" % int(m.sum()))


def erase_plaque(rgba):
    px, py, pw, ph = PLAQUE
    d = pill_distance(rgba.shape, px, py, pw, ph)
    alpha = np.clip((1.0 - d) / 2.0, 0.0, 1.0)
    rgb = rgba[:, :, :3].astype(np.float32) * (1 - alpha[:, :, None])
    rgba[:, :, :3] = np.clip(rgb, 0, 255).round().astype(np.uint8)
    print("  plaque repainted: %d px" % int((alpha > 0.5).sum()))


def erase_tabs(rgba):
    lum = rgba[:, :, :3].mean(2)
    grain = np.random.default_rng(11).normal(0.0, 2.2, rgba.shape)
    for box, centre, selected, text in TABS:
        x, y, w, h = box
        full = (x, y, x + w, y + h)
        m = glyph_mask(lum, full, "contrast", delta=26 if selected else 16,
                       size=41, dilate=2 if selected else 4)
        if selected:
            # parchment is smooth: diffusion leaves no visible patch
            diffuse_fill(rgba, full, m)
        else:
            # dark wood plate: diffusion plus a light grain so the healed area
            # keeps the plate's noise instead of reading as a flat band
            diffuse_fill(rgba, full, m)
            sub = rgba[y:y + h, x:x + w]
            sub[m] = np.clip(sub[m].astype(np.float32) + grain[y:y + h, x:x + w][m],
                             0, 255).astype(np.uint8)
    print("  tab labels removed: %d" % len(TABS))


def clear_source_labels(rgba):
    """Those labels float on transparent pixels: just wipe the rectangles."""
    for box, centre, text in SOURCE_LABELS:
        x, y, w, h = box
        rgba[y:y + h, x:x + w] = (0, 0, 0, 0)
    print("  source labels cleared: %d" % len(SOURCE_LABELS))


def erase_back(rgba, box):
    x, y, w, h = box
    full = (x, y, x + w, y + h)
    lum = rgba[:, :, :3].mean(2)
    m = glyph_mask(lum, full, "contrast", delta=22, size=45, dilate=2)
    diffuse_fill(rgba, full, m)
    print("  back glyph removed: %d px" % int(m.sum()))


# ---------------------------------------------------------------------------
# spec + title
# ---------------------------------------------------------------------------
def text_op(cx, cy, text, size, color, font, variation=None, stroke_width=0,
            stroke_fill=None):
    op = {
        "rect": [int(cx) - 1, int(cy) - 1, 2, 2],
        "text": text,
        "font": font,
        "size": int(size),
        "color": color,
        "align": "center",
        "valign": "center",
        "dx": 0,
        "dy": 0,
    }
    if variation:
        op["variation"] = variation
    if stroke_width:
        op["stroke_width"] = int(stroke_width)
        op["stroke_fill"] = stroke_fill or "#000000"
    return op


def spaced_ops(cx, cy, text, size, color, font, variation=None, pitch=None):
    if not pitch:
        return [text_op(cx, cy, text, size, color, font, variation)]
    total = pitch * (len(text) - 1)
    return [text_op(cx - total / 2.0 + i * pitch, cy, ch, size, color, font,
                    variation) for i, ch in enumerate(text)]


def build_spec():
    spec = []
    px, py, pw, ph = PLAQUE
    spec += spaced_ops(px + pw / 2.0, py + ph / 2.0, PLAQUE_TEXT, PLAQUE_SIZE,
                       PLAQUE_COLOR, NOTO, "Bold", pitch=PLAQUE_PITCH)
    for box, centre, selected, text in TABS:
        if selected:
            # soft drop shadow under the white label, as the Latin had
            spec.append(text_op(centre[0] + 2, centre[1] + 2, text, TAB_SIZE,
                                "#665e4e", NOTO, "Bold"))
            spec.append(text_op(centre[0], centre[1], text, TAB_SIZE, TAB_ON,
                                NOTO, "Bold"))
        else:
            spec.append(text_op(centre[0], centre[1], text, TAB_SIZE, TAB_OFF,
                                NOTO, "Bold"))
    for box, right_centre, text in SOURCE_LABELS:
        # right aligned to the original label's right edge
        measure = ImageFont.truetype(NOTO, SOURCE_SIZE)
        measure.set_variation_by_name("Bold")
        b = measure.getbbox(text)
        width = b[2] - b[0]
        cx = right_centre[0] - width / 2.0
        spec.append(text_op(cx + 2, right_centre[1] + 2, text, SOURCE_SIZE,
                            "#2a2721", NOTO, "Bold"))
        spec.append(text_op(cx, right_centre[1], text, SOURCE_SIZE,
                            SOURCE_COLOR, NOTO, "Bold"))
    for box, centre, color in BACK_BUTTONS:
        spec.append(text_op(centre[0], centre[1], BACK_TEXT, BACK_SIZE, color,
                            NOTO, "Bold"))
    return spec


def draw_title(im):
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    metrics = ImageDraw.Draw(Image.new("L", (8, 8)))
    for ch, size, cx, cy in TITLE:
        font = ImageFont.truetype(TITLE_FONT, size)
        b = metrics.textbbox((0, 0), ch, font=font, anchor="la",
                             stroke_width=TITLE_STROKE)
        pad = 16
        tile = Image.new("RGBA", (b[2] - b[0] + pad * 2, b[3] - b[1] + pad * 2),
                         (0, 0, 0, 0))
        ImageDraw.Draw(tile).text((pad - b[0], pad - b[1]), ch, font=font,
                                  fill=TITLE_COLOR, anchor="la",
                                  stroke_width=TITLE_STROKE,
                                  stroke_fill=TITLE_COLOR)
        tile = tile.resize((max(1, round(tile.width * TITLE_XSCALE)), tile.height),
                           Image.LANCZOS)
        layer.alpha_composite(tile, (round(cx - tile.width / 2.0),
                                     round(cy - tile.height / 2.0)))
    out = im.copy()
    out.alpha_composite(layer)
    return out


def preview(im, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    w, h = im.size
    for name, col in (("dark", (26, 24, 22, 255)), ("light", (238, 236, 232, 255))):
        bg = Image.new("RGBA", (w, h), col)
        bg.alpha_composite(im)
        bg.convert("RGB").save(os.path.join(out_dir, "music_check_%s.png" % name))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", default=SHEET)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--spec", default=SPEC)
    ap.add_argument("--recon-dir", default=RECON)
    args = ap.parse_args()

    rng = np.random.default_rng(19790221)
    im = Image.open(args.sheet).convert("RGBA")
    rgba = np.array(im)
    orig_alpha = rgba[:, :, 3].copy()
    print("erasing music.png")
    heal_title(rgba, rng)
    erase_plaque(rgba)
    erase_tabs(rgba)
    for box, centre, color in BACK_BUTTONS:
        erase_back(rgba, box)
    # keep the sprite alpha exactly as shipped (only the cleared labels change it)
    rgba[:, :, 3] = orig_alpha
    clear_source_labels(rgba)
    erased_path = os.path.join(ROOT, "_recon", "music_erased.png")
    Image.fromarray(rgba).save(erased_path)

    spec = build_spec()
    os.makedirs(os.path.join(ROOT, "work", "ui"), exist_ok=True)
    with open(args.spec, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=1)
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "ui_edit.py"),
                    "--image", erased_path, "--spec", args.spec,
                    "--out", args.out], check=True)

    out = Image.open(args.out).convert("RGBA")
    out = draw_title(out)
    out.save(args.out)
    preview(out, args.recon_dir)
    print("music -> %s (%d spec ops + calligraphy)" % (args.out, len(spec)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

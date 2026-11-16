#!/usr/bin/env python3
"""Localise the gallery sheet (system/album.png) into Chinese.

The sheet is 1920x4464 and holds four stacked UI bands:

  y    0..1079   header: calligraphic 美術室 + the GRAPHICS LIBRARY plaque
  y 2189..2963   PAGE 01 thumb grid (5x4 empty slots)
  y 3017..3791   PAGE 02 thumb grid (5 empty slots, then 2 faded ones)
  y 3825..4159   page buttons, number strip and two 戻る / BACK circle buttons

Every translatable string is baked into a textured background (stone, parchment,
watercolour plate), so the old glyphs are removed with a mask based fill:

  * calligraphy  - the beige ink is segmented by its warm tint, then every masked
    pixel is refilled from a random nearby clean patch of the same texture;
  * plaque       - the plaque base is pure black, so the golden letters are simply
    repainted black;
  * NO DATA      - the warm grey letters are separated from the paper by a local
    contrast mask, refilled from the surrounding parchment;
  * 戻る          - the glyphs are separated from the plate by a local contrast
    mask and refilled from the plate around them.

The Chinese strings are described in work/ui/album_spec.json and drawn by
tools/ui_edit.py on top of the erased sheet; PAGE 01/02, the digits and the
decorations are deliberately left untouched.

Usage:
  python tools/ui_album.py [--sheet ...] [--out ...] [--recon-dir ...]
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

SHEET = os.path.join(ROOT, "work", "extract", "system", "album.png")
OUT = os.path.join(ROOT, "work", "ui_out", "album.png")
SPEC = os.path.join(ROOT, "work", "ui", "album_spec.json")
RECON = os.path.join(ROOT, "_recon")

TITLE_FONT = SIMKAI if os.path.exists(SIMKAI) else LXGW
TITLE_COLOR = (150, 130, 92, 238)   # translucent beige, as the original ink
TITLE_STROKE = 3                    # fake the brush weight of the original
TITLE_XSCALE = 0.85                 # original glyphs are ~0.8 as wide as tall
BODY_COLOR = "#6f6558"       # NO DATA watermark grey-brown
PLAQUE_COLOR = "#807a6d"     # plaque small-caps colour

# ---------------------------------------------------------------------------
# geometry measured on the 1920x4464 sheet
# ---------------------------------------------------------------------------
# calligraphy: (char, size, ink centre x, ink centre y); drawn condensed
TITLE = [("美", 215, 95, 100), ("术", 215, 290, 102), ("室", 190, 470, 80)]
TITLE_BOX = (0, 0, 570, 340)          # region that may contain ink

PLAQUE = (376, 170, 176, 29)          # x, y, w, h of the black pill
PLAQUE_TEXT = "图像鉴赏"
PLAQUE_SIZE = 22
PLAQUE_PITCH = 37

# empty-thumbnail placeholders: block origin (the NO DATA wordmark sits at +13,+15
# inside a 82x62 stamp) for both page bands
NODATA_P1 = [(334 + 282 * c, 2345 + 168 * r) for r in range(4) for c in range(5)]
NODATA_P2 = [(334 + 282 * c, 3173) for c in range(5)] + \
            [(334, 3341), (616, 3341)]
NODATA_TEXT = "无数据"

# (x, y, w, h) tight boxes around 戻る, and the ink centre of the replacement;
# (mode, colour): dark glyph on light plate / white glyph on teal plate
BACK_BUTTONS = [
    ((1788, 3886, 112, 44), (1846, 3911), "dark", "#221f1b"),
    ((1788, 4060, 112, 44), (1846, 4084), "bright", "#f4f2ea"),
]
BACK_TEXT = "返回"
BACK_SIZE = 35


# ---------------------------------------------------------------------------
# masking / inpainting helpers
# ---------------------------------------------------------------------------
def warm_ink_mask(rgb, box, min_tint=14, min_r=55):
    """Segment the beige calligraphy: warm tint (R-B) above the stone's."""
    x0, y0, x1, y1 = box
    sub = rgb[y0:y1, x0:x1].astype(np.int32)
    r, b = sub[:, :, 0], sub[:, :, 2]
    m = ((r - b) > min_tint) & (r > min_r)
    m = ndimage.binary_closing(m, np.ones((3, 3)))
    m = ndimage.binary_dilation(m, np.ones((5, 5)))
    return m


def local_contrast_mask(lum, box, thr, dilate=2):
    """Mask glyph pixels that stick out of their locally averaged background."""
    x0, y0, x1, y1 = box
    sub = lum[y0:y1, x0:x1]
    bg = ndimage.median_filter(sub, size=(11, 11))
    m = np.abs(sub - bg) > thr
    m = ndimage.binary_opening(m, np.ones((2, 2)))
    if dilate:
        m = ndimage.binary_dilation(m, np.ones((dilate, dilate)))
    return m


def glyph_mask(lum, box, mode, delta=24, size=41, dilate=2, opening=False):
    """Separate a label from its plate with a large median background model.

    A 41 px median ignores the strokes (they never fill half the window), so
    solid glyph bodies are caught as well as their soft shadows. No opening
    pass: the thin 1 px tops of strokes must survive the mask. mode="contrast"
    also catches the dark rim drawn around white letters.
    """
    x0, y0, x1, y1 = box
    sub = lum[y0:y1, x0:x1]
    bg = ndimage.median_filter(sub, size=size, mode="nearest")
    if mode == "dark":
        m = sub < bg - delta
    elif mode == "bright":
        m = sub > bg + delta
    else:
        m = np.abs(sub - bg) > delta
    if opening:
        m = ndimage.binary_opening(m, np.ones((2, 2)))
    if dilate:
        m = ndimage.binary_dilation(m, np.ones((dilate, dilate)))
    return m


def dark_glyph_mask(lum, box, thr, dilate=2):
    x0, y0, x1, y1 = box
    m = lum[y0:y1, x0:x1] < thr
    m = ndimage.binary_opening(m, np.ones((2, 2)))
    if dilate:
        m = ndimage.binary_dilation(m, np.ones((dilate, dilate)))
    return m


def bright_glyph_mask(lum, box, thr, dilate=2):
    x0, y0, x1, y1 = box
    m = lum[y0:y1, x0:x1] > thr
    m = ndimage.binary_opening(m, np.ones((2, 2)))
    if dilate:
        m = ndimage.binary_dilation(m, np.ones((dilate, dilate)))
    return m


def patch_fill(rgba, mask, rng, radii, max_lum=None, min_alpha=200, exclude=None,
               min_lum=None, max_sat=None):
    """Replace masked pixels with texture taken from random nearby clean patches.

    Each masked pixel copies an unmasked source pixel at a random offset, so the
    grain / watercolour speckle of the background survives instead of a flat
    colour block. Pixels that cannot be sourced are filled from their nearest
    clean neighbour.
    """
    h, w = mask.shape
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return
    lum = rgba[:, :, :3].mean(2)
    usable = ~mask
    usable &= rgba[:, :, 3] > min_alpha
    if max_lum is not None:
        usable &= lum < max_lum
    if exclude is not None:
        usable &= ~exclude
    if min_lum is not None:
        usable &= lum >= min_lum
    if max_sat is not None:
        usable &= (rgba[:, :, :3].max(2).astype(np.int32)
                   - rgba[:, :, :3].min(2).astype(np.int32)) <= max_sat
    offsets = []
    for rad in radii:
        for ang in range(0, 360, 12):
            offsets.append((int(round(rad * np.cos(np.radians(ang)))),
                            int(round(rad * np.sin(np.radians(ang))))))
    rng.shuffle(offsets)
    done = np.zeros(len(xs), bool)
    src_rgba = rgba.copy()
    for dx, dy in offsets:
        if done.all():
            break
        sx = np.clip(xs + dx, 0, w - 1)
        sy = np.clip(ys + dy, 0, h - 1)
        ok = (~done) & usable[sy, sx]
        idx = np.nonzero(ok)[0]
        if not len(idx):
            continue
        rgba[ys[idx], xs[idx]] = src_rgba[sy[idx], sx[idx]]
        done[idx] = True
    rem = np.nonzero(~done)[0]
    if len(rem):
        dist, (iy, ix) = ndimage.distance_transform_edt(mask, return_indices=True)
        rgba[ys[rem], xs[rem]] = src_rgba[iy[ys[rem], xs[rem]], ix[ys[rem], xs[rem]]]


def apply_mask_at(rgba, box, m, rng, radii, max_lum=None, exclude=None,
                  min_lum=None, max_sat=None):
    x0, y0, x1, y1 = box
    full = np.zeros(rgba.shape[:2], bool)
    full[y0:y1, x0:x1] = m
    patch_fill(rgba, full, rng, radii, max_lum=max_lum, exclude=exclude,
               min_lum=min_lum, max_sat=max_sat)
    return int(full.sum())


def soften(rgba, mask, sigma=0.6):
    """Soften the seam of a patch filled area (keeps the copied grain)."""
    if not mask.any():
        return
    blur = ndimage.gaussian_filter(rgba.astype(np.float32), (sigma, sigma, 0))
    edge = ndimage.binary_dilation(mask, np.ones((3, 3))) & ~ndimage.binary_erosion(
        mask, np.ones((3, 3)))
    rgba[edge] = blur[edge].round().astype(np.uint8)


# ---------------------------------------------------------------------------
# erasing passes
# ---------------------------------------------------------------------------
def erase_title(rgba, rng):
    rgb = rgba[:, :, :3]
    box = TITLE_BOX
    m = warm_ink_mask(rgb, box)
    # the plaque is opaque black and gets its own treatment below
    px, py, pw, ph = PLAQUE
    m[max(0, py - 3):py + ph + 3, max(0, px - 3):px + pw + 3] = False
    # never source patches from the plaque - its golden letters would ghost
    exclude = np.zeros(rgba.shape[:2], bool)
    exclude[py - 8:py + ph + 8, px - 8:px + pw + 8] = True
    n = apply_mask_at(rgba, box, m, rng, (26, 44, 66, 92), max_lum=150,
                      exclude=exclude)
    print("  title ink removed: %d px" % n)


def pill_mask(shape, px, py, pw, ph):
    """Rounded pill covering the plaque, for a clean text repaint."""
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    r = ph / 2.0
    cy = py + r
    x0, x1 = px + r, px + pw - r
    dx = np.clip(xx, x0, x1) - xx
    dy = cy - yy
    return (dx * dx + dy * dy) <= (r - 0.6) ** 2


def erase_plaque(rgba):
    """The plaque base is pure black - repaint the golden small caps black."""
    px, py, pw, ph = PLAQUE
    lum = rgba[:, :, :3].mean(2)
    pill = pill_mask(lum.shape, px, py, pw, ph)
    m = pill & (lum > 26)
    rgba[m] = (0, 0, 0, 255)
    print("  plaque repainted: %d px" % int(m.sum()))


def erase_nodata(rgba, blocks, rng, faded_blocks=()):
    faded = set(faded_blocks)
    lum = rgba[:, :, :3].mean(2)
    for (bx, by) in blocks:
        is_faded = (bx, by) in faded
        top = by + 10 if is_faded else by + 12
        box = (bx + 6, top, bx + 96, by + 41)
        x0, y0, x1, y1 = box
        sub = lum[y0:y1, x0:x1]
        paper = np.percentile(sub, 90)
        m = sub < paper - (20 if is_faded else 24)
        m = ndimage.binary_dilation(m, np.ones((2, 2)))
        apply_mask_at(rgba, box, m, rng, (10, 16, 24, 34), max_sat=26)
    print("  NO DATA slots re-stamped: %d" % len(blocks))


def diffuse_fill(rgba, box, m, iterations=240):
    """Laplace inpaint of a masked label: the plate shading flows through the hole.

    Watercolour / printed plates have soft gradients rather than hard texture, so
    a diffusion fill leaves no screenshot-visible patch, unlike a copied patch.
    """
    x0, y0, x1, y1 = box
    sub = rgba[y0:y1, x0:x1].astype(np.float32)
    work = sub.copy()
    # seed the hole from the nearest surrounding colour
    dist, (iy, ix) = ndimage.distance_transform_edt(m, return_indices=True)
    work[m] = sub[iy[m], ix[m]]
    for _ in range(iterations):
        blur = ndimage.uniform_filter(work, size=(3, 3, 1), mode="nearest")
        work[m] = blur[m]
    rgba[y0:y1, x0:x1] = np.clip(work, 0, 255).round().astype(np.uint8)
    return int(m.sum())


def erase_back(rgba, box, mode, rng):
    x, y, w, h = box
    box = (x, y, x + w, y + h)
    lum = rgba[:, :, :3].mean(2)
    m = glyph_mask(lum, box, "contrast", delta=22, size=45, dilate=2)
    n = diffuse_fill(rgba, box, m)
    print("  back glyph removed: %d px" % n)


# ---------------------------------------------------------------------------
# spec
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
    """Draw a short string with wide tracking, as the Latin small caps had."""
    if not pitch:
        return [text_op(cx, cy, text, size, color, font, variation)]
    total = pitch * (len(text) - 1)
    ops = []
    for i, ch in enumerate(text):
        ops.append(text_op(cx - total / 2.0 + i * pitch, cy, ch, size, color,
                           font, variation))
    return ops


def draw_title(im):
    """Composite the calligraphy: condensed, faux-bold and slightly translucent.

    ui_edit.py cannot scale a glyph run or blend it translucently, so the header
    title is rendered here; every other string goes through the JSON spec.
    """
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


def build_spec():
    spec = []
    px, py, pw, ph = PLAQUE
    spec += spaced_ops(px + pw / 2.0, py + ph / 2.0, PLAQUE_TEXT, PLAQUE_SIZE,
                       PLAQUE_COLOR, NOTO, "Bold", pitch=PLAQUE_PITCH)
    for (bx, by) in NODATA_P1:
        spec.append(text_op(bx + 40, by + 26, NODATA_TEXT, 21, BODY_COLOR, NOTO,
                            "Bold"))
    for (bx, by) in NODATA_P2:
        spec.append(text_op(bx + 40, by + 27, NODATA_TEXT, 28, BODY_COLOR, NOTO,
                            "Bold"))
    for box, centre, mode, color in BACK_BUTTONS:
        spec.append(text_op(centre[0], centre[1], BACK_TEXT, BACK_SIZE, color,
                            NOTO, "Bold"))
    return spec


def preview(im, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    w, h = im.size
    for name, col in (("dark", (26, 24, 22, 255)), ("light", (238, 236, 232, 255))):
        bg = Image.new("RGBA", (w, h), col)
        bg.alpha_composite(im)
        bg.convert("RGB").save(os.path.join(out_dir, "album_check_%s.png" % name))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", default=SHEET)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--spec", default=SPEC)
    ap.add_argument("--recon-dir", default=RECON)
    args = ap.parse_args()

    rng = np.random.default_rng(20240517)
    im = Image.open(args.sheet).convert("RGBA")
    rgba = np.array(im)
    print("erasing album.png")
    erase_title(rgba, rng)
    erase_plaque(rgba)
    erase_nodata(rgba, NODATA_P1, rng)
    erase_nodata(rgba, NODATA_P2, rng, faded_blocks=((334, 3341), (616, 3341)))
    for box, centre, mode, color in BACK_BUTTONS:
        erase_back(rgba, box, mode, rng)
    erased = Image.fromarray(rgba)
    os.makedirs(os.path.join(ROOT, "work", "ui"), exist_ok=True)
    erased_path = os.path.join(ROOT, "_recon", "album_erased.png")
    erased.save(erased_path)

    spec = build_spec()
    with open(args.spec, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=1)
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "ui_edit.py"),
                    "--image", erased_path, "--spec", args.spec,
                    "--out", args.out], check=True)

    out = Image.open(args.out).convert("RGBA")
    out = draw_title(out)
    out.save(args.out)
    preview(out, args.recon_dir)
    print("album -> %s (%d spec ops + calligraphy)" % (args.out, len(spec)))

    # album_thum.png is a plain montage of CG thumbnails: no translatable text
    # (verified with a matched filter, see the report), so the sheet is passed
    # through unchanged through an empty spec.
    thum = os.path.join(ROOT, "work", "extract", "system", "album_thum.png")
    thum_out = os.path.join(ROOT, "work", "ui_out", "album_thum.png")
    thum_spec = os.path.join(ROOT, "work", "ui", "album_thum_spec.json")
    with open(thum_spec, "w", encoding="utf-8") as fh:
        json.dump([], fh, indent=1)
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "ui_edit.py"),
                    "--image", thum, "--spec", thum_spec,
                    "--out", thum_out], check=True)
    th = Image.open(thum_out).convert("RGB")
    for name, col in (("dark", (26, 24, 22)), ("light", (238, 236, 232))):
        bg = Image.new("RGB", th.size, col)
        bg.paste(th)
        bg.save(os.path.join(args.recon_dir, "album_thum_check_%s.png" % name))
    print("album_thum -> %s (no text found, passthrough)" % thum_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

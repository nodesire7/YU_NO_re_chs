#!/usr/bin/env python3
"""Localize the in-game menu labels and keep their original icons and lighting."""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation, convolve, distance_transform_edt, gaussian_filter

from ui_config import FONT
from ui_edit import glyph_mask, load_font

ROOT = Path(__file__).resolve().parent.parent
# The lower bounds end at the original sprite margins, before each next icon.
ROWS = (
    (146, 196, "历史记录"),
    (329, 374, "设置"),
    (503, 548, "帮助"),
    (679, 723, "存档"),
    (864, 925, "返回\n标题"),
)
INK = ((76, 10, 0), (76, 10, 0), (147, 133, 113))
BASE_X = 313
COLUMN_WIDTH = 176
COLUMN_PITCH = 210


def centered_label(layer, text, font, box, color):
    left, top, right, bottom = box
    lines = text.split("\n")
    height = (bottom - top) // len(lines)
    for i, line in enumerate(lines):
        line_top = top + height * i
        mask = glyph_mask(line, font, right - left, height - (len(lines) > 1))
        sprite = Image.new("RGBA", mask.size, color)
        sprite.putalpha(mask)
        x = (left + right - sprite.width) // 2
        y = line_top + (height - sprite.height) // 2
        layer.alpha_composite(sprite, (x, y))


def remove_menu_ink(sprite, mask, selected):
    """Reconstruct the glow behind the original lettering from adjacent pixels."""
    pixels = np.array(sprite)
    if selected:
        return restore_selected_glow(pixels, mask)
    retained = (~mask).astype(float)
    # Estimate opacity and color in premultiplied space so the old letters
    # cannot leave a dark fringe in the flattened highlight.
    weights = gaussian_filter(retained, 4)
    alpha = pixels[:, :, 3] / 255
    smooth_alpha = gaussian_filter(alpha * retained, 4)
    restored_alpha = np.divide(smooth_alpha[mask], weights[mask],
                               out=np.zeros(np.count_nonzero(mask)), where=weights[mask] > 0)
    pixels[mask, 3] = np.rint(255 * restored_alpha)
    for channel in range(3):
        color = gaussian_filter(pixels[:, :, channel] * alpha * retained, 4)
        pixels[mask, channel] = np.rint(
            np.divide(color[mask], smooth_alpha[mask],
                      out=np.zeros(np.count_nonzero(mask)), where=smooth_alpha[mask] > 0)
        )
    return Image.fromarray(pixels)


def restore_selected_glow(pixels, mask):
    """Keep the original halo and interpolate it only where ink covered it."""
    alpha = pixels[:, :, 3].astype(float)
    yy, xx = distance_transform_edt(mask, return_distances=False, return_indices=True)
    alpha[mask] = alpha[yy[mask], xx[mask]]
    # Diffusion keeps the original opacity at the boundary and fills the
    # lettering footprint without leaving its silhouette in the highlight.
    kernel = np.array(((0, 1, 0), (1, 0, 1), (0, 1, 0))) / 4
    for _ in range(120):
        alpha[mask] = convolve(alpha, kernel, mode="nearest")[mask]
    pixels[mask, 3] = np.rint(alpha[mask])
    pixels[mask, :3] = (249, 206, 122)
    return Image.fromarray(pixels)


def replace_exit(original, output, font, col):
    # The EXIT label is built into a plate. Replace only the old lettering and
    # its antialiasing by sampling the nearest plate color outside the glyph.
    x = 350 + COLUMN_PITCH * col
    box = (x, 980, x + 95, 1030)
    pixels = np.array(original.crop(box))
    min_green = (14, 16, 63)[col]
    letters = (pixels[:, :, 1] > min_green) & (pixels[:, :, 2] > min_green)
    repair = binary_dilation(letters, iterations=1)
    yy, xx = distance_transform_edt(repair, return_distances=False, return_indices=True)
    pixels[repair, :3] = pixels[yy[repair], xx[repair], :3]
    layer = Image.fromarray(pixels)
    centered_label(layer, "退出\n游戏", font, (8, 2, 87, 46), (191, 173, 146))
    output.paste(layer, box[:2])


def localize(original, font_path):
    output = original.copy()
    font = load_font(str(font_path), 64, "Medium")
    for top, bottom, text in ROWS:
        original_label = np.asarray(original.crop((BASE_X, top, BASE_X + COLUMN_WIDTH, bottom)))
        core = (original_label[:, :, 3] >= 225) & (original_label[:, :, 0] < 157) & (original_label[:, :, 1] < 69)
        ink_y, ink_x = np.where(core)
        bounds = (ink_x.min(), ink_y.min(), ink_x.max() + 1, ink_y.max() + 1)
        # The three states share the same lettering. Include the faint,
        # weathered pixels around the ink in the mask.
        mask = binary_dilation(core, iterations=4)
        for col, color in enumerate(INK):
            x = BASE_X + COLUMN_PITCH * col
            original_sprite = original.crop((x, top, x + COLUMN_WIDTH, bottom))
            layer = remove_menu_ink(original_sprite, mask, selected=(col == 1))
            centered_label(layer, text, font, bounds, color)
            output.paste(layer, (x, top))
    for col in range(3):
        replace_exit(original, output, font, col)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sheet", type=Path, default=ROOT / "work/extract/system/menuchip.png")
    parser.add_argument("--out", type=Path, default=ROOT / "work/ui_out/menuchip.png")
    parser.add_argument("--preview", type=Path)
    parser.add_argument("--font", type=Path, default=FONT)
    args = parser.parse_args()

    with Image.open(args.sheet) as sheet:
        output = localize(sheet.convert("RGBA"), args.font)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    output.save(args.out)
    if args.preview is not None:
        preview = Image.new("RGBA", output.size, (78, 71, 68, 255))
        preview.alpha_composite(output)
        preview.convert("RGB").save(args.preview)


if __name__ == "__main__":
    main()

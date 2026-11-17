"""Check built font atlases against the generated typeface and original private glyphs."""
import argparse
from pathlib import Path
import unicodedata

from PIL import Image
from make_font import fit_fixed_cell, FIXED_METRIC_CELLS

ROOT = Path(__file__).resolve().parent.parent


def verify(directory, generated, original, charset):
    chars = charset.read_text(encoding="utf-8")
    with Image.open(generated) as image:
        generated_image = image.convert("RGBA")
    with Image.open(original) as image:
        original_image = image.convert("RGBA")
    errors = []
    private = sum(unicodedata.category(char) == "Co" for char in chars)
    for name in ("font.png", "font2.png"):
        with Image.open(directory / name) as image:
            actual = image.convert("RGBA")
        if actual.size != generated_image.size:
            raise ValueError(f"{name}: atlas size differs from generated font")
        for index, char in enumerate(chars):
            x, y = index % 64 * 48, index // 64 * 48
            box = (x, y, x + 48, y + 48)
            source = original_image if unicodedata.category(char) == "Co" else generated_image
            expected = source.crop(box)
            if index < FIXED_METRIC_CELLS and unicodedata.category(char) != "Co" and not char.isspace():
                expected = fit_fixed_cell(expected, original_image.crop(box))
            if actual.crop(box).tobytes() != expected.tobytes():
                errors.append(f"{name}:{index}:U+{ord(char):04X}")
            ink_bounds = actual.crop(box).getchannel("A").getbbox()
            old_bounds = original_image.crop(box).getchannel("A").getbbox()
            if (index < FIXED_METRIC_CELLS and unicodedata.category(char) != "Co"
                    and ink_bounds and old_bounds
                    and (ink_bounds[0] < old_bounds[0] or ink_bounds[2] > old_bounds[2])):
                errors.append(f"{name}:{index}:ink outside engine's original horizontal slot")
            if char.isspace() and ink_bounds:
                errors.append(f"{name}:{index}:neighboring ink leaked into whitespace cell")
            if (ink_bounds and not unicodedata.category(char).startswith("C")
                    and (ink_bounds[1] == 0 or ink_bounds[3] == 48)):
                errors.append(f"{name}:{index}:ink touches vertical clipping edge")
            if (not char.isspace() and not unicodedata.category(char).startswith("C")
                    and expected.getchannel("A").getbbox() is None):
                errors.append(f"{name}:{index}:missing glyph U+{ord(char):04X}")
    if errors:
        raise ValueError(f"{len(errors)} font errors; first 20: {', '.join(errors[:20])}")
    print(f"PASS: both atlases, {len(chars) - private} dialogue-font cells, {private} preserved private cells")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=ROOT / "work/system_build")
    parser.add_argument("--generated", type=Path, default=ROOT / "work/fontgen/FONT_A.png")
    parser.add_argument("--original", type=Path, default=ROOT / "font/origin/font.png")
    parser.add_argument("--charset", type=Path, default=ROOT / "work/charset_new.utf8")
    args = parser.parse_args()
    try:
        verify(args.directory, args.generated, args.original, args.charset)
    except ValueError as exc:
        parser.exit(1, f"FAIL: {exc}\n")


if __name__ == "__main__":
    main()

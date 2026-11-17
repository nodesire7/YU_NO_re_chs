"""Check built font atlases against the generated typeface and original private glyphs."""
import argparse
from pathlib import Path
import unicodedata

from PIL import Image

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
            if actual.crop(box).tobytes() != expected.tobytes():
                errors.append(f"{name}:{index}:U+{ord(char):04X}")
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

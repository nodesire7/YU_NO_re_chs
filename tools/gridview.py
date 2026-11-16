#!/usr/bin/env python3
"""Save a crop of an image with a coordinate grid, for reading off UI coordinates.

Usage: python gridview.py --image x.png --crop 0,600,900,1250 --out crop.png [--scale 2]
                         [--bg dark|light|checker]
"""
import argparse
import os

from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--crop", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--step", type=int, default=100)
    ap.add_argument("--bg", default="checker", choices=["dark", "light", "checker"])
    args = ap.parse_args()

    x0, y0, x1, y1 = [int(v) for v in args.crop.split(",")]
    im = Image.open(args.image).convert("RGBA").crop((x0, y0, x1, y1))
    w, h = im.size
    if args.bg == "dark":
        base = Image.new("RGBA", im.size, (24, 24, 24, 255))
    elif args.bg == "light":
        base = Image.new("RGBA", im.size, (240, 240, 240, 255))
    else:
        base = Image.new("RGBA", im.size, (128, 128, 128, 255))
        d0 = ImageDraw.Draw(base)
        for yy in range(0, h, 32):
            for xx in range(0, w, 32):
                if ((xx // 32) + (yy // 32)) % 2 == 0:
                    d0.rectangle([xx, yy, xx + 31, yy + 31], fill=(160, 160, 160, 255))
    base.alpha_composite(im)
    out = base.convert("RGB")
    if args.scale != 1.0:
        out = out.resize((int(w * args.scale), int(h * args.scale)), Image.LANCZOS)
    d = ImageDraw.Draw(out)
    scale = args.scale
    for x in range(0, w, args.step):
        px = int(x * scale)
        d.line([px, 0, px, out.height], fill=(255, 0, 0), width=1)
        d.text((px + 2, 2), str(x + x0), fill=(255, 80, 80))
    for y in range(0, h, args.step):
        py = int(y * scale)
        d.line([0, py, out.width, py], fill=(0, 160, 255), width=1)
        d.text((2, py + 1), str(y + y0), fill=(80, 200, 255))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    out.save(args.out)
    print(out.size, "->", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Translate the small ITEM heading on the message-window sheet (meswin.png).

The heading sits between two decorative squiggles on a dark strip, so the glyph band can
be cleared and redrawn without touching the ornaments.

Usage: python ui_meswin.py [--sheet ...] [--out ...]
"""
import argparse
import json
import os
import subprocess
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "NotoSerifSC-VF.ttf")

# measured: "ITEM" occupies x 975..1045, y 683..715 (between the squiggles)
RECT = [968, 678, 86, 42]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", default=os.path.join(ROOT, "work", "extract", "system", "meswin.png"))
    ap.add_argument("--out", default=os.path.join(ROOT, "work", "ui_out", "meswin.png"))
    ap.add_argument("--preview", default=os.path.join(ROOT, "work", "ui_out", "meswin_preview.png"))
    args = ap.parse_args()

    spec = [
        {"rect": RECT, "clear": True},
        {"rect": RECT, "text": "道具", "font": FONT, "size": 30, "variation": "Bold",
         "color": "#efe9dc", "align": "center", "valign": "center"},
    ]
    spec_path = os.path.join(ROOT, "work", "ui", "meswin_spec.json")
    with open(spec_path, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=1)
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "ui_edit.py"),
                    "--image", args.sheet, "--spec", spec_path, "--out", args.out], check=True)

    im = Image.open(args.out).convert("RGBA")
    bg = Image.new("RGBA", (400, 120), (28, 26, 24, 255))
    bg.alpha_composite(im.crop((880, 650, 1280, 770)))
    bg.convert("RGB").save(args.preview)
    print("meswin ->", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Final pass over the text set: normalise ellipses, parentheses and duplicate punctuation.

Runs after the hand-written patches (patch_jp_lines / patch_ui_lines), which may introduce
a few of these patterns again. Idempotent.

Usage: python final_clean.py [--text work/text_final]
"""
import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REPLACEMENTS = [
    ("‥‥", "……"),
    ("，，", "，"),
    ("。。", "。"),
    ("、。", "。"),
    ("、、", "、"),
    ("。。", "。"),
]


def clean(line: str) -> str:
    for a, b in REPLACEMENTS:
        line = line.replace(a, b)
    line = re.sub(r"（([^（）]{0,80})\)", r"（\1）", line)
    line = re.sub(r"\(([^()]{0,80})）", r"（\1）", line)
    return line


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default=os.path.join(ROOT, "work", "text_final"))
    args = ap.parse_args()
    changed = 0
    for name in sorted(os.listdir(args.text)):
        if not name.endswith(".txt"):
            continue
        path = os.path.join(args.text, name)
        src = open(path, encoding="utf-8", errors="replace").read()
        lines = [clean(l) for l in src.split("\n")]
        out = "\n".join(lines)
        if out != src:
            open(path, "w", encoding="utf-8", newline="\n").write(out)
            changed += 1
    print("final_clean: %d files updated" % changed)
    return 0


if __name__ == "__main__":
    sys.exit(main())

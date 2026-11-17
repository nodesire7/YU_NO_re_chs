#!/usr/bin/env python3
"""Generate the font charset used for packing.

The game addresses glyphs by 2-byte code (0x8000 + index); the font atlas is laid out in
that same order. We keep the first 640 entries of the shipped Japanese charset (ASCII,
punctuation, kana) so their character indices stay compatible, then append every other character
used by the translated script, sorted by frequency.

Usage: python make_charset.py [--text work/text_final] [--out work/charset_new.utf8]
"""
import argparse
import collections
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_HEAD = 640


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default=os.path.join(ROOT, "work", "text_final"))
    ap.add_argument("--base", default=os.path.join(ROOT, "font", "charset.utf8"))
    ap.add_argument("--out", default=os.path.join(ROOT, "work", "charset_new.utf8"))
    args = ap.parse_args()

    text = []
    for name in sorted(os.listdir(args.text)):
        if name.endswith(".txt"):
            text.append(open(os.path.join(args.text, name), encoding="utf-8", errors="replace").read())
    text = "".join(text)
    counts = collections.Counter(text)
    head = open(args.base, encoding="utf-8").read()[:BASE_HEAD]
    added = [c for c in counts if c not in head]
    added.sort(key=lambda c: -counts[c])
    charset = head + "".join(added)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="") as fh:
        fh.write(charset)
    print("charset: %d glyphs (%d unique), %d rows" %
          (len(charset), len(set(charset)), (len(charset) + 63) // 64))
    return 0


if __name__ == "__main__":
    sys.exit(main())

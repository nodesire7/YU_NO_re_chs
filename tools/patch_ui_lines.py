#!/usr/bin/env python3
"""Small wording fixes for the system/UI text (machine-translation leftovers).

Index-based so it stays stable: run after prepare_text.py and patch_jp_lines.py.

Usage: python patch_ui_lines.py [--text work/text_final]
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# file -> {line index: new text}
EXACT = {
    "yns_title.scx.txt": {
        2: "\u3000删除存档",
        30: "\u3000删除",
    },
    "_startup.scx.txt": {
        0: '[color index="A0160000"]消息结束',
    },
    "_system.scx.txt": {
        9: "存档时间",
        22: "结局数",
        36: "文字设置",
    },
}

YESNO_FILES = ("_startup.scx.txt", "_yunosys.scx.txt", "yns_title.scx.txt")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default=os.path.join(ROOT, "work", "text_final"))
    args = ap.parse_args()

    changed = 0
    for name, mapping in EXACT.items():
        path = os.path.join(args.text, name)
        if not os.path.exists(path):
            print("missing", path, file=sys.stderr)
            continue
        lines = open(path, encoding="utf-8", errors="replace").read().split("\n")
        for idx, new in mapping.items():
            if idx < len(lines) and lines[idx] != new:
                lines[idx] = new
                changed += 1
        open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines))

    # はい / いいえ used as confirmation buttons
    for name in YESNO_FILES:
        path = os.path.join(args.text, name)
        if not os.path.exists(path):
            continue
        lines = open(path, encoding="utf-8", errors="replace").read().split("\n")
        touched = False
        for i, line in enumerate(lines):
            if line.strip() == "是啊":
                lines[i] = "是"
                changed += 1
                touched = True
            elif line.strip() == "没关系":
                lines[i] = "否"
                changed += 1
                touched = True
        if touched:
            open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines))

    print("patched %d UI lines" % changed)
    return 0


if __name__ == "__main__":
    sys.exit(main())

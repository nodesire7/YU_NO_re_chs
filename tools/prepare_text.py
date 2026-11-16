#!/usr/bin/env python3
"""Prepare the final Chinese script text set for packing.

Source: alltexts/zh (line-aligned with the Japanese scripts, containing "JF:"/"JF|"
machine-translation markers). Output: work/text_final/<name>.scx.txt with the markers
stripped and a small glossary of recurring mistranslations applied.

Usage: python prepare_text.py [--src alltexts/zh] [--out work/text_final]
"""
import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Order matters: longer/more specific patterns first.
GLOSSARY = [
    # system / UI wording produced by machine translation
    ("Xinput规格焊盘为字母表示。", "XInput 规格按键以字母显示。"),
    ("Xinput规格焊盘", "XInput 规格按键"),
    ("游戏垫", "游戏手柄"),
    ("游戏板", "游戏手柄"),
    ("焊盘", "按键"),
    ("嗯－指针", "嗯—指针"),
    ("亚由美不在……走错了吗？", "亚由美不在……是我走错了吗？"),
    ("大能力生理学", "超能力生理学"),
    ("网子", "网子"),
    ("老头子", "老爸"),
    ("没有在这里", "不在这里"),
    ("的房子那里", "的宅邸"),
    ("不加载", "不读取"),
    # keep full-width punctuation consistent
    ("…….", "……"),
]


def clean_line(line: str) -> str:
    # strip machine-translation markers wherever they appear
    line = line.replace("JF|", "").replace("JF:", "")
    for a, b in GLOSSARY:
        line = line.replace(a, b)
    # duplicated punctuation produced by the machine translation
    line = line.replace("，，", "，").replace("。。", "。").replace("、。", "。")
    # doubled characters that are always typos in context
    for a, b in (("是是理成", "是理成"), ("那是是锁上", "那是锁上"),
                 ("是是。那么", "是。那么"), ("的的灯", "的灯")):
        line = line.replace(a, b)
    return line


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=os.path.join(ROOT, "alltexts", "zh"))
    ap.add_argument("--out", default=os.path.join(ROOT, "work", "text_final"))
    ap.add_argument("--report", default=os.path.join(ROOT, "work", "text_report.txt"))
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    n_files = n_lines = n_markers = 0
    report = []
    for name in sorted(os.listdir(args.src)):
        if not name.endswith(".txt"):
            continue
        src = os.path.join(args.src, name)
        raw = open(src, encoding="utf-8", errors="replace").read()
        n_markers += raw.count("JF:") + raw.count("JF|")
        lines = [clean_line(l) for l in raw.split("\n")]
        open(os.path.join(args.out, name), "w", encoding="utf-8", newline="\n").write("\n".join(lines))
        n_files += 1
        n_lines += len(lines)
        leftover = [l for l in lines if "JF:" in l or "JF|" in l]
        if leftover:
            report.append("%s: %d leftover markers" % (name, len(leftover)))

    with open(args.report, "w", encoding="utf-8") as fh:
        fh.write("files=%d lines=%d stripped_markers=%d\n" % (n_files, n_lines, n_markers))
        fh.write("\n".join(report))
    print("wrote %d files, %d lines, stripped %d markers -> %s" % (n_files, n_lines, n_markers, args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())

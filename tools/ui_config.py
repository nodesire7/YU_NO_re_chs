#!/usr/bin/env python3
"""Translate the labels in the config screen sheet (config.png).

The label column uses white glyphs on transparent background, so the rows are found with
a brightness/alpha profile and then replaced with Chinese text of the same size.

Usage: python ui_config.py [--sheet ...] [--out ...]
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "NotoSerifSC-VF.ttf")

TEXTS = [
    ("信息", True),
    ("声音", True),
    ("其他设置", True),
    ("文本显示速度", False),
    ("自动模式推进速度", False),
    ("保持自动模式", False),
    ("跳过模式的对象", False),
    ("保持跳过模式", False),
    ("语音与文本同步", False),
    ("BGM 设定", False),
    ("跳过语音", False),
    (None, False),            # BGM - already latin
    ("音效", False),
    ("系统音效", False),
    ("角色语音", False),
    ("提示功能", False),
    ("面板答案显示", False),
    ("手柄按键显示", False),
    ("全屏切换", False),
    ("画质", False),
]


def detect_rows(im, x0=1920, x1=2230, y0=1080, y1=2050):
    a = np.array(im)
    al = a[:, :, 3].astype(int)
    lum = a[:, :, :3].mean(2)
    m = (al > 60) & (lum > 150)
    sub = m[y0:y1, x0:x1]
    prof = sub.sum(1)
    rows = []
    start = None
    for i, v in enumerate(prof):
        if v > 2 and start is None:
            start = i
        elif v <= 2 and start is not None:
            if i - start >= 6:
                rows.append((y0 + start, y0 + i - 1))
            start = None
    if start is not None and len(prof) - start >= 6:
        rows.append((y0 + start, y0 + len(prof) - 1))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", default=os.path.join(ROOT, "work", "extract", "system", "config.png"))
    ap.add_argument("--out", default=os.path.join(ROOT, "work", "ui_out", "config.png"))
    ap.add_argument("--preview", default=os.path.join(ROOT, "work", "ui_out", "config_preview.png"))
    args = ap.parse_args()

    im = Image.open(args.sheet).convert("RGBA")
    rows = detect_rows(im)
    if len(rows) < len(TEXTS):
        print("warning: only %d label rows detected" % len(rows), file=sys.stderr)

    spec = []
    for (y0, y1), (text, is_header) in zip(rows, TEXTS):
        if not text:
            continue
        h = y1 - y0 + 1
        spec.append({
            "rect": [1893, y0 - 5, 520, h + 10],
            "clear": True,
        })
        spec.append({
            "rect": [1952, y0 - 4, 400, h + 8],
            "text": text,
            "font": FONT,
            "size": 33 if is_header else max(22, min(28, int(h * 0.95))),
            "variation": "Bold",
            "color": "#eae5d7",
            "align": "left",
            "valign": "center",
            "dx": 0,
        })
    # cast / voice-test name column (x 2430-2660, 16 rows, ~48px pitch)
    names = ["有马拓也", "有马亚由美", "一条美月", "武田绘里子", "结城正胜", "岛津澪",
             "波多乃神奈", "朝仓香织", "龙藏寺幸三", "丰富秀夫", "优诺", "阿曼达",
             "塞蕾丝", "其他（男性）", "其他（女性）", "北条笃"]
    centers = [1218, 1265, 1313, 1362, 1410, 1458, 1506, 1554, 1602, 1650,
               1698, 1745, 1793, 1841, 1889, 1937]
    for cy, name in zip(centers, names):
        spec.append({"rect": [2425, cy - 22, 265, 44], "clear": True})
        spec.append({"rect": [2432, cy - 20, 250, 42], "text": name, "font": FONT, "size": 30,
                     "variation": "Bold", "color": "#f2efe6", "align": "left",
                     "valign": "center", "dx": 0, "stroke_width": 1, "stroke_fill": "#14110c"})

    # section subtitles drawn after the decorative squiggles
    for y, text in ((1088, "文本设定"), (1124, "声音设定"), (1160, "其他设定")):
        spec.append({"rect": [2436, y - 4, 460, 40], "clear": True})
        spec.append({"rect": [2444, y - 4, 440, 40], "text": text, "font": FONT, "size": 26,
                     "variation": "Bold", "color": "#d9d3c4", "align": "left",
                     "valign": "center", "dx": 0})
    spec_path = os.path.join(ROOT, "work", "ui", "config_spec.json")
    with open(spec_path, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=1)
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "ui_edit.py"),
                    "--image", args.sheet, "--spec", spec_path, "--out", args.out], check=True)

    out = Image.open(args.out).convert("RGBA")
    bg = Image.new("RGBA", (700, 700), (30, 28, 26, 255))
    bg.alpha_composite(out.crop((1860, 1080, 2560, 1780)))
    bg.convert("RGB").save(args.preview)
    print("config -> %s (%d rows)" % (args.out, len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

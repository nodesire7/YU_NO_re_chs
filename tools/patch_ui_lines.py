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
    "yns_01.scx.txt": {
        4: "[name]拓也[line]空无一人的家里，只剩我一个人吗……。[%p]",
        5: "[name]拓也[line]算了，也不是会为这种事消沉的年纪了。怎么办？[%p]",
        6: "[name]拓也[line]呼……回到自己的房间了。[%p]",
        10: "[name]拓也[line]……这是我的房间啊。[%p]",
    },
    "_startup.scx.txt": {
        0: '[color index="A0160000"]消息结束',
    },
    "_system.scx.txt": {
        9: "存档时间",
        22: "结局数",
        36: "文字设置",
        40: "自动模式推进速度",
        45: "音效",
        46: "系统音效",
        47: "提示功能",
        50: "全部",
        51: "快",
        52: "普通",
        53: "慢",
        54: "开启",
        55: "关闭",
        57: "全部",
        58: "有",
        59: "无",
        62: "设置是否在选项或未读消息到达时",
        63: "保持自动模式。",
        64: "设置跳过模式时要跳过的",
        65: "消息对象。",
        66: "设置是否在选项或未读消息到达时",
        67: "保持跳过模式。",
        73: "设置是否使用屏幕",
        74: "（触摸屏）。",
        145: "L肩键",
        146: "R肩键",
        147: "返回键",
        148: "开始键",
        149: "L摇杆按键",
        150: "R摇杆按键",
        151: "L扳机",
        152: "R扳机",
        180: "亚由美和龙藏寺……还有神奈酱去哪里了",
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

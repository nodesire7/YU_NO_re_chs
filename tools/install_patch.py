#!/usr/bin/env python3
"""Install the built patch into the game folder, keeping a rollback backup.

Usage: python tools/install_patch.py --game <dir> [--scrchs ...] [--syschs ...] [--manual ...] [--patch ...]
"""
import argparse
import os
import shutil
import sys

BACKUP = "_backup_cht"


def backup(game, rel):
    src = os.path.join(game, rel)
    if not os.path.exists(src):
        return
    dst_dir = os.path.join(game, BACKUP)
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, os.path.basename(rel))
    if not os.path.exists(dst):
        shutil.copy2(src, dst)
        print("backup", rel, "->", dst)


def install(game, src, rel):
    if not src or not os.path.exists(src):
        print("skip missing", rel, file=sys.stderr)
        return
    dst = os.path.join(game, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    print("installed", rel)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", required=True)
    ap.add_argument("--scrchs", default=None)
    ap.add_argument("--syschs", default=None)
    ap.add_argument("--manual", default=None)
    ap.add_argument("--patch", default=None)
    args = ap.parse_args()

    if args.manual:
        if not os.path.isfile(args.manual):
            ap.error("manual archive does not exist: " + args.manual)
        backup(args.game, "data/manual.cpk")
    for rel in ("data/scrchs.cpk", "data/syschs.cpk", "patch.dll"):
        backup(args.game, rel)
    install(args.game, args.scrchs, "data/scrchs.cpk")
    install(args.game, args.syschs, "data/syschs.cpk")
    install(args.game, args.patch, "patch.dll")
    if args.manual:
        install(args.game, args.manual, "data/manual.cpk")
    print("done. rollback files are in", os.path.join(args.game, BACKUP))
    return 0


if __name__ == "__main__":
    sys.exit(main())

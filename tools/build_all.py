#!/usr/bin/env python3
"""One-shot build of the Chinese patch assets.

Steps (idempotent, re-runnable):
  1. clean the translated text (strip machine-translation markers)
  2. build the font charset from the final text
  3. generate the bitmap font atlas and merge it with the original ASCII rows
  4. encode every .scx with the Chinese text
  5. pack data/scrchs.cpk and data/syschs.cpk using the original archives as ID reference
  6. optionally install into the game folder (with backups)

Requirements:
  * pack/sc3tools-main_pack  : cargo build --release   (script encoder)
  * pack/sc3tools-decode     : cargo build --release   (script text extractor, verification)
  * pack/mgsfontgen-dx-master: dotnet build -c Release (font atlas generator)
  * pack/crifilesystem v2.40.13.0/cpkmakec.exe         (CPK packer, shipped in repo)

Usage:
  python tools/build_all.py [--game F:\\game\\steam\\steamapps\\common\\YU-NO] [--install]
"""
import argparse
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COPY = shutil.copy2


def run(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True, **kw)


def rust_bin(crate):
    exe = os.path.join(ROOT, "pack", crate, "target", "release", "sc3tools.exe")
    if not os.path.exists(exe):
        raise SystemExit("missing %s (run: cargo build --release in pack/%s)" % (exe, crate))
    return exe


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default=r"F:\game\steam\steamapps\common\YU-NO")
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--font-family", default="Noto Serif SC")
    args = ap.parse_args()

    work = os.path.join(ROOT, "work")
    text_final = os.path.join(work, "text_final")
    script_dir = os.path.join(work, "extract", "script")
    build_dir = os.path.join(work, "script_build")
    system_src = os.path.join(work, "extract", "system")
    system_build = os.path.join(work, "system_build")
    ui_out = os.path.join(work, "ui_out")
    patch_out = os.path.join(work, "patch_build", "patch.dll")
    out = os.path.join(work, "out")
    os.makedirs(out, exist_ok=True)

    # 1. text
    run([sys.executable, os.path.join(ROOT, "tools", "prepare_text.py")])

    # 1b. fill in the lines that are still Japanese (zz.scx monologue etc.)
    run([sys.executable, os.path.join(ROOT, "tools", "patch_jp_lines.py")])
    run([sys.executable, os.path.join(ROOT, "tools", "patch_ui_lines.py")])

    # 2. charset
    charset = os.path.join(work, "charset_new.utf8")
    run([sys.executable, os.path.join(ROOT, "tools", "make_charset.py")])
    COPY(charset, os.path.join(ROOT, "pack", "sc3tools-main_pack", "resources", "yuno", "charset.utf8"))
    COPY(charset, os.path.join(ROOT, "pack", "sc3tools-decode", "resources", "yuno", "charset.utf8"))
    for crate in ("sc3tools-main_pack", "sc3tools-decode"):
        run(["cargo", "build", "--release"], cwd=os.path.join(ROOT, "pack", crate))

    # 3. font
    fontgen = os.path.join(ROOT, "pack", "mgsfontgen-dx-master", "bin", "Release", "net461", "mgsfontgen-dx.exe")
    fontdir = os.path.join(work, "fontgen")
    os.makedirs(fontdir, exist_ok=True)
    run([fontgen, "generate",
         "--charset", charset,
         "--compound-characters", os.path.join(ROOT, "font", "compound_chars.map"),
         "--font-family", args.font_family, "--image-format", "png"], cwd=fontdir)
    run([sys.executable, os.path.join(ROOT, "tools", "make_font.py"),
         "--generated", os.path.join(fontdir, "FONT_A.png"),
         "--original", os.path.join(ROOT, "font", "origin", "font.png"),
         "--outdir", system_build])

    # 4. encode scripts
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    shutil.copytree(script_dir, build_dir, ignore=shutil.ignore_patterns("txt"))
    run([rust_bin("sc3tools-main_pack"), "replace-text",
         os.path.join(build_dir, "*.scx"), os.path.join(text_final, "*.txt"), "yuno"])

    # 5. CPKs
    scrchs = os.path.join(out, "scrchs.cpk")
    run([sys.executable, os.path.join(ROOT, "tools", "build_cpk.py"),
         "--reference", os.path.join(work, "ref", "scrchs.cpk"),
         "--src", build_dir, "--out", scrchs])
    if os.path.isdir(ui_out):
        for name in os.listdir(ui_out):
            if name.endswith(".png") and os.path.exists(os.path.join(system_src, name)):
                COPY(os.path.join(ui_out, name), os.path.join(system_build, name))
    syschs = os.path.join(out, "syschs.cpk")
    run([sys.executable, os.path.join(ROOT, "tools", "build_cpk.py"),
         "--reference", os.path.join(work, "ref", "syschs.cpk"),
         "--src", system_build, "--out", syschs])

    # 6. install
    if args.install:
        run([sys.executable, os.path.join(ROOT, "tools", "install_patch.py"),
             "--game", args.game, "--scrchs", scrchs, "--syschs", syschs, "--patch", patch_out])
    print("done:", scrchs, syschs)
    return 0


if __name__ == "__main__":
    sys.exit(main())

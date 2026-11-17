#!/usr/bin/env python3
"""One-shot build of the Chinese patch assets.

Steps (idempotent, re-runnable):
  1. clean the translated text (strip machine-translation markers)
  2. build the font charset from the final text
  3. generate all text glyphs in one font and retain original private-use glyphs
  4. encode every .scx with the Chinese text
  5. regenerate the title, menu and settings sprites, and manuals, then pack the CPKs
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
import tempfile

from build_cpk import CPKMAKEC
from install_patch import BACKUP
from localize_text import prepare

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


def build_manual(game, work, out):
    reference = os.path.join(work, "ref", "manual.cpk")
    if not os.path.isfile(reference):
        # An existing installation may already contain the translated manual.
        backup = os.path.join(game, BACKUP, "manual.cpk")
        original = backup if os.path.isfile(backup) else os.path.join(game, "data", "manual.cpk")
        COPY(original, reference)

    source = os.path.join(work, "extract", "manual")
    staging = os.path.join(work, "manual_build")
    os.makedirs(source, exist_ok=True)
    run([CPKMAKEC, reference, "-extract=" + source, "-noerrorstop"])
    run([sys.executable, os.path.join(ROOT, "tools", "ui_manual.py"),
         "--source", source, "--out", staging])
    manual = os.path.join(out, "manual.cpk")
    run([sys.executable, os.path.join(ROOT, "tools", "build_cpk.py"),
         "--reference", reference, "--src", staging, "--out", manual])
    return manual


def verify_manuscript_archive(archive, text_dir):
    width_map = str.maketrans({**{code: code - 0xFEE0 for code in range(0xFF01, 0xFF5F)}, 0x3000: 0x20})
    with tempfile.TemporaryDirectory() as directory:
        run([CPKMAKEC, archive, "-extract=" + directory, "-noerrorstop"])
        run([rust_bin("sc3tools-decode"), "extract-text", os.path.join(directory, "*.scx"), "yuno"])
        decoded = {name for name in os.listdir(os.path.join(directory, "txt")) if name.endswith(".scx.txt")}
        expected = {name for name in os.listdir(text_dir) if name.endswith(".scx.txt")}
        if decoded != expected:
            raise ValueError("编译后的脚本文本文件与译稿不一致")
        for name in sorted(expected):
            with open(os.path.join(text_dir, name), encoding="utf-8") as source:
                source_lines = source.read().translate(width_map).splitlines()
            with open(os.path.join(directory, "txt", name), encoding="utf-8") as result:
                result_lines = result.read().translate(width_map).splitlines()
            if source_lines != result_lines:
                raise ValueError(f"解包回读与译稿不一致：{name}")
    print(f"解包回读通过，共 {len(expected)} 个脚本。")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default=r"F:\game\steam\steamapps\common\YU-NO")
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--font-family", default="LXGW WenKai")
    ap.add_argument("--localization", default=os.path.join(ROOT, "localization"),
                    help="从已校完的整份中日对照译稿批量构建（默认 localization）")
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

    if args.localization:
        text_final = os.path.join(work, "localization_zh")
        manuscript_script = os.path.join(args.localization, "original_scx")
        if os.path.isdir(manuscript_script):
            script_dir = manuscript_script
        elif not os.path.isdir(script_dir):
            os.makedirs(script_dir, exist_ok=True)
            run([CPKMAKEC, os.path.join(args.game, "data", "script.cpk"),
                 "-extract=" + script_dir, "-noerrorstop"])
        try:
            prepare(args.localization, text_final)
        except ValueError as exc:
            ap.error(str(exc))
    else:
        run([sys.executable, os.path.join(ROOT, "tools", "prepare_text.py")])
        run([sys.executable, os.path.join(ROOT, "tools", "patch_jp_lines.py")])
        run([sys.executable, os.path.join(ROOT, "tools", "patch_ui_lines.py")])
        run([sys.executable, os.path.join(ROOT, "tools", "final_clean.py")])

    # 2. charset
    charset = os.path.join(work, "charset_new.utf8")
    run([sys.executable, os.path.join(ROOT, "tools", "make_charset.py"), "--text", text_final])
    COPY(charset, os.path.join(ROOT, "pack", "sc3tools-main_pack", "resources", "yuno", "charset.utf8"))
    COPY(charset, os.path.join(ROOT, "pack", "sc3tools-decode", "resources", "yuno", "charset.utf8"))
    for crate in ("sc3tools-main_pack", "sc3tools-decode"):
        crate_dir = os.path.join(ROOT, "pack", crate)
        run(["cargo", "build", "--release", "--target-dir", os.path.join(crate_dir, "target")], cwd=crate_dir)

    # 3. font
    run(["dotnet", "build", os.path.join(ROOT, "pack", "mgsfontgen-dx-master", "src", "MgsFontGenDX.csproj"),
         "-c", "Release"])
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
         "--charset", charset,
         "--outdir", system_build])
    run([sys.executable, os.path.join(ROOT, "tools", "verify_font.py"),
         "--directory", system_build, "--generated", os.path.join(fontdir, "FONT_A.png"),
         "--charset", charset])

    # 4. encode scripts
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    shutil.copytree(script_dir, build_dir, ignore=shutil.ignore_patterns("txt"))
    run([rust_bin("sc3tools-main_pack"), "replace-text",
         os.path.join(build_dir, "*.scx"), os.path.join(text_final, "*.txt"), "yuno"])

    # 5. Regenerate the menu atlases from the extracted original textures.
    for tool in ("ui_config.py", "ui_menu.py", "ui_title.py"):
        run([sys.executable, os.path.join(ROOT, "tools", tool)])

    run([sys.executable, os.path.join(ROOT, "tools", "ui_help.py"),
         "--recon-dir", os.path.join(work, "ui", "help_check")])
    run([sys.executable, os.path.join(ROOT, "tools", "ui_guide.py")])

    # Preserve the reference archive IDs when packing the rebuilt files.
    scrchs = os.path.join(out, "scrchs.cpk")
    run([sys.executable, os.path.join(ROOT, "tools", "build_cpk.py"),
         "--reference", os.path.join(work, "ref", "scrchs.cpk"),
         "--src", build_dir, "--out", scrchs])
    if args.localization:
        verify_manuscript_archive(scrchs, text_final)
    if os.path.isdir(ui_out):
        for name in os.listdir(ui_out):
            if name.endswith(".png") and os.path.exists(os.path.join(system_src, name)):
                COPY(os.path.join(ui_out, name), os.path.join(system_build, name))
    syschs = os.path.join(out, "syschs.cpk")
    run([sys.executable, os.path.join(ROOT, "tools", "build_cpk.py"),
         "--reference", os.path.join(work, "ref", "syschs.cpk"),
         "--src", system_build, "--out", syschs])

    manual = build_manual(args.game, work, out)

    # 6. install
    if args.install:
        run([sys.executable, os.path.join(ROOT, "tools", "install_patch.py"),
             "--game", args.game, "--scrchs", scrchs, "--syschs", syschs, "--manual", manual, "--patch", patch_out])
    print("done:", scrchs, syschs, manual)
    return 0


if __name__ == "__main__":
    sys.exit(main())

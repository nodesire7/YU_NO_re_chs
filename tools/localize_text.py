#!/usr/bin/env python3
"""Export the original script and a Chinese manuscript, then validate it for a batch build."""
import argparse
import json
from pathlib import Path
import re
from subprocess import run

from build_cpk import CPKMAKEC
from final_clean import clean
from prepare_text import clean_line

ROOT = Path(__file__).resolve().parent.parent
GAME = Path(r"F:\game\steam\steamapps\common\YU-NO")
MANUSCRIPT = "中日对照.jsonl"
MACHINE_MARK = re.compile(r"JF[:|]")
CONTROLS = re.compile(
    r"\[(?:name|line|linebreak|alt-linebreak|center|parallel|"
    r"ruby-?(?:base|text-?start|text-?end)|ruby-center-per-char|"
    r"auto-?forward(?:-1a)?|%p|%e|%05|%18|"
    r"(?:color|margin|font|hardcoded-?value|evaluate) [^\]]+|[A-Z][A-Z0-9_]*)\]"
    r"|:[a-zA-Z][a-zA-Z0-9_]*:"
)


def text_files(directory):
    files = {path.name: path for path in directory.glob("*.scx.txt")}
    if not files:
        raise ValueError(f"没有找到脚本文本：{directory}")
    return files


def read_lines(path):
    return path.read_text(encoding="utf-8").splitlines()


def extract(args):
    out = args.out.resolve()
    manuscript = out / MANUSCRIPT
    if manuscript.exists():
        raise ValueError(f"已存在译稿，请为新的提取指定目录：{manuscript}")
    original = out / "original_scx"
    out.mkdir(parents=True, exist_ok=True)
    crate = ROOT / "pack/sc3tools-main"
    decoder = crate / "target/release/sc3tools.exe"
    if not decoder.is_file():
        run(["cargo", "build", "--release", "--target-dir", str(crate / "target")], cwd=crate, check=True)
    run([CPKMAKEC, str(args.game / "data/script.cpk"), f"-extract={original}", "-noerrorstop"], check=True)
    run([str(decoder), "extract-text", str(original / "*.scx"), "yuno"], check=True)
    ja = text_files(original / "txt")
    zh = text_files(args.chinese)
    raw = text_files(ROOT / "alltexts/zh")
    if ja.keys() != zh.keys() or ja.keys() != raw.keys():
        raise ValueError("原版脚本、现有译文和校对标记的文件名不一致")
    reviewed = {}
    for path in args.reviewed:
        for entry in read_lines(path):
            row = json.loads(entry)
            key = (row["file"], row["line"])
            if key in reviewed:
                raise ValueError(f"重复的校对记录：{key}")
            reviewed[key] = row
    draft = []
    baseline_dir = out / "baseline_zh"
    baseline_dir.mkdir(exist_ok=True)
    for name in sorted(ja):
        source = read_lines(ja[name])
        baseline = zh[name].read_text(encoding="utf-8")
        marked = read_lines(raw[name])
        for index, (original_line, current, raw_line) in enumerate(
            zip(source, baseline.splitlines(), marked, strict=True), 1
        ):
            pending = bool(MACHINE_MARK.search(raw_line))
            rec = reviewed.pop((name, index), None)
            if rec:
                if not pending or rec["ja"] != original_line or rec["zh"] != raw_line:
                    raise ValueError(f"校对记录和原文不一致：{name}:{index}")
                current = clean(clean_line(rec["new"]))
                pending = False
            draft.append(dict(file=name, line=index, ja=original_line, zh=current, pending=pending))
        (baseline_dir / name).write_text(baseline, encoding="utf-8", newline="\n")
    if reviewed:
        raise ValueError(f"找不到对应脚本的校对记录：{next(iter(reviewed))}")
    with manuscript.open("x", encoding="utf-8", newline="\n") as stream:
        for row in draft:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"已提取 {len(ja)} 个脚本，共 {len(draft)} 行。待校 {sum(row['pending'] for row in draft)} 行。")
    print(manuscript)


def prepare(localization, output, allow_draft=False):
    localization = Path(localization)
    output = Path(output)
    source_dir = localization / "original_scx/txt"
    baseline_dir = localization / "baseline_zh"
    source = text_files(source_dir if source_dir.is_dir() else ROOT / "alltexts/ja")
    baseline = text_files(baseline_dir if baseline_dir.is_dir() else ROOT / "alltexts/zh")
    if source.keys() != baseline.keys():
        raise ValueError("译稿基准与原版脚本的文件名不一致")
    texts = {name: [] for name in source}
    expected = {name: read_lines(path) for name, path in source.items()}
    baseline_text = {name: path.read_text(encoding="utf-8") for name, path in baseline.items()}
    previous = {name: text.splitlines() for name, text in baseline_text.items()}
    for name in expected:
        if len(expected[name]) != len(previous[name]):
            raise ValueError(f"译稿基准与原版脚本的行数不一致：{name}")
    pending_count = 0
    with (localization / MANUSCRIPT).open(encoding="utf-8") as stream:
        for record_number, line in enumerate(stream, 1):
            row = json.loads(line)
            name = row["file"]
            index = row["line"]
            if name not in texts or type(index) is not int or index != len(texts[name]) + 1:
                raise ValueError(f"第 {record_number} 条记录的文件名或行号不正确")
            if index > len(expected[name]) or row["ja"] != expected[name][index - 1]:
                raise ValueError(f"译稿里的原文与提取文件不一致：{name}:{index}")
            zh = row["zh"]
            old = previous[name][index - 1]
            if not isinstance(zh, str) or zh.splitlines() not in ([], [zh]) or MACHINE_MARK.search(zh):
                raise ValueError(f"译文包含多行或机翻标记：{name}:{index}")
            if CONTROLS.findall(old) != CONTROLS.findall(zh):
                raise ValueError(f"控制标签或变量发生变化：{name}:{index}")
            if CONTROLS.sub("", old).strip() and not CONTROLS.sub("", zh).strip():
                raise ValueError(f"原有译文被清空：{name}:{index}")
            if type(row["pending"]) is not bool:
                raise ValueError(f"待校状态应为 true 或 false：{name}:{index}")
            pending_count += row["pending"]
            texts[name].append(zh)
    for name, lines in texts.items():
        if len(lines) != len(expected[name]):
            raise ValueError(f"译稿缺行：{name}，应有 {len(expected[name])} 行")
    if pending_count and not allow_draft:
        raise ValueError(f"译稿仍有 {pending_count} 行待校。完成校对后再运行整批打包。")

    if output.exists() and set(p.name for p in output.glob("*.txt")) - texts.keys():
        raise ValueError(f"输出目录包含无关文本：{output}")
    output.mkdir(parents=True, exist_ok=True)
    for name, lines in texts.items():
        tail = "\n" if baseline_text[name].endswith("\n") else ""
        (output / name).write_text("\n".join(lines) + tail, encoding="utf-8", newline="\n")
    print(f"整批验证通过，共 {len(texts)} 个文件、{sum(map(len, texts.values()))} 行，待校 {pending_count} 行。")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("extract", help="从原版 CPK 提取日文并建立中日对照稿")
    export.add_argument("--game", type=Path, default=GAME)
    export.add_argument("--chinese", type=Path, default=ROOT / "work/text_final")
    export.add_argument("--out", type=Path, required=True)
    export.add_argument("--reviewed", action="append", type=Path, default=[])
    validate = sub.add_parser("prepare", help="校验整份译稿并导出脚本编码输入")
    validate.add_argument("--localization", type=Path, required=True)
    validate.add_argument("--out", type=Path, required=True)
    validate.add_argument("--draft", action="store_true", help="仅输出未完稿供阅读和校对")
    args = parser.parse_args()
    try:
        if args.command == "extract":
            extract(args)
        else:
            prepare(args.localization, args.out, allow_draft=args.draft)
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()

"""Audit every manuscript row; emit source-linked display risks, not a simulated engine pass."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from localize_text import CONTROLS, MANUSCRIPT, ROOT, read_lines

VARIABLE = re.compile(r":[a-zA-Z][a-zA-Z0-9_]*:")
BREAK = re.compile(r"\[(?:alt-)?linebreak\]")


def visible(text):
    return CONTROLS.sub("", text)


def map_text(text, transform):
    """Transform literal spans only, retaining tags and case-sensitive engine variables."""
    chunks, offset = [], 0
    for match in CONTROLS.finditer(text):
        chunks.extend((transform(text[offset:match.start()]), match.group()))
        offset = match.end()
    chunks.append(transform(text[offset:]))
    return "".join(chunks)


def audit(path, baseline=None):
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    source = {p.name: read_lines(p) for p in (ROOT / "alltexts/ja").glob("*.scx.txt")}
    base = {(r['file'], r['line']): r for r in baseline} if baseline is not None else None
    counts = Counter()
    issues, long_rows, layouts, metadata, quotations, address_changes = [], [], [], [], [], []
    for row in rows:
        key = row['file'], row['line']
        counts[row['file']] += 1
        ja, zh = row['ja'], row['zh']
        flags = []
        if key[0] not in source or key[1] != counts[key[0]] or key[1] > len(source[key[0]]) or source[key[0]][key[1]-1] != ja:
            flags.append('original_or_index_mismatch')
        if base is not None and (key not in base or CONTROLS.findall(base[key]['zh']) != CONTROLS.findall(zh)):
            flags.append('controls_changed')
        if Counter(VARIABLE.findall(ja)) != Counter(VARIABLE.findall(zh)):
            flags.append('source_variable_mismatch')
        if '\n' in zh or '\r' in zh or '\ufffd' in zh or re.search(r'JF[:|]', zh):
            flags.append('invalid_text')
        body = zh.split('[line]', 1)[-1]
        text = visible(body)
        dialogue = '[line]' in zh
        # System rows 1/2 are original line-breaking tables, not displayed prose.
        is_metadata = (key[0] == '_system.scx.txt' and key[1] in (1, 2)) or (
            key[0] == '_tips.scx.txt' and ja == zh and (
                key[1] in (6, 11) or (14 <= key[1] <= 1040 and key[1] % 5 in (4, 0))))
        # These seven dictionary definitions explain Japanese spellings/examples.
        retained_example = key[0] == '_tips.scx.txt' and key[1] in (156, 201, 271, 581, 876, 966, 1026)
        if is_metadata:
            metadata.append(list(key))
        elif retained_example:
            quotations.append(list(key))
        elif re.search(r'[\u3040-\u30ff]', text):
            flags.append('kana_remaining')
        if dialogue and re.search(r'[ \u3000]{4,}', text):
            flags.append('dialogue_whitespace_run')
        if not is_metadata and re.search(r'，。|。，', text):
            flags.append('comma_full_stop_collision')
        if dialogue:
            speaker = visible(zh.partition('[line]')[0]).strip()
            if speaker and text.startswith((speaker + '：', speaker + ':')):
                flags.append('speaker_repeated_in_dialogue')
            if '絵里子先生' in ja and '绘里子先生' in text:
                flags.append('eriko_teacher_title')
            if '神奈チャン' in ja and re.search(r'神奈[·・ ]*[张張昌陈]', text):
                flags.append('kana_honorific_misread_as_name')
        if dialogue and base is not None and key in base:
            original_translation = base[key]['zh'].partition('[line]')[2]
            for surname in ('岛津', '有马'):
                if surname + '先生' in text and any(surname + title in original_translation
                                                  for title in ('同学', '女士', '夫人', '太太', '小姐', '主任')):
                    address_changes.append(dict(file=key[0], line=key[1], ja=ja, before=original_translation, after=text))
                    break
        if dialogue and re.search(r'[,，][!?！？。]', text):
            flags.append('comma_before_sentence_ending')
        if not is_metadata and '‥' in text:
            flags.append('two_dot_leader_in_translation')
        if dialogue and re.search(r'[!?()]', text) and not re.search(r'[A-Za-zＡ-Ｚａ-ｚ]', text):
            flags.append('mixed_dialogue_punctuation')
        if dialogue and re.fullmatch(r'（[^（）]+）。', text):
            original_body = visible(ja.split('[line]', 1)[-1])
            if '[line]' in ja and not re.search(r'[（(「『《]', original_body):
                flags.append('added_dialogue_parentheses')
        if not visible(zh).strip() and visible(ja).strip():
            flags.append('empty_translation')
        ref = dict(file=key[0], line=key[1], ja=ja, zh=zh)
        if flags:
            issues.append(dict(**ref, flags=flags))
        if dialogue and len(text) >= 45:
            long_rows.append(dict(**ref, visible_characters=len(text)))
        if '[margin ' in zh or BREAK.search(zh):
            layouts.append(dict(**ref, explicit_breaks=len(BREAK.findall(zh)), dialogue=dialogue))
    missing = {name: len(lines)-counts[name] for name, lines in source.items() if len(lines) != counts[name]}
    return dict(manuscript_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                rows=len(rows), scripts=len(source), nonempty_scripts=len(counts), dialogue_rows=sum('[line]' in r['zh'] for r in rows),
                pending_flags=sum(r['pending'] for r in rows), missing=missing,
                issue_counts=dict(Counter(flag for row in issues for flag in row['flags'])),
                issues=issues, long_dialogue=sorted(long_rows, key=lambda r: -r['visible_characters']),
                changed_forms_of_address=address_changes, explicit_layout=layouts, original_metadata=metadata, retained_japanese_examples=quotations,
                limitation='Length is a review priority, not an engine width simulation. Static checks do not certify all routes or semantic accuracy.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manuscript', type=Path, default=ROOT / 'localization' / MANUSCRIPT)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--out', type=Path, default=ROOT / 'work/display_audit/report.json')
    args = parser.parse_args()
    baseline = [json.loads(x) for x in args.baseline.read_text(encoding='utf-8').splitlines()] if args.baseline else None
    report = audit(args.manuscript, baseline)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v if not isinstance(v,list) else len(v) for k, v in report.items() if k not in ('issues','long_dialogue','explicit_layout')}, ensure_ascii=False))
    return int(bool(report['issues'] or report['missing']))


if __name__ == '__main__':
    raise SystemExit(main())

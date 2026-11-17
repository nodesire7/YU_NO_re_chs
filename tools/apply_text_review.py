"""Apply a source-checked JSONL review atomically; repeated application is a no-op."""
import argparse
import json
from pathlib import Path
from localize_text import CONTROLS, MANUSCRIPT, ROOT


def apply(manuscript, review):
    rows = [json.loads(x) for x in manuscript.read_text(encoding='utf-8').splitlines()]
    lookup = {(r['file'], r['line']): r for r in rows}
    seen, changed = set(), 0
    for entry in review:
        key = entry['file'], entry['line']
        if key in seen:
            raise ValueError(f'Duplicate review: {key}')
        seen.add(key)
        row = lookup[key]
        if row['ja'] != entry['ja'] or row['zh'] not in (entry['before'], entry['after']):
            raise ValueError(f'Source/current text changed: {key}')
        if CONTROLS.findall(entry['before']) != CONTROLS.findall(entry['after']):
            raise ValueError(f'Review changes control tokens: {key}')
        if row['zh'] != entry['after']:
            row['zh'] = entry['after']
            changed += 1
    if changed:
        temp = manuscript.with_suffix('.jsonl.tmp')
        temp.write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in rows), encoding='utf-8')
        temp.replace(manuscript)
    return changed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manuscript', type=Path, default=ROOT/'localization'/MANUSCRIPT)
    parser.add_argument('--review', type=Path, required=True)
    args = parser.parse_args()
    review = [json.loads(x) for x in args.review.read_text(encoding='utf-8').splitlines()]
    print(f'Applied {apply(args.manuscript, review)} rows.')

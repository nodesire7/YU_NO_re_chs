"""Collect per-scene edits against the reviewed source revision into one batch."""
import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path

from localize_text import CONTROLS, MANUSCRIPT, ROOT


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def fingerprint(rows):
    payload = "".join(json.dumps([r["line"], r["ja"], r["zh"]], ensure_ascii=False,
                                 separators=(",", ":")) + "\n" for r in rows)
    return sha256(payload.encode()).hexdigest()


def assemble(manuscript, directory):
    scenes = defaultdict(list)
    for row in read_jsonl(manuscript):
        scenes[row["file"]].append(row)
    coverage = json.loads((directory / "coverage.json").read_text(encoding="utf-8"))
    if {p.name[:-6] for p in directory.glob("*.scx.txt.jsonl")} != set(coverage):
        raise ValueError("Scene files differ from the coverage index")
    batch = []
    for name, record in sorted(coverage.items()):
        scene = scenes[name]
        edits = read_jsonl(directory / (name + ".jsonl"))
        indices = [e["line"] for e in edits]
        original = [dict(row) for row in scene]
        for edit in edits:
            pos = edit["line"] - 1
            if 0 <= pos < len(scene) and original[pos]["zh"] == edit["after"]:
                original[pos]["zh"] = edit["before"]
        if ([r["line"] for r in scene] != list(range(1, len(scene) + 1))
                or (record["first"], record["last"], record["checked"]) != (1, len(scene), len(scene))
                or fingerprint(original) != record["current_ja_zh_sha256"]):
            raise ValueError(f"Reviewed script no longer matches manuscript: {name}")
        if (record["proposed"] != len(edits) or indices != sorted(set(indices))
                or any(i < 1 or i > len(scene) for i in indices)):
            raise ValueError(f"Unexpected edit count or line indices: {name}")
        for edit in edits:
            r = scene[edit["line"] - 1]
            if (edit["file"] != name or edit["ja"] != r["ja"] or r["zh"] not in (edit["before"], edit["after"])
                    or edit["after"] == edit["before"]
                    or CONTROLS.findall(edit["after"]) != CONTROLS.findall(edit["before"])):
                raise ValueError(f"Invalid review: {name}:{edit['line']}")
        batch.extend(edits)
    shared_path = directory / "interaction_text.jsonl"
    shared = read_jsonl(shared_path) if shared_path.is_file() else []
    seen = {(e["file"], e["line"]) for e in batch}
    for edit in shared:
        name, line = edit["file"], edit["line"]
        if name in coverage or (name, line) in seen or not 1 <= line <= len(scenes[name]):
            raise ValueError(f"Reconcile repeated interaction with scene review: {name}:{line}")
        row = scenes[name][line - 1]
        if (edit["ja"] != row["ja"] or row["zh"] not in (edit["before"], edit["after"]) or edit["after"] == edit["before"]
                or CONTROLS.findall(edit["after"]) != CONTROLS.findall(edit["before"])):
            raise ValueError(f"Repeated interaction changed: {name}:{line}")
        seen.add((name, line))
    return batch + shared, sum(r["checked"] for r in coverage.values()), len(shared)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manuscript", type=Path, default=ROOT / "localization" / MANUSCRIPT)
    parser.add_argument("--reviews", type=Path, default=ROOT / "localization/reviews/in_progress/normal_playthrough")
    parser.add_argument("--out", type=Path, default=ROOT / "work/review_next/scene-review.jsonl")
    args = parser.parse_args()
    if args.out.resolve() == args.manuscript.resolve() or args.out.resolve().is_relative_to(args.reviews.resolve()):
        parser.error("Choose an output file outside the review inputs")
    batch, checked, shared = assemble(args.manuscript, args.reviews)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in batch), encoding="utf-8", newline="\n")
    print(f"{checked} scene rows checked, {shared} other occurrences, {len(batch)} edits assembled")

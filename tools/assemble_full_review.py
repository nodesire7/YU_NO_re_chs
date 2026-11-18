"""Export a complete, source-locked dialogue review to a ledger and one edit batch."""
import argparse
from collections import Counter
from hashlib import sha256
import gzip
import json
from pathlib import Path
import sqlite3
import tempfile

from localize_text import CONTROLS, MANUSCRIPT, ROOT


def read_lines(path):
    return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines()]


def source_context(lookup, file, line):
    entry = lookup.get((file, line))
    if entry is None:
        return ""
    return entry["ja"].removeprefix("[name]").replace("[line]", "：").removesuffix("[%p]")


def remaining_keys(rows, reviews):
    covered_scenes = set(json.loads((reviews / "in_progress/normal_playthrough/coverage.json").read_text(encoding="utf-8")))
    covered_scenes.add("yns_open.scx.txt")
    covered = set()
    files = [*(reviews / "in_progress").glob("*.jsonl"), reviews / "in_progress/normal_playthrough/interaction_text.jsonl",
             reviews / "v1.3.3/changes.jsonl"]
    for path in files:
        for r in read_lines(path):
            covered.add((r["file"], r["line"]))
    for item in read_lines(reviews / "v1.3.3/long_dialogue_review.jsonl"):
        covered.update(tuple(ref) for ref in item["refs"])
    for item in json.loads((reviews / "v1.3.3/numbers_review.json").read_text(encoding="utf-8")):
        covered.add((item["file"], item["line"]))
    return {(r["file"], r["line"]) for r in rows if "[line]" in r["zh"]
            and r["file"] not in covered_scenes and (r["file"], r["line"]) not in covered}


def assemble(db, source, destination):
    if destination.exists():
        raise ValueError(f"Output directory already exists: {destination}")
    rows = read_lines(source)
    lookup = {(r["file"], r["line"]): r for r in rows}
    expected = remaining_keys(rows, ROOT / "localization/reviews")
    if len(expected) != 83_407:
        raise ValueError(f"Unexpected review scope: {len(expected)} rows")
    pending = expected.copy()
    source_hash = sha256(source.read_bytes()).hexdigest()
    db.row_factory = sqlite3.Row
    if db.execute("select v from meta where k='source'").fetchone()["v"] != source_hash:
        raise ValueError("Manuscript no longer matches the review input")
    db.execute("begin")
    speaker_edits = {}
    if db.execute("select 1 from sqlite_master where type='table' and name='speaker_edits'").fetchone():
        speaker_edits = {r["id"]: r for r in db.execute("select id,original,previous,replacement from speaker_edits")}
    changes, decisions, coverage = [], Counter(), []
    per_script = {}
    for row in db.execute("""select file,line,id,source,zh,preceding,following,decision,reason,step
                              from positions join jobs using(id) order by file,line"""):
        key = row["file"], row["line"]
        if key not in pending:
            raise ValueError(f"Unexpected or duplicated review position: {key}")
        pending.remove(key)
        base = lookup[key]
        if row["source"] != base["ja"] or row["zh"] != base["zh"]:
            raise ValueError(f"Source mismatch at {key}")
        context = [row["preceding"], row["following"]]
        if context != [source_context(lookup, key[0], key[1] + offset) for offset in (-1, 1)]:
            original = base["ja"].partition("[line]")[2].removesuffix("[%p]")
            if context != ["", ""] or not original or original.strip("《》‥。!?"):
                raise ValueError(f"Japanese scene context mismatch at {key}")
        fingerprint = json.dumps([base["ja"], base["zh"], *context], ensure_ascii=False, separators=(",", ":"))
        if sha256(fingerprint.encode("utf-8")).hexdigest() != row["id"]:
            raise ValueError(f"Dialogue fingerprint mismatch at {key}")
        prefix, _, old_body = base["zh"].partition("[line]")
        suffix = "[%p]" if old_body.endswith("[%p]") else ""
        decision = row["decision"]
        if row["step"] != "accepted" or not isinstance(decision, str) or not row["reason"]:
            raise ValueError(f"Unresolved dialogue: {key}")
        if not decision.strip():
            original_body = base["ja"].partition("[line]")[2].removesuffix("[%p]")
            if decision != "" or old_body != suffix or original_body != "":
                raise ValueError(f"Empty translation of a nonempty source: {key}")
        speaker = speaker_edits.get(row["id"])
        if speaker:
            replacement = speaker["replacement"]
            if (base["ja"].partition("[line]")[0] != speaker["original"] or prefix != speaker["previous"]
                    or not replacement.startswith("[name]") or not replacement.removeprefix("[name]").strip()
                    or CONTROLS.findall(prefix) != CONTROLS.findall(replacement)):
                raise ValueError(f"Speaker revision differs from the source or changes its controls: {key}")
            prefix = replacement
        after = prefix + "[line]" + decision + suffix
        if (CONTROLS.findall(after) != CONTROLS.findall(base["zh"]) or "\n" in after
                or "\r" in after or "\ufffd" in after or decision in ("?", "=")):
            raise ValueError(f"Invalid reviewed text: {key}")
        changed = base["zh"] != after
        if changed:
            changes.append(dict(file=key[0], line=key[1], ja=base["ja"], before=base["zh"], after=after))
        method = row["reason"].partition(":")[0]
        decisions[(method, changed)] += 1
        script = per_script.setdefault(key[0], Counter())
        script["checked"] += 1
        script["changed"] += int(changed)
        if speaker:
            script["speaker_revised"] += 1
        if method.startswith("silence/"):
            script["punctuation"] += 1
        elif method.startswith("editor "):
            script["editor_compared"] += 1
        else:
            script["model_assisted"] += 1
        coverage.append([*key, "edit" if changed else "keep", row["reason"], row["id"]])
    if pending:
        raise ValueError(f"{len(pending)} positions missing from the ledger")
    supplementary = []
    if db.execute("select 1 from sqlite_master where type='table' and name='supplementary'").fetchone():
        for record in db.execute("select file,line,ja,before,after from supplementary order by file,line"):
            item = dict(record)
            key = item["file"], item["line"]
            original = lookup.get(key)
            if key in expected or original is None or (original["ja"], original["zh"]) != (item["ja"], item["before"]):
                raise ValueError(f"Supplementary edit differs from original or overlaps dialogue ledger: {key}")
            before, after = item["before"], item["after"]
            if (not after.strip() or after == before or CONTROLS.findall(after) != CONTROLS.findall(before)
                    or any(char in after for char in ("\n", "\r", "\ufffd"))):
                raise ValueError(f"Invalid supplementary edit: {key}")
            supplementary.append(item)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as tempdir:
        tmp = Path(tempdir) / "result"
        tmp.mkdir()
        with (tmp / "coverage.jsonl.gz").open("wb") as out, gzip.GzipFile(fileobj=out, mode="wb", mtime=0) as gz:
            for row in coverage:
                gz.write((json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8"))
        (tmp / "changes.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False)+"\n" for r in changes),
                                            encoding="utf-8", newline="\n")
        (tmp / "supplementary.jsonl").write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in supplementary),
                                                 encoding="utf-8", newline="\n")
        (tmp / "by_script.json").write_text(json.dumps(per_script, ensure_ascii=False, indent=2)+"\n",
                                            encoding="utf-8")
        report = dict(input_sha256=source_hash, checked=len(coverage), changed=len(changes), scripts=len(per_script),
                      distinct_contexts=len({row[-1] for row in coverage}), supplementary_edits=len(supplementary),
                      coverage_columns=["file", "line", "decision", "method", "context_sha256"],
                      methods=[dict(method=k, changed=v, count=n) for (k,v),n in sorted(decisions.items())])
        (tmp / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        tmp.rename(destination)
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--database", type=Path, required=True)
    p.add_argument("--manuscript", type=Path, default=ROOT / "localization" / MANUSCRIPT)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    with sqlite3.connect(args.database.resolve().as_uri()+"?mode=ro", uri=True) as conn:
        print(assemble(conn, args.manuscript, args.out))

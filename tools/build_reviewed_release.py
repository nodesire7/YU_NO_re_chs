"""Apply one complete review, rebuild the scripts, then package and exercise both installers."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import zipfile

from apply_text_review import apply
from assemble_full_review import assemble, read_lines
from audit_text import audit
from localize_text import MANUSCRIPT, ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--compiler", required=True, type=Path)
    args = parser.parse_args()
    from build_installer import build

    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+){2}", args.version) or any(int(n) > 65535 for n in args.version.split(".")):
        parser.error("Use a numeric major.minor.patch version")
    if not args.compiler.is_file():
        parser.error("NSIS compiler not found")
    version = "v" + args.version
    src = ROOT / "localization" / MANUSCRIPT
    review = src.parent / "reviews" / version
    with sqlite3.connect(args.database.resolve().as_uri() + "?mode=ro", uri=True) as db:
        pending = db.execute("select count(*) from positions join jobs using(id) where step != 'accepted'").fetchone()[0]
        if pending:
            raise SystemExit(f"{pending:,} dialogue positions still need a decision")
        if not review.exists():
            assemble(db, src, review)
            db.rollback()
        summary = json.loads((review / "summary.json").read_text(encoding="utf-8"))
        changes = read_lines(review / "changes.jsonl") + read_lines(review / "supplementary.jsonl")
        # Keep the exact input bytes so a retry can verify both the export and the applied manuscript.
        stamp = summary["input_sha256"]
        backup = ROOT / "work" / f"manuscript-{stamp}.jsonl"
        if not backup.exists():
            original = src.read_bytes()
            if sha256(original).hexdigest() != stamp:
                raise ValueError("Missing original for resumed review")
            with tempfile.NamedTemporaryFile(dir=backup.parent, delete=False) as f:
                f.write(original)
            Path(f.name).replace(backup)
        if sha256(backup.read_bytes()).hexdigest() != stamp:
            raise ValueError("Stored review input checksum mismatch")
        with tempfile.TemporaryDirectory(dir=backup.parent) as temporary:
            scratch = Path(temporary)
            assemble(db, backup, scratch / "review")
            for name in ("summary.json", "coverage.jsonl.gz", "changes.jsonl", "supplementary.jsonl", "by_script.json"):
                if (review / name).read_bytes() != (scratch / "review" / name).read_bytes():
                    raise ValueError(f"Review export differs from editorial decisions: {name}")
            expected = scratch / "manuscript.jsonl"
            expected.write_bytes(backup.read_bytes())
            if apply(expected, changes) != summary["changed"] + summary["supplementary_edits"]:
                raise ValueError("Edit count mismatch")
            quality = audit(expected, read_lines(backup))
            if quality["issues"] or quality["missing"]:
                raise ValueError(f"Manuscript audit failed: {quality['issue_counts']}, missing {quality['missing']}")
            before = sha256(src.read_bytes()).digest()
            after = sha256(expected.read_bytes()).digest()
            if before != after:
                if before.hex() != stamp:
                    raise ValueError("Current manuscript differs from the reviewed input")
                apply(src, changes)
            if sha256(src.read_bytes()).digest() != after:
                raise ValueError("Applied manuscript checksum mismatch")

    def run(tool, *arguments):
        subprocess.run([sys.executable, "-X", "utf8", "-u", str(ROOT / "tools" / tool), *arguments],
                       cwd=ROOT, check=True)

    run("build_all.py")
    run("package_release.py", "--version", args.version)
    dist = ROOT / "dist"
    stage = dist / version
    exe = dist / f"GBTGames_YU-NO_CHS_{version}_Setup.exe"
    build(stage, exe, args.version, str(args.compiler))
    archive = dist / f"YU-NO_CHS_A-FEI-_{version}.zip"
    with zipfile.ZipFile(archive) as z:
        files = {p.relative_to(stage).as_posix() for p in stage.rglob("*") if p.is_file()}
        if len(z.namelist()) != len(files) or set(z.namelist()) != files:
            raise ValueError("ZIP file list differs from staging")
        for name in files:
            if z.read(name) != (stage / name).read_bytes():
                raise ValueError(f"ZIP payload differs: {name}")
    for options in ([], ["--installer", str(exe)]):
        run("verify_release.py", "--version", args.version, "--staging", str(stage), *options)
    print(f"{summary['checked']:,} dialogue positions, {summary['changed']:,} edits. Verified {exe} and {archive}.")


if __name__ == "__main__":
    main()

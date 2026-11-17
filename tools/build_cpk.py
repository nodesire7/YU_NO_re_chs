#!/usr/bin/env python3
"""Build a CPK from a directory of files using a reference CPK's ID mapping.

Usage:
  python build_cpk.py --reference <original.cpk> --src <dir> --out <out.cpk> [--align 2048]

The reference supplies the file order and IDs (so the game keeps resolving resources
by the same IDs). Files are matched by name against <src>.
"""
import argparse
import csv
import os
import subprocess
import sys
import tempfile

CPKMAKEC = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "pack", "crifilesystem v2.40.13.0", "cpkmakec.exe")
CPKMAKEC = os.path.normpath(CPKMAKEC)


def export_info(cpkmakec, cpk, out_csv):
    r = subprocess.run([cpkmakec, cpk, "-exportcpkinfo=" + out_csv],
                       capture_output=True, text=True, errors="replace")
    if not os.path.exists(out_csv):
        raise RuntimeError("export failed: " + (r.stdout or "") + (r.stderr or ""))
    return out_csv


def read_info(path):
    rows = []
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            parts = next(csv.reader([line]))
            if len(parts) < 10:
                continue
            rows.append({"name": parts[0], "id": int(parts[1]),
                         "size": int(parts[2]), "path": parts[9]})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", required=True)
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--align", default="2048")
    ap.add_argument("--mode", default="FILENAMEID")
    ap.add_argument("--cpkmakec", default=CPKMAKEC)
    args = ap.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        info = os.path.join(tmp, "info.csv")
        export_info(args.cpkmakec, args.reference, info)
        ref = read_info(info)

    missing = []
    csv_lines = []
    for r in ref:
        local = os.path.join(args.src, r["name"])
        if not os.path.exists(local):
            missing.append(r["name"])
            continue
        csv_lines.append("%s,%s,%d,Uncompress" % (local, r["name"], r["id"]))
    if missing:
        print("missing %d files, e.g. %s" % (len(missing), missing[:5]), file=sys.stderr)
        return 2

    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="ascii", newline="") as fh:
        fh.write("\n".join(csv_lines) + "\n")
        list_csv = fh.name
    try:
        with tempfile.TemporaryDirectory(dir=os.path.dirname(os.path.abspath(args.out))) as stage:
            archive = os.path.join(stage, "build.cpk")
            r = subprocess.run([args.cpkmakec, list_csv, archive,
                                "-align=" + args.align, "-mode=" + args.mode, "-noerrorstop"],
                               capture_output=True, text=True, errors="replace")
            if r.returncode or not os.path.isfile(archive):
                print("build failed:\n" + (r.stdout or "") + (r.stderr or ""), file=sys.stderr)
                return 3
            os.replace(archive, args.out)
        print("built", args.out, os.path.getsize(args.out), "files:", len(csv_lines))
    finally:
        os.unlink(list_csv)
    return 0


if __name__ == "__main__":
    sys.exit(main())

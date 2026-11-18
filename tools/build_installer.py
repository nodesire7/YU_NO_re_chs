"""Build a self-contained GBTGames installer from a verified release staging directory."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def build(staging, output, version, compiler):
    staging, output = staging.resolve(), output.resolve()
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:-[A-Za-z0-9.-]+)?", version)
    if not match or any(int(part) > 65535 for part in match.groups()):
        raise ValueError(f"Invalid installer version: {version}")
    windows_version = ".".join((*match.groups(), "0"))
    manifest = json.loads((staging / "manifest.json").read_text(encoding="utf-8"))
    expected = {"data/scrchs.cpk", "data/syschs.cpk", "data/manual.cpk", "patch.dll", "GBT_logo.png"}
    declared = {r["path"].replace("\\", "/") for r in manifest}
    actual = {p.relative_to(staging / "files").as_posix() for p in (staging / "files").rglob("*") if p.is_file()}
    if actual != expected or declared != expected or len(manifest) != len(expected):
        raise ValueError("Unexpected installer payload")
    for entry in manifest:
        path = staging / "files" / entry["path"]
        if path.stat().st_size != entry["bytes"] or sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError(f"Manifest mismatch: {path}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        assets = Path(tmp)
        logo = Image.open(ROOT / "distribution/GBT_logo.png").convert("RGBA")
        shutil.copyfile(ROOT / "distribution/GBT.ico", assets / "gbt.ico")
        logo.thumbnail((140, 50), Image.Resampling.LANCZOS)
        header = Image.new("RGB", (150, 57), "white")
        header.paste(logo, ((150-logo.width)//2, (57-logo.height)//2), logo)
        header.save(assets / "gbt-header.bmp")
        candidate = assets / "installer.exe"
        subprocess.run([compiler, "/INPUTCHARSET", "UTF8", "/V2", f"/DSTAGING={staging}",
                        f"/DASSETS={assets}", f"/DOUTPUT={candidate}", f"/DPATCH_VERSION={version}",
                        f"/DWINDOWS_VERSION={windows_version}",
                        str(ROOT / "distribution/installer.nsi")], check=True)
        candidate.replace(output)
    checksum = sha256(output.read_bytes()).hexdigest()
    output.with_suffix(".exe.sha256").write_text(f"{checksum}  {output.name}\n", encoding="utf-8")
    print(f"{output} ({output.stat().st_size} bytes, SHA-256 {checksum})")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--version", required=True)
    p.add_argument("--staging", type=Path)
    p.add_argument("--out", type=Path)
    p.add_argument("--compiler", default=os.getenv("MAKENSIS") or shutil.which("makensis"))
    args = p.parse_args()
    if not args.compiler:
        p.error("Use --compiler to select makensis.exe")
    build(args.staging or ROOT / "dist" / f"v{args.version}",
          args.out or ROOT / "dist" / f"GBTGames_YU-NO_CHS_v{args.version}_Setup.exe",
          args.version, args.compiler)

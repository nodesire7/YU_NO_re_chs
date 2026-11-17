"""Package built CPKs with verified, reversible Windows installation scripts."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='1.3.1')
    args = parser.parse_args()
    staging = ROOT / 'dist' / f'v{args.version}'
    staging.mkdir(parents=True, exist_ok=True)
    sources = {f'data\\{name}.cpk': ROOT / 'work/out' / f'{name}.cpk'
               for name in ('scrchs', 'syschs', 'manual')}
    sources['patch.dll'] = ROOT / 'work/patch_build/patch.dll'
    sources['GBT_logo.png'] = ROOT / 'distribution/GBT_logo.png'
    manifest = []
    for rel, source in sources.items():
        target = staging / 'files' / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        manifest.append(dict(path=rel, bytes=source.stat().st_size,
                             sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
    (staging / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    script = (ROOT / 'distribution/patch.ps1').read_text(encoding='utf-8-sig')
    (staging / 'patch.ps1').write_text(script, encoding='utf-8-sig')
    for name, mode in [('安装到游戏目录', 'Install'), ('卸载还原', 'Uninstall')]:
        batch = ('@echo off\nchcp 936 >nul\n'
                 f'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0patch.ps1" -Mode {mode} -Game "%~1"\n'
                 'set "RESULT=%ERRORLEVEL%"\npause\nexit /b %RESULT%\n')
        (staging / f'{name}.bat').write_text(batch, encoding='gbk', newline='\r\n')
    shutil.copy2(ROOT / 'distribution/汉化说明.txt', staging / '汉化说明.txt')
    archive = ROOT / 'dist' / f'YU-NO_CHS_A-FEI-_v{args.version}.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as package:
        for path in sorted(staging.rglob('*')):
            if path.is_file():
                package.write(path, path.relative_to(staging).as_posix())
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.zip.sha256').write_text(f'{digest}  {archive.name}\n', encoding='utf-8')
    print(archive, archive.stat().st_size, digest)


if __name__ == '__main__':
    main()

"""Exercise the packaged installer with pre-existing files and a clean game folder."""
import hashlib
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import shutil

ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--version', default='1.3.4-local')
parser.add_argument('--installer', type=Path, help='Exercise the self-contained installer EXE')
parser.add_argument('--staging', type=Path)
args = parser.parse_args()
STAGE = args.staging or ROOT / 'dist' / f'v{args.version}'
FILES = ['data/scrchs.cpk', 'data/syschs.cpk', 'data/manual.cpk', 'patch.dll', 'GBT_logo.png']
results = []
for kind in ('existing', 'clean', 'legacy', 'locked'):
    with tempfile.TemporaryDirectory(prefix='release_check_', dir=ROOT / 'work') as temp:
        base = Path(temp)
        game = base / 'Steam Library' / 'YU-NO'
        game.mkdir(parents=True)
        if args.installer:
            exe = base / '移动测试' / 'sub folder' / 'GBT Setup.exe'
            exe.parent.mkdir(parents=True)
            shutil.copy2(args.installer, exe)
        assert game.resolve().is_relative_to((ROOT / 'work').resolve())
        (game / 'data').mkdir()
        (game / 'Game.exe').write_bytes(b'test-only-not-executable')
        before = {}
        for rel in FILES if kind != 'clean' else ['data/manual.cpk']:
            data = ('ORIGINAL ' + rel).encode()
            (game / rel).write_bytes(data)
            before[rel] = data
        if kind == 'legacy':
            backup = game / '_backup_cht'
            backup.mkdir()
            for rel, data in before.items():
                (backup / Path(rel).name).write_bytes(data)
                (game / rel).write_bytes(b'OLDER PATCH')
        def run(mode, expect_success=True):
            if args.installer:
                # NSIS requires /D= last and literal, including when the path contains spaces.
                switches = [str(exe), '/S'] + (['/RESTORE'] if mode == 'Uninstall' else [])
                command = subprocess.list2cmdline(switches) + ' /D=' + str(game)
                result = subprocess.run(command, executable=str(exe), cwd=base, timeout=180)
                assert (result.returncode == 0) == expect_success, (mode, result.returncode)
                return
            result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                                     '-File', str(STAGE / 'patch.ps1'), '-Mode', mode, '-Game', str(game)],
                                    capture_output=True)
            assert (result.returncode == 0) == expect_success, (mode, result.stdout, result.stderr)
        if kind == 'locked':
            # A regular reader denies FILE_SHARE_DELETE on Windows. The fourth replacement must fail.
            with (game / 'patch.dll').open('rb') as held_file:
                run('Install', expect_success=False)
            assert all((game / path).read_bytes() == data for path, data in before.items())
            assert not list(game.glob('.gbt-yuno-*'))
        run('Install')
        saved = {p.name: p.read_bytes() for p in (game / '_backup_cht').iterdir()}
        for entry in json.loads((STAGE / 'manifest.json').read_text(encoding='utf-8')):
            assert hashlib.sha256((game / entry['path']).read_bytes()).hexdigest() == entry['sha256']
        run('Install')
        assert saved == {p.name: p.read_bytes() for p in (game / '_backup_cht').iterdir()}
        run('Uninstall')
        for rel in FILES:
            if rel in before:
                assert (game / rel).read_bytes() == before[rel], rel
            else:
                assert not (game / rel).exists(), rel
        results.append(dict(scenario=kind, install=True, reinstall_preserves_backup=True,
                            uninstall_restores_original=True))
        print(kind, 'PASS')
(ROOT / 'work' / f'installer_v{args.version}_results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')

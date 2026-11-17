"""Exercise the packaged installer with pre-existing files and a clean game folder."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
STAGE = ROOT / 'dist/v1.3.0'
FILES = ['data/scrchs.cpk', 'data/syschs.cpk', 'data/manual.cpk', 'patch.dll', 'GBT_logo.png']
results = []
for kind in ('existing', 'clean', 'legacy'):
    with tempfile.TemporaryDirectory(prefix='release_check_', dir=ROOT / 'work') as temp:
        game = Path(temp)
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
        def run(mode):
            result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                                     '-File', str(STAGE / 'patch.ps1'), '-Mode', mode, '-Game', str(game)],
                                    capture_output=True)
            assert result.returncode == 0, (mode, result.stdout, result.stderr)
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
(ROOT / 'work/installer_v1.3_results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')

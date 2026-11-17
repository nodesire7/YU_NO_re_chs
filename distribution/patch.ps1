param(
    [ValidateSet('Install', 'Uninstall')][string]$Mode = 'Install',
    [string]$Game
)
$ErrorActionPreference = 'Stop'
try {
    if (-not $Game) { $Game = Read-Host '请输入游戏目录（包含 Game.exe）' }
    $Game = (Resolve-Path -LiteralPath $Game).Path
    if (-not (Test-Path -LiteralPath (Join-Path $Game 'Game.exe') -PathType Leaf)) {
        throw '该目录不包含 Game.exe。'
    }
    $backup = Join-Path $Game '_backup_cht'
    $statePath = Join-Path $backup 'install-state.json'
    $files = @('data\scrchs.cpk', 'data\syschs.cpk', 'data\manual.cpk', 'patch.dll', 'GBT_logo.png')
    if ($Mode -eq 'Install') {
        $manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        foreach ($rel in $files) {
            $source = Join-Path $PSScriptRoot (Join-Path 'files' $rel)
            $entry = $manifest | Where-Object { $_.path -eq $rel }
            $stream = [IO.File]::OpenRead($source)
            $sha = [Security.Cryptography.SHA256]::Create()
            try { $hash = ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-', '') }
            finally { $stream.Dispose(); $sha.Dispose() }
            if (-not $entry -or $hash -ne $entry.sha256) {
                throw "补丁文件校验失败：$rel。请重新完整解压补丁包。"
            }
        }
        New-Item -ItemType Directory -Path $backup -Force | Out-Null
        if (-not (Test-Path -LiteralPath $statePath)) {
            $state = foreach ($rel in $files) {
                $target = Join-Path $Game $rel
                $saved = Join-Path $backup ([IO.Path]::GetFileName($rel))
                $existed = (Test-Path -LiteralPath $saved) -or (Test-Path -LiteralPath $target)
                if ((Test-Path -LiteralPath $target) -and -not (Test-Path -LiteralPath $saved)) {
                    Copy-Item -LiteralPath $target -Destination $saved
                }
                [pscustomobject]@{ path = $rel; existed = $existed }
            }
            $state | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding UTF8
        }
        foreach ($rel in $files) {
            $target = Join-Path $Game $rel
            New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($target)) -Force | Out-Null
            Copy-Item -LiteralPath (Join-Path $PSScriptRoot (Join-Path 'files' $rel)) -Destination $target -Force
        }
        Write-Host '安装完成。请通过游戏启动器启动游戏；原文件保存在 _backup_cht。'
    } else {
        if (Test-Path -LiteralPath $statePath) {
            $state = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
        } else {
            # Older releases did not record originally absent files. Restore only known backups.
            $state = foreach ($rel in $files) {
                if (Test-Path -LiteralPath (Join-Path $backup ([IO.Path]::GetFileName($rel)))) {
                    [pscustomobject]@{ path = $rel; existed = $true }
                }
            }
            if (-not $state) { throw '没有找到可还原的 _backup_cht 备份。' }
        }
        foreach ($entry in $state) {
            if ($entry.path -notin $files) { throw '备份记录包含未知文件。' }
            if ($entry.existed -and -not (Test-Path -LiteralPath (Join-Path $backup ([IO.Path]::GetFileName($entry.path))))) {
                throw "缺少备份：$($entry.path)"
            }
        }
        foreach ($entry in $state) {
            $target = Join-Path $Game $entry.path
            if ($entry.existed) {
                Copy-Item -LiteralPath (Join-Path $backup ([IO.Path]::GetFileName($entry.path))) -Destination $target -Force
            } elseif (Test-Path -LiteralPath $target) {
                Remove-Item -LiteralPath $target
            }
        }
        Write-Host '还原完成。原先不存在的补丁文件已移除，备份仍保留。'
    }
    exit 0
} catch {
    Write-Error $_ -ErrorAction Continue
    exit 1
}

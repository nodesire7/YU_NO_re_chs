param(
    [ValidateSet('Install', 'Uninstall')][string]$Mode = 'Install',
    [string]$Game
)
$ErrorActionPreference = 'Stop'
$guard = $null
$ownsGuard = $false

function Set-PatchFiles($gameRoot, $operations) {
    $root = [IO.Path]::GetFullPath($gameRoot)
    $transaction = [IO.Path]::GetFullPath((Join-Path $root ('.gbt-yuno-' + [Guid]::NewGuid().ToString('N'))))
    if ([IO.Path]::GetDirectoryName($transaction) -ne $root.TrimEnd('\')) { throw '临时目录路径无效。' }
    $pending = [Collections.Generic.List[object]]::new()
    $applied = [Collections.Generic.List[object]]::new()
    $keepRecovery = $false
    try {
        [void][IO.Directory]::CreateDirectory($transaction)
        foreach ($operation in $operations) {
            $target = Join-Path $gameRoot $operation.Relative
            $slot = [string]$pending.Count
            $incoming = Join-Path $transaction ($slot + '.new')
            $previous = Join-Path $transaction ($slot + '.old')
            $existed = [IO.File]::Exists($target)
            if ($operation.Source) {
                [IO.File]::Copy($operation.Source, $incoming)
                [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target))
            }
            $pending.Add([pscustomobject]@{ Target=$target; Incoming=$incoming; Previous=$previous;
                Existed=$existed; Install=[bool]$operation.Source })
        }
        foreach ($item in $pending) {
            if ($item.Install -and $item.Existed) {
                [IO.File]::Replace($item.Incoming, $item.Target, $item.Previous, $true)
            } elseif ($item.Install) {
                [IO.File]::Move($item.Incoming, $item.Target)
            } elseif ($item.Existed) {
                [IO.File]::Move($item.Target, $item.Previous)
            } else {
                continue
            }
            $applied.Add($item)
        }
    } catch {
        $failure = $_
        for ($i = $applied.Count - 1; $i -ge 0; $i--) {
            $item = $applied[$i]
            try {
                if ($item.Existed -and [IO.File]::Exists($item.Target)) {
                    [IO.File]::Copy($item.Previous, $item.Target, $true)
                } elseif ($item.Existed) {
                    [IO.File]::Move($item.Previous, $item.Target)
                } else {
                    [IO.File]::Delete($item.Target)
                }
            } catch {
                $keepRecovery = $true
                Write-Warning "原文件保留在 $transaction，请检查 $($item.Target)。"
            }
        }
        throw $failure
    } finally {
        if (-not $keepRecovery -and [IO.Directory]::Exists($transaction)) {
            [IO.Directory]::Delete($transaction, $true)
        }
    }
}
try {
    if (-not $Game) { $Game = Read-Host '请输入游戏目录（包含 Game.exe）' }
    $Game = (Resolve-Path -LiteralPath $Game).Path
    if (-not (Test-Path -LiteralPath (Join-Path $Game 'Game.exe') -PathType Leaf)) {
        throw '该目录不包含 Game.exe。'
    }
    $identity = [Text.Encoding]::UTF8.GetBytes($Game.TrimEnd('\').ToUpperInvariant())
    $sha = [Security.Cryptography.SHA256]::Create()
    try { $guardKey = [BitConverter]::ToString($sha.ComputeHash($identity)).Replace('-', '') }
    finally { $sha.Dispose() }
    $guard = [Threading.Mutex]::new($false, ('Local\GBTGames-YUNO-' + $guardKey))
    try { $ownsGuard = $guard.WaitOne(0) }
    catch [Threading.AbandonedMutexException] { $ownsGuard = $true }
    if (-not $ownsGuard) { throw '另一个安装或还原操作正在处理此游戏目录。' }
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
                throw "补丁文件校验失败：$rel。请重新获取完整补丁后重试。"
            }
        }
        New-Item -ItemType Directory -Path $backup -Force | Out-Null
        if (-not (Test-Path -LiteralPath $statePath)) {
            $state = foreach ($rel in $files) {
                $target = Join-Path $Game $rel
                $saved = Join-Path $backup ([IO.Path]::GetFileName($rel))
                $existed = (Test-Path -LiteralPath $saved) -or (Test-Path -LiteralPath $target)
                if ((Test-Path -LiteralPath $target) -and -not (Test-Path -LiteralPath $saved)) {
                    $temporary = $saved + '.' + [Guid]::NewGuid().ToString('N') + '.tmp'
                    try {
                        [IO.File]::Copy($target, $temporary)
                        [IO.File]::Move($temporary, $saved)
                    } finally {
                        if ([IO.File]::Exists($temporary)) { [IO.File]::Delete($temporary) }
                    }
                }
                [pscustomobject]@{ path = $rel; existed = $existed }
            }
            $temporary = $statePath + '.' + [Guid]::NewGuid().ToString('N') + '.tmp'
            try {
                $state | ConvertTo-Json | Set-Content -LiteralPath $temporary -Encoding UTF8
                [IO.File]::Move($temporary, $statePath)
            } finally {
                if ([IO.File]::Exists($temporary)) { [IO.File]::Delete($temporary) }
            }
        }
        $operations = foreach ($rel in $files) {
            [pscustomobject]@{ Relative=$rel; Source=(Join-Path $PSScriptRoot (Join-Path 'files' $rel)) }
        }
        Set-PatchFiles $Game $operations
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
        $operations = foreach ($entry in $state) {
            $source = if ($entry.existed) { Join-Path $backup ([IO.Path]::GetFileName($entry.path)) }
            [pscustomobject]@{ Relative=$entry.path; Source=$source }
        }
        Set-PatchFiles $Game $operations
        Write-Host '还原完成。原先不存在的补丁文件已移除，备份仍保留。'
    }
    exit 0
} catch {
    Write-Error $_ -ErrorAction Continue
    exit 1
} finally {
    if ($ownsGuard) { $guard.ReleaseMutex() }
    if ($guard) { $guard.Dispose() }
}

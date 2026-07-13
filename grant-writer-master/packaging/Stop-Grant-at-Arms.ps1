$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$PidDir = Join-Path $Here "runtime\pids"
$expected = @{
    app = [IO.Path]::GetFullPath((Join-Path $Here "GrantAtArms.exe"))
    llama = [IO.Path]::GetFullPath((Join-Path $Here "runtime\llama\llama-server.exe"))
}
$stopped = 0
$refused = 0

foreach ($name in @("app", "llama")) {
    $recordPath = Join-Path $PidDir "$name.json"
    if (-not (Test-Path -LiteralPath $recordPath -PathType Leaf)) { continue }
    try {
        $record = Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json
        $process = Get-Process -Id ([int]$record.pid) -ErrorAction SilentlyContinue
        if (-not $process) {
            Remove-Item -LiteralPath $recordPath -Force
            continue
        }
        $actualPath = [IO.Path]::GetFullPath($process.Path)
        $actualStart = $process.StartTime.ToUniversalTime().ToString("o")
        $pathMatches = [string]::Equals($actualPath, $expected[$name], [StringComparison]::OrdinalIgnoreCase)
        $timeMatches = [string]::Equals($actualStart, [string]$record.start_time_utc, [StringComparison]::Ordinal)
        if ($pathMatches -and $timeMatches) {
            & taskkill.exe /PID $process.Id /T /F | Out-Null
            if ($LASTEXITCODE -ne 0) { throw "Could not stop the verified $name process tree." }
            $stopped += 1
        }
        else {
            Write-Warning "Refused to stop PID $($process.Id): its path or start time does not match the Grant-at-Arms record."
            $refused += 1
        }
    }
    catch {
        Write-Warning "Refused to use invalid process record $recordPath."
        $refused += 1
    }
    finally {
        if (Test-Path -LiteralPath $recordPath) { Remove-Item -LiteralPath $recordPath -Force }
    }
}

foreach ($legacy in @("app.pid", "llama.pid")) {
    $legacyPath = Join-Path $PidDir $legacy
    if (Test-Path -LiteralPath $legacyPath) {
        Remove-Item -LiteralPath $legacyPath -Force
        Write-Warning "Removed an old PID-only record without stopping a process."
    }
}

Write-Host "Stopped $stopped verified Grant-at-Arms process(es). Refused $refused unverified record(s)."

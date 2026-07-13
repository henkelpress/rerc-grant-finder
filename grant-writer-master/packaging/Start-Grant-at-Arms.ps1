param(
    [switch]$DryRun,
    [switch]$AcceptGemmaTerms,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$RuntimeDir = Join-Path $Here "runtime"
$LlamaDir = Join-Path $RuntimeDir "llama"
$LlamaExe = Join-Path $LlamaDir "llama-server.exe"
$AppExe = Join-Path $Here "GrantAtArms.exe"
$IntegrityPath = Join-Path $Here "file_integrity.json"
$ModelDir = Join-Path $Here "models"
$ModelName = "gemma-3-1b-it-Q4_K_M.gguf"
$ModelPath = Join-Path $ModelDir $ModelName
$ModelUrl = "https://huggingface.co/ggml-org/gemma-3-1b-it-GGUF/resolve/main/gemma-3-1b-it-Q4_K_M.gguf?download=true"
$ModelBytes = 806058240
$ModelSha256 = "8ccc5cd1f1b3602548715ae25a66ed73fd5dc68a210412eea643eb20eb75a135"
$LogDir = Join-Path $RuntimeDir "logs"
$PidDir = Join-Path $RuntimeDir "pids"
$AppUrl = "http://127.0.0.1:8789"
$AppHealthUrl = "$AppUrl/health"
$ModelHealthUrl = "http://127.0.0.1:8788/health"
$ModelListUrl = "http://127.0.0.1:8788/v1/models"
$VcRuntimeUrl = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
$VcRuntimeFiles = @("MSVCP140.dll", "VCRUNTIME140.dll", "VCRUNTIME140_1.dll")

function Get-Sha256 {
    param([string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Test-VcRuntime {
    foreach ($name in $VcRuntimeFiles) {
        if (-not (Test-Path -LiteralPath (Join-Path $env:WINDIR "System32\$name") -PathType Leaf)) {
            return $false
        }
    }
    return $true
}

function Install-VcRuntime {
    Write-Host "Grant-at-Arms needs the standard Microsoft Visual C++ runtime."
    Write-Host "Windows may ask for permission while the official Microsoft installer runs."
    $installer = Join-Path $env:TEMP "Grant-at-Arms-vc_redist.x64.exe"
    $curl = Get-DownloadClient
    & $curl -L --fail --retry 3 --output $installer $VcRuntimeUrl
    if ($LASTEXITCODE -ne 0) { throw "The Microsoft runtime download failed." }
    $signature = Get-AuthenticodeSignature -LiteralPath $installer
    if ($signature.Status -ne "Valid" -or [string]$signature.SignerCertificate.Subject -notmatch "Microsoft Corporation") {
        Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue
        throw "The Microsoft runtime installer did not have a valid Microsoft signature."
    }
    $process = Start-Process -FilePath $installer -ArgumentList @("/install", "/quiet", "/norestart") -Verb RunAs -Wait -PassThru
    Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue
    if ($process.ExitCode -notin @(0, 1638, 3010)) {
        throw "The Microsoft runtime installer returned exit code $($process.ExitCode)."
    }
    if (-not (Test-VcRuntime)) {
        throw "The Microsoft runtime is still unavailable after installation."
    }
}

function Assert-FileIntegrity {
    if (-not (Test-Path -LiteralPath $IntegrityPath -PathType Leaf)) {
        throw "file_integrity.json is missing. Extract the full ZIP again."
    }
    $manifest = Get-Content -LiteralPath $IntegrityPath -Raw | ConvertFrom-Json
    foreach ($entry in $manifest.files) {
        $path = Join-Path $Here ([string]$entry.path)
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "A required package file is missing: $($entry.path)"
        }
        if ((Get-Sha256 -Path $path) -ne ([string]$entry.sha256).ToLowerInvariant()) {
            throw "A required package file failed its SHA-256 check: $($entry.path). Extract a fresh copy of the ZIP."
        }
    }
}

function Test-AppEndpoint {
    try {
        $response = Invoke-RestMethod -Uri $AppHealthUrl -TimeoutSec 3
        return ($response.status -eq "ok" -and $response.app -eq "Grant-at-Arms" -and $response.version -eq "0.2.3")
    }
    catch { return $false }
}

function Test-ModelEndpoint {
    try {
        $health = Invoke-RestMethod -Uri $ModelHealthUrl -TimeoutSec 3
        $models = Invoke-RestMethod -Uri $ModelListUrl -TimeoutSec 3
        if ($health.status -ne "ok") { return $false }
        foreach ($item in $models.data) {
            if ([string]$item.id -like "*$ModelName*") { return $true }
        }
        return $false
    }
    catch { return $false }
}

function Test-LocalPort {
    param([int]$Port)
    $client = [Net.Sockets.TcpClient]::new()
    try {
        $attempt = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        if (-not $attempt.AsyncWaitHandle.WaitOne(600)) { return $false }
        $client.EndConnect($attempt)
        return $true
    }
    catch { return $false }
    finally { $client.Dispose() }
}

function Write-ProcessRecord {
    param([string]$Name, [Diagnostics.Process]$Process, [string]$ExpectedPath)
    $Process.Refresh()
    $record = [ordered]@{
        pid = $Process.Id
        executable_path = [IO.Path]::GetFullPath($ExpectedPath)
        start_time_utc = $Process.StartTime.ToUniversalTime().ToString("o")
    }
    $json = $record | ConvertTo-Json
    [IO.File]::WriteAllText((Join-Path $PidDir "$Name.json"), $json, [Text.UTF8Encoding]::new($false))
}

function Get-DownloadClient {
    $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
    if ($curl) { return $curl.Source }
    throw "Windows curl.exe was not found. Install current Windows updates, then try again."
}

Assert-FileIntegrity
[IO.Directory]::CreateDirectory($ModelDir) | Out-Null
[IO.Directory]::CreateDirectory($LogDir) | Out-Null
[IO.Directory]::CreateDirectory($PidDir) | Out-Null
$vcRuntimeReady = Test-VcRuntime

$modelReady = $false
if (Test-Path -LiteralPath $ModelPath -PathType Leaf) {
    $modelReady = ((Get-Item -LiteralPath $ModelPath).Length -eq $ModelBytes) -and ((Get-Sha256 -Path $ModelPath) -eq $ModelSha256)
    if (-not $modelReady) {
        $rejected = "$ModelPath.rejected-$(Get-Date -Format yyyyMMdd-HHmmss)"
        Move-Item -LiteralPath $ModelPath -Destination $rejected
        Write-Warning "The existing model failed its integrity check and was moved to $rejected"
    }
}

if ($DryRun) {
    [pscustomobject]@{
        status = "PASS"
        package_integrity = $true
        app_exe = (Test-Path -LiteralPath $AppExe -PathType Leaf)
        llama_runtime = (Test-Path -LiteralPath $LlamaExe -PathType Leaf)
        model_ready = $modelReady
        microsoft_runtime_ready = $vcRuntimeReady
        model_download_bytes = $ModelBytes
        app_url = $AppUrl
    } | ConvertTo-Json
    exit 0
}

if (-not $vcRuntimeReady) {
    Install-VcRuntime
}

if (-not $modelReady) {
    Write-Host "Grant-at-Arms needs the Gemma 3 1B local writing model."
    Write-Host "The first download is about 806 MB. It stays in this folder."
    Write-Host "Gemma Terms: https://ai.google.dev/gemma/terms"
    Write-Host "Gemma Prohibited Use Policy: https://ai.google.dev/gemma/prohibited_use_policy"
    $accepted = $AcceptGemmaTerms -or ($env:GRANT_AT_ARMS_ACCEPT_GEMMA_TERMS -eq "1")
    if (-not $accepted) {
        $answer = Read-Host "Download Gemma and continue? Type Y to agree"
        $accepted = $answer -match "^[Yy]$"
    }
    if (-not $accepted) {
        Write-Host "Setup stopped. No model was downloaded."
        exit 0
    }
    $partial = "$ModelPath.partial"
    if (Test-Path -LiteralPath $partial) { Remove-Item -LiteralPath $partial -Force }
    Write-Host "Downloading the local model..."
    $curl = Get-DownloadClient
    & $curl -L --fail --retry 3 --progress-bar --output $partial $ModelUrl
    if ($LASTEXITCODE -ne 0) { throw "The model download failed." }
    Write-Host "Checking the model file..."
    if ((Get-Sha256 -Path $partial) -ne $ModelSha256) {
        Remove-Item -LiteralPath $partial -Force
        throw "The model file did not pass its SHA-256 check. It was removed."
    }
    Move-Item -LiteralPath $partial -Destination $ModelPath -Force
}

if (-not (Test-ModelEndpoint)) {
    if (Test-LocalPort -Port 8788) {
        throw "Port 8788 is already used by a different service. Close that service and start Grant-at-Arms again."
    }
    Write-Host "Starting the local Gemma writer..."
    $threads = [Math]::Max(2, [Math]::Min(8, [Environment]::ProcessorCount - 1))
    $llamaOut = Join-Path $LogDir "llama.out.log"
    $llamaErr = Join-Path $LogDir "llama.err.log"
    $llamaArgs = @("-m", ('"' + $ModelPath + '"'), "--host", "127.0.0.1", "--port", "8788", "-c", "8192", "-t", "$threads")
    $llama = Start-Process -FilePath $LlamaExe -ArgumentList $llamaArgs -WorkingDirectory $LlamaDir -WindowStyle Hidden -RedirectStandardOutput $llamaOut -RedirectStandardError $llamaErr -PassThru
    Write-ProcessRecord -Name "llama" -Process $llama -ExpectedPath $LlamaExe
    $deadline = (Get-Date).AddSeconds(120)
    while ((Get-Date) -lt $deadline -and -not (Test-ModelEndpoint)) { Start-Sleep -Seconds 2 }
    if (-not (Test-ModelEndpoint)) { throw "The local Gemma writer did not start. See runtime\logs\llama.err.log." }
}

if (-not (Test-AppEndpoint)) {
    if (Test-LocalPort -Port 8789) {
        throw "Port 8789 is already used by a different service. Close that service and start Grant-at-Arms again."
    }
    Write-Host "Starting Grant-at-Arms..."
    $env:GRANT_AT_ARMS_LOCAL_CHAT_URL = "http://127.0.0.1:8788/v1/chat/completions"
    $env:GRANT_AT_ARMS_LOCAL_HEALTH_URL = $ModelHealthUrl
    $env:GRANT_AT_ARMS_LOCAL_MODELS_URL = $ModelListUrl
    $appOut = Join-Path $LogDir "app.out.log"
    $appErr = Join-Path $LogDir "app.err.log"
    $app = Start-Process -FilePath $AppExe -ArgumentList @("--serve", "--host", "127.0.0.1", "--port", "8789") -WorkingDirectory $Here -WindowStyle Hidden -RedirectStandardOutput $appOut -RedirectStandardError $appErr -PassThru
    Write-ProcessRecord -Name "app" -Process $app -ExpectedPath $AppExe
    $deadline = (Get-Date).AddSeconds(30)
    while ((Get-Date) -lt $deadline -and -not (Test-AppEndpoint)) { Start-Sleep -Milliseconds 500 }
    if (-not (Test-AppEndpoint)) { throw "Grant-at-Arms did not start. See runtime\logs\app.err.log." }
}

Write-Host "Grant-at-Arms is ready at $AppUrl"
if (-not $NoBrowser) { Start-Process $AppUrl }

param(
    [switch]$AcceptRuntimeDownload,
    [string]$OutputDirectory = "",
    [string]$InnoCompiler = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $Here
Set-Location -LiteralPath $Here
$Version = "0.3.0"
$RuntimeName = "llama-b9987-bin-win-cpu-x64.zip"
$RuntimeUrl = "https://github.com/ggerganov/llama.cpp/releases/download/b9987/$RuntimeName"
$RuntimeSha256 = "6847d537b3cd5099051989d08c7eca4296e7a0f1755dbf0540c82e37768320f3"
$LicenseUrl = "https://raw.githubusercontent.com/ggml-org/llama.cpp/b9987/LICENSE"
$BuildRoot = Join-Path $Here "build\installer-$Version"
$CacheDir = Join-Path $Here "build-cache"
$ArchivePath = Join-Path $CacheDir $RuntimeName
$Extracted = Join-Path $BuildRoot "llama-extracted"
$PyInstallerRoot = Join-Path $BuildRoot "pyinstaller"
$PackageRoot = Join-Path $BuildRoot "RERCie"
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $Here "dist" }
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
$InstallerPath = Join-Path $OutputDirectory "RERCie-Setup.exe"
$Csc = "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if (-not $InnoCompiler) { $InnoCompiler = Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe" }

function Get-Sha256([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

$sourceQaPath = Join-Path $Here "packaging\QA_EVIDENCE.json"
$sourceQa = Get-Content -LiteralPath $sourceQaPath -Raw | ConvertFrom-Json
if ($sourceQa.status -ne "PASS") { throw "QA_EVIDENCE.json must have top-level PASS status before a release build." }
$requiredQaChecks = @("source_smoke", "native_launcher", "display_scaling", "installer_wizard", "package_integrity", "live_catalog", "local_generation", "docx_export", "api_privacy_regression", "service_identity_checks", "licensing_and_runtime")
foreach ($checkName in $requiredQaChecks) {
    $check = $sourceQa.checks.PSObject.Properties[$checkName]
    if (-not $check -or $check.Value.status -ne "PASS") { throw "Required QA check is not PASS: $checkName" }
}

python .\rercie.py --smoke
if ($LASTEXITCODE -ne 0) { throw "The RERCie source smoke test failed." }

$dirty = @(& git -C $RepoRoot status --porcelain)
if ($LASTEXITCODE -ne 0) { throw "Git status failed." }
if ($dirty.Count -gt 0) {
    throw "The release build requires a clean Git worktree. Commit the reviewed source, then build again."
}

if (Test-Path -LiteralPath $BuildRoot) { Remove-Item -LiteralPath $BuildRoot -Recurse -Force }
[IO.Directory]::CreateDirectory($BuildRoot) | Out-Null
[IO.Directory]::CreateDirectory($CacheDir) | Out-Null
[IO.Directory]::CreateDirectory($OutputDirectory) | Out-Null
[IO.Directory]::CreateDirectory($PackageRoot) | Out-Null

python -m PyInstaller --noconfirm --clean --distpath (Join-Path $PyInstallerRoot "dist") --workpath (Join-Path $PyInstallerRoot "work") .\RERCieService.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }

if (-not (Test-Path -LiteralPath $ArchivePath -PathType Leaf) -or (Get-Sha256 $ArchivePath) -ne $RuntimeSha256) {
    if (-not $AcceptRuntimeDownload) {
        throw "The pinned llama.cpp runtime is not cached. Build again with -AcceptRuntimeDownload."
    }
    curl.exe -L --fail --retry 3 --output $ArchivePath $RuntimeUrl
    if ($LASTEXITCODE -ne 0) { throw "The llama.cpp runtime download failed." }
}
if ((Get-Sha256 $ArchivePath) -ne $RuntimeSha256) { throw "The llama.cpp runtime archive failed its SHA-256 check." }

[IO.Directory]::CreateDirectory($Extracted) | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
[IO.Compression.ZipFile]::ExtractToDirectory($ArchivePath, $Extracted)
[IO.Directory]::CreateDirectory((Join-Path $PackageRoot "runtime\llama")) | Out-Null
$runtimeFiles = @(
    "llama-server.exe",
    "llama-server-impl.dll",
    "llama-common.dll",
    "llama.dll",
    "mtmd.dll",
    "ggml.dll",
    "ggml-base.dll",
    "libomp140.x86_64.dll"
)
foreach ($cpuDll in Get-ChildItem -LiteralPath $Extracted -Filter "ggml-cpu-*.dll" -File) { $runtimeFiles += $cpuDll.Name }
foreach ($name in $runtimeFiles | Select-Object -Unique) {
    $source = Join-Path $Extracted $name
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Required llama.cpp runtime file is missing: $name" }
    Copy-Item -LiteralPath $source -Destination (Join-Path $PackageRoot "runtime\llama\$name")
}
$ServiceSource = Join-Path $PyInstallerRoot "dist\RERCieService"
$ServiceDestination = Join-Path $PackageRoot "service"
if (-not (Test-Path -LiteralPath (Join-Path $ServiceSource "RERCieService.exe") -PathType Leaf)) { throw "The one-folder RERCie service build was not created." }
Copy-Item -LiteralPath $ServiceSource -Destination $ServiceDestination -Recurse

if (-not (Test-Path -LiteralPath $Csc -PathType Leaf)) { throw "The Windows C# compiler was not found at $Csc." }
$cscArgs = @(
    "/nologo", "/target:winexe", "/optimize+", "/platform:x64",
    "/out:$(Join-Path $PackageRoot 'RERCie.exe')",
    "/win32icon:$(Join-Path $RepoRoot 'assets\rercie.ico')",
    "/reference:System.dll", "/reference:System.Core.dll", "/reference:System.Drawing.dll",
    "/reference:System.Windows.Forms.dll", "/reference:System.Net.Http.dll",
    "/reference:System.Web.Extensions.dll", "/reference:System.Security.dll",
    (Join-Path $Here "packaging\RERCieLauncher.cs")
)
& $Csc @cscArgs
if ($LASTEXITCODE -ne 0) { throw "The native RERCie launcher build failed." }

$PythonRoot = (& python -c "import sys; print(sys.base_prefix)").Trim()
$PythonLicense = Join-Path $PythonRoot "LICENSE.txt"
if (-not (Test-Path -LiteralPath $PythonLicense -PathType Leaf)) { throw "The Python license file was not found at $PythonLicense." }
Copy-Item -LiteralPath $PythonLicense -Destination (Join-Path $PackageRoot "LICENSE-PYTHON.txt")
[IO.Directory]::CreateDirectory((Join-Path $PackageRoot "licenses")) | Out-Null
Copy-Item -LiteralPath (Join-Path $Here "licenses\LICENSE-QWEN.txt") -Destination (Join-Path $PackageRoot "licenses\LICENSE-QWEN.txt")
curl.exe -L --fail --retry 3 --output (Join-Path $PackageRoot "runtime\llama\LICENSE-llama.cpp") $LicenseUrl
if ($LASTEXITCODE -ne 0) { throw "The llama.cpp license download failed." }

foreach ($name in @("installer_manifest.json", "QA_EVIDENCE.json")) {
    Copy-Item -LiteralPath (Join-Path $Here "packaging\$name") -Destination $PackageRoot
}
foreach ($name in @("README.md", "MODEL_NOTICE.md", "THIRD_PARTY_NOTICES.md")) {
    Copy-Item -LiteralPath (Join-Path $Here $name) -Destination $PackageRoot
}
Copy-Item -LiteralPath (Join-Path $Here "examples") -Destination $PackageRoot -Recurse
Copy-Item -LiteralPath (Join-Path $Here "local_knowledge") -Destination $PackageRoot -Recurse
[IO.Directory]::CreateDirectory((Join-Path $PackageRoot "assets")) | Out-Null
Copy-Item -LiteralPath (Join-Path $RepoRoot "assets\rercie-otter.jpg") -Destination (Join-Path $PackageRoot "assets\rercie-otter.jpg")
Copy-Item -LiteralPath (Join-Path $RepoRoot "assets\ASSET_PROVENANCE.md") -Destination (Join-Path $PackageRoot "ASSET_PROVENANCE.md")

$integrityFiles = @(
    Get-Item -LiteralPath (Join-Path $PackageRoot "RERCie.exe")
    Get-ChildItem -LiteralPath (Join-Path $PackageRoot "service") -Recurse -File | Where-Object { $_.Extension -in @(".exe", ".dll", ".pyd") }
    Get-ChildItem -LiteralPath (Join-Path $PackageRoot "runtime\llama") -File | Where-Object { $_.Extension -in @(".exe", ".dll") }
)
$entries = foreach ($file in $integrityFiles) {
    $relative = $file.FullName.Substring($PackageRoot.Length + 1).Replace("\", "/")
    [ordered]@{ path = $relative; bytes = $file.Length; sha256 = Get-Sha256 $file.FullName }
}
$integrity = [ordered]@{
    app = "RERCie"
    version = $Version
    generated_utc = [DateTime]::UtcNow.ToString("o")
    files = @($entries)
}
$integrityPath = Join-Path $PackageRoot "file_integrity.json"
[IO.File]::WriteAllText($integrityPath, ($integrity | ConvertTo-Json -Depth 5), [Text.UTF8Encoding]::new($false))

$sourceCommit = (& git -C $RepoRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $sourceCommit -notmatch "^[0-9a-f]{40}$") { throw "The build must run from a Git checkout with a valid source commit." }
$qaPath = Join-Path $PackageRoot "QA_EVIDENCE.json"
$qa = Get-Content -LiteralPath $qaPath -Raw | ConvertFrom-Json
$qa.release_binding.source_commit = $sourceCommit
$qa.release_binding.integrity_manifest_sha256 = Get-Sha256 $integrityPath
$qa.release_binding | Add-Member -NotePropertyName built_utc -NotePropertyValue ([DateTime]::UtcNow.ToString("o")) -Force
$qa.release_binding | Add-Member -NotePropertyName worktree_clean -NotePropertyValue ($dirty.Count -eq 0) -Force
$qa.checks.package_integrity.integrity_checked_binaries = @($entries).Count
[IO.File]::WriteAllText($qaPath, ($qa | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))

$serviceQaPort = 18791
$serviceQaToken = ([Guid]::NewGuid().ToString("N") + [Guid]::NewGuid().ToString("N"))
$serviceQaExe = Join-Path $PackageRoot "service\RERCieService.exe"
$serviceQaProcess = $null
$serviceQaReady = $false
$oldSessionToken = $env:RERCIE_SESSION_TOKEN
$oldExpectedHost = $env:RERCIE_EXPECTED_HOST
$oldAppRoot = $env:RERCIE_APP_ROOT
try {
    $env:RERCIE_SESSION_TOKEN = $serviceQaToken
    $env:RERCIE_EXPECTED_HOST = "127.0.0.1:$serviceQaPort"
    $env:RERCIE_APP_ROOT = $PackageRoot
    $serviceQaProcess = Start-Process -FilePath $serviceQaExe -ArgumentList @("--serve", "--host", "127.0.0.1", "--port", "$serviceQaPort") -WorkingDirectory (Split-Path $serviceQaExe) -PassThru
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:$serviceQaPort/health" -Headers @{ "X-RERCie-Token" = $serviceQaToken } -TimeoutSec 2
            if ($health.status -eq "ok" -and $health.app -eq "RERCie") { $serviceQaReady = $true; break }
        } catch { }
        Start-Sleep -Milliseconds 500
    }
} finally {
    if ($serviceQaProcess -and -not $serviceQaProcess.HasExited) {
        Stop-Process -Id $serviceQaProcess.Id -Force -ErrorAction SilentlyContinue
        $serviceQaProcess.WaitForExit(10000)
    }
    $env:RERCIE_SESSION_TOKEN = $oldSessionToken
    $env:RERCIE_EXPECTED_HOST = $oldExpectedHost
    $env:RERCIE_APP_ROOT = $oldAppRoot
}
if (-not $serviceQaReady) { throw "The packaged authenticated RERCie service health check failed." }
if ($serviceQaProcess -and -not $serviceQaProcess.HasExited) { throw "The packaged RERCie service did not stop cleanly." }
$qa.checks.service_identity_checks.status = "PASS"
$qa.checks.service_identity_checks | Add-Member -NotePropertyName packaged_authenticated_health -NotePropertyValue $true -Force
[IO.File]::WriteAllText($qaPath, ($qa | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))

$smokePath = Join-Path $BuildRoot "launcher-smoke.json"
$smokeProcess = Start-Process -FilePath (Join-Path $PackageRoot "RERCie.exe") -ArgumentList @("--smoke-output", ('"' + $smokePath + '"')) -Wait -PassThru
if ($smokeProcess.ExitCode -ne 0) { throw "The native launcher smoke test failed." }
if (-not (Test-Path -LiteralPath $smokePath -PathType Leaf)) { throw "The native launcher smoke report was not created." }
$smoke = Get-Content -LiteralPath $smokePath -Raw | ConvertFrom-Json
if ($smoke.status -ne "PASS" -or $smoke.powershell_required -ne $false) { throw "The native launcher smoke report was not valid." }

if (-not (Test-Path -LiteralPath $InnoCompiler -PathType Leaf)) { throw "Inno Setup was not found at $InnoCompiler." }
if (Test-Path -LiteralPath $InstallerPath) { Remove-Item -LiteralPath $InstallerPath -Force }
& $InnoCompiler "/DSourceRoot=$PackageRoot" "/DOutputDir=$OutputDirectory" "/DAppVersion=$Version" (Join-Path $Here "packaging\RERCie.iss")
if ($LASTEXITCODE -ne 0) { throw "The RERCie installer build failed." }
if (-not (Test-Path -LiteralPath $InstallerPath -PathType Leaf)) { throw "The RERCie installer was not created." }

$signature = Get-AuthenticodeSignature -LiteralPath $InstallerPath
[pscustomobject]@{
    status = "PASS"
    version = $Version
    installer = $InstallerPath
    bytes = (Get-Item -LiteralPath $InstallerPath).Length
    sha256 = Get-Sha256 $InstallerPath
    signature_status = [string]$signature.Status
    powershell_required = $false
    integrity_files = @($entries).Count
    source_commit = $sourceCommit
    worktree_clean = ($dirty.Count -eq 0)
    launcher_smoke = $smokePath
} | ConvertTo-Json
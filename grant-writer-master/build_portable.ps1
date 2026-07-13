param(
    [switch]$AcceptRuntimeDownload,
    [string]$OutputDirectory = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $Here
$Version = "0.2.3"
$RuntimeName = "llama-b9987-bin-win-cpu-x64.zip"
$RuntimeUrl = "https://github.com/ggerganov/llama.cpp/releases/download/b9987/$RuntimeName"
$RuntimeSha256 = "6847d537b3cd5099051989d08c7eca4296e7a0f1755dbf0540c82e37768320f3"
$LicenseUrl = "https://raw.githubusercontent.com/ggml-org/llama.cpp/b9987/LICENSE"
$BuildRoot = Join-Path $Here "build\portable-$Version"
$CacheDir = Join-Path $Here "build-cache"
$ArchivePath = Join-Path $CacheDir $RuntimeName
$Extracted = Join-Path $BuildRoot "llama-extracted"
$PyInstallerRoot = Join-Path $BuildRoot "pyinstaller"
$PackageRoot = Join-Path $BuildRoot "Grant-at-Arms"
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $Here "dist" }
$ZipPath = Join-Path $OutputDirectory "grant-at-arms-local-writer.zip"

function Get-Sha256([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

python .\grant_at_arms.py --smoke
if ($LASTEXITCODE -ne 0) { throw "The source smoke test failed." }

if (Test-Path -LiteralPath $BuildRoot) { Remove-Item -LiteralPath $BuildRoot -Recurse -Force }
[IO.Directory]::CreateDirectory($BuildRoot) | Out-Null
[IO.Directory]::CreateDirectory($CacheDir) | Out-Null
[IO.Directory]::CreateDirectory($OutputDirectory) | Out-Null

python -m PyInstaller --noconfirm --clean --distpath (Join-Path $PyInstallerRoot "dist") --workpath (Join-Path $PyInstallerRoot "work") .\GrantAtArms.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }

if (-not (Test-Path -LiteralPath $ArchivePath -PathType Leaf) -or (Get-Sha256 $ArchivePath) -ne $RuntimeSha256) {
    if (-not $AcceptRuntimeDownload) {
        throw "The pinned llama.cpp runtime is not cached. Run again with -AcceptRuntimeDownload."
    }
    curl.exe -L --fail --retry 3 --output $ArchivePath $RuntimeUrl
    if ($LASTEXITCODE -ne 0) { throw "The llama.cpp runtime download failed." }
}
if ((Get-Sha256 $ArchivePath) -ne $RuntimeSha256) { throw "The llama.cpp runtime archive failed its SHA-256 check." }

[IO.Directory]::CreateDirectory($Extracted) | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
[IO.Compression.ZipFile]::ExtractToDirectory($ArchivePath, $Extracted)
[IO.Directory]::CreateDirectory((Join-Path $PackageRoot "runtime\llama")) | Out-Null
Copy-Item -Path (Join-Path $Extracted "*") -Destination (Join-Path $PackageRoot "runtime\llama") -Recurse
Copy-Item -LiteralPath (Join-Path $PyInstallerRoot "dist\GrantAtArms.exe") -Destination $PackageRoot

$PythonRoot = (& python -c "import sys; print(sys.base_prefix)").Trim()
$PythonLicense = Join-Path $PythonRoot "LICENSE.txt"
if (-not (Test-Path -LiteralPath $PythonLicense -PathType Leaf)) {
    throw "The Python license file was not found at $PythonLicense."
}
Copy-Item -LiteralPath $PythonLicense -Destination (Join-Path $PackageRoot "LICENSE-PYTHON.txt")
curl.exe -L --fail --retry 3 --output (Join-Path $PackageRoot "runtime\llama\LICENSE-llama.cpp") $LicenseUrl
if ($LASTEXITCODE -ne 0) { throw "The llama.cpp license download failed." }

foreach ($name in @("Start-Grant-at-Arms.cmd", "Start-Grant-at-Arms.ps1", "Stop-Grant-at-Arms.cmd", "Stop-Grant-at-Arms.ps1", "portable_manifest.json", "QA_EVIDENCE.json")) {
    Copy-Item -LiteralPath (Join-Path $Here "packaging\$name") -Destination $PackageRoot
}
foreach ($name in @("README.md", "MODEL_NOTICE.md", "THIRD_PARTY_NOTICES.md")) {
    Copy-Item -LiteralPath (Join-Path $Here $name) -Destination $PackageRoot
}
Copy-Item -LiteralPath (Join-Path $Here "examples") -Destination $PackageRoot -Recurse
Copy-Item -LiteralPath (Join-Path $Here "local_knowledge") -Destination $PackageRoot -Recurse

$integrityFiles = @(
    Get-Item -LiteralPath (Join-Path $PackageRoot "GrantAtArms.exe")
    Get-ChildItem -LiteralPath (Join-Path $PackageRoot "runtime\llama") -File | Where-Object { $_.Extension -in @(".exe", ".dll") }
)
$entries = foreach ($file in $integrityFiles) {
    $relative = $file.FullName.Substring($PackageRoot.Length + 1).Replace("\", "/")
    [ordered]@{ path = $relative; bytes = $file.Length; sha256 = Get-Sha256 $file.FullName }
}
$integrity = [ordered]@{
    app = "Grant-at-Arms"
    version = $Version
    generated_utc = [DateTime]::UtcNow.ToString("o")
    files = @($entries)
}
$integrityPath = Join-Path $PackageRoot "file_integrity.json"
$integrity | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $integrityPath -Encoding utf8

$sourceCommit = (& git -C $Here rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $sourceCommit -notmatch "^[0-9a-f]{40}$") {
    throw "The release build must run from a Git checkout with a valid source commit."
}
$qaPath = Join-Path $PackageRoot "QA_EVIDENCE.json"
$qa = Get-Content -LiteralPath $qaPath -Raw | ConvertFrom-Json
$qa.release_binding.source_commit = $sourceCommit
$qa.release_binding.integrity_manifest_sha256 = Get-Sha256 $integrityPath
$qa.release_binding | Add-Member -NotePropertyName built_utc -NotePropertyValue ([DateTime]::UtcNow.ToString("o")) -Force
$qa.checks.portable_integrity.integrity_checked_binaries = @($entries).Count
[IO.File]::WriteAllText($qaPath, ($qa | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))

if (Test-Path -LiteralPath $ZipPath) { Remove-Item -LiteralPath $ZipPath -Force }
$archive = [IO.Compression.ZipFile]::Open($ZipPath, [IO.Compression.ZipArchiveMode]::Create)
try {
    foreach ($file in Get-ChildItem -LiteralPath $PackageRoot -Recurse -File) {
        $relative = $file.FullName.Substring($PackageRoot.Length + 1).Replace("\", "/")
        [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $file.FullName, "Grant-at-Arms/$relative", [IO.Compression.CompressionLevel]::Optimal) | Out-Null
    }
}
finally { $archive.Dispose() }
[pscustomobject]@{
    status = "PASS"
    version = $Version
    zip = $ZipPath
    bytes = (Get-Item -LiteralPath $ZipPath).Length
    sha256 = Get-Sha256 $ZipPath
    integrity_files = @($entries).Count
} | ConvertTo-Json

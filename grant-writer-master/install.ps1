$ErrorActionPreference = "Stop"

$Model = if ($env:GRANT_AT_ARMS_MODEL) { $env:GRANT_AT_ARMS_MODEL } else { "gemma3:4b" }

Write-Host "Grant-at-Arms setup"
Write-Host "Checking Python..."

$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $Python) {
    throw "Python 3.10 or newer is required. Install Python, then run .\install.ps1 again."
}

python --version

Write-Host "Checking Ollama..."
$Ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $Ollama) {
    Write-Warning "Ollama was not found. Install Ollama, then run this script again."
    Start-Process "https://ollama.com/download"
    exit 0
}

ollama --version
Write-Host "Downloading local model: $Model"
ollama pull $Model

Write-Host "Setup complete."
Write-Host "Run .\run.ps1, then open http://127.0.0.1:8789"


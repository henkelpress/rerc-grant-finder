param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8789
)

$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Here

python .\grant_at_arms.py --serve --host $HostName --port $Port


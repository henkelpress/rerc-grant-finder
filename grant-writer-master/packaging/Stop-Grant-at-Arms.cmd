@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Stop-Grant-at-Arms.ps1"
if errorlevel 1 pause

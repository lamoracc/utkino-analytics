$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name UtkinoAnalytics `
    run_app.py

New-Item -ItemType Directory -Path "release" -Force | Out-Null
Copy-Item -LiteralPath "dist\UtkinoAnalytics.exe" -Destination "release\UtkinoAnalytics.exe" -Force
Copy-Item -LiteralPath "README_CUSTOMER.txt" -Destination "release\README.txt" -Force

Write-Host "Build complete: $root\release\UtkinoAnalytics.exe"


$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --hidden-import xlrd `
    --hidden-import openpyxl `
    --hidden-import et_xmlfile `
    --name HotelAnalytics `
    run_app.py

New-Item -ItemType Directory -Path "release" -Force | Out-Null
Copy-Item -LiteralPath "dist\HotelAnalytics.exe" -Destination "release\HotelAnalytics.exe" -Force
Copy-Item -LiteralPath "README_CUSTOMER.txt" -Destination "release\README.txt" -Force

Write-Host "Build complete: $root\release\HotelAnalytics.exe"

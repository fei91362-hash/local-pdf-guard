$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

& .\.venv\Scripts\pyinstaller.exe packaging\pyinstaller\LocalPDFGuard.spec --clean --noconfirm

$Zip = "dist\LocalPDFGuard-0.1.0-portable-win64.zip"
if (Test-Path $Zip) { Remove-Item $Zip -Force }
Compress-Archive -Path "dist\LocalPDFGuard\*" -DestinationPath $Zip
Write-Host $Zip


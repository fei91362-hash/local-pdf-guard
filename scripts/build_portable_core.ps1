$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

& .\.venv\Scripts\pyinstaller.exe packaging\pyinstaller\LocalPDFGuardCore.spec --clean --noconfirm

$Zip = "dist\LocalPDFGuardCore-0.1.0-portable-win64.zip"
if (Test-Path $Zip) { Remove-Item $Zip -Force }
Compress-Archive -Path "dist\LocalPDFGuardCore\*" -DestinationPath $Zip
Write-Host $Zip


$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (!(Test-Path "dist\LocalPDFGuard\LocalPDFGuard.exe")) {
  & powershell -ExecutionPolicy Bypass -File scripts\build_portable_gui.ps1
}

$Iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (!(Test-Path $Iscc)) {
  throw "ISCC.exe not found at $Iscc"
}

& $Iscc packaging\inno\LocalPDFGuard.iss
if ($LASTEXITCODE -ne 0) {
  throw "Inno Setup failed with exit code $LASTEXITCODE"
}
Write-Host "dist\LocalPDFGuard-0.1.0-setup-win64.exe"

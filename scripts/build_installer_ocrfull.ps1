$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

& powershell -ExecutionPolicy Bypass -File scripts\build_portable_gui_ocrfull.ps1
& powershell -ExecutionPolicy Bypass -File scripts\build_installer.ps1 -Edition "ocrfull"

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (Test-Path "requirements.ocr.lock.txt") {
  & .\.venv\Scripts\pip.exe install -r requirements.ocr.lock.txt
}

& powershell -ExecutionPolicy Bypass -File scripts\build_portable_gui.ps1 -Edition "ocrfull"

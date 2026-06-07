$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

& .\.venv\Scripts\python.exe scripts\generate_sample_pdf.py

$Output = "work\sample_guarded_flattened.pdf"
$Report = "work\sample_guarded_flattened_report.json"

if (Test-Path $Output) { Remove-Item $Output -Force }
if (Test-Path $Report) { Remove-Item $Report -Force }

& .\.venv\Scripts\python.exe -m pdf_guard process `
  --input work\sample_sensitive.pdf `
  --output $Output `
  --owner-password "owner-pass" `
  --watermark "内部资料 禁止外传" `
  --redact-mobile `
  --redact-id-card `
  --redact-email `
  --keyword "Alpha" `
  --flatten `
  --flatten-dpi 100 `
  --report-json $Report

if (!(Test-Path $Output)) {
  throw "Flatten smoke output PDF was not created."
}
if (!(Test-Path $Report)) {
  throw "Flatten smoke report JSON was not created."
}

& .\.venv\Scripts\python.exe -c "import json, pathlib; data=json.loads(pathlib.Path('work/sample_guarded_flattened_report.json').read_text(encoding='utf-8')); assert data['verification']['passed'], data; assert data['encrypted'], data; assert data['flattened'], data; print('flatten smoke passed')"


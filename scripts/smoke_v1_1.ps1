$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

& .\.venv\Scripts\python.exe -m pytest -q
& .\.venv\Scripts\python.exe scripts\generate_sample_pdf.py

$SingleOut = "work\smoke_v1_1_guarded.pdf"
$SingleReport = "work\smoke_v1_1_guarded.report.json"
if (Test-Path $SingleOut) { Remove-Item $SingleOut -Force }
if (Test-Path $SingleReport) { Remove-Item $SingleReport -Force }

& .\.venv\Scripts\python.exe -m pdf_guard process `
  --input work\sample_sensitive.pdf `
  --output $SingleOut `
  --owner-password "owner-pass" `
  --watermark "Internal Use Only" `
  --redact-mobile `
  --redact-id-card `
  --redact-email `
  --keyword Alpha `
  --report-json $SingleReport

$BatchDir = "work\smoke_batch"
$BatchOut = "work\smoke_batch_out"
if (!(Test-Path $BatchDir)) { New-Item -ItemType Directory -Path $BatchDir | Out-Null }
if (Test-Path $BatchOut) { Remove-Item $BatchOut -Recurse -Force }
Copy-Item work\sample_sensitive.pdf "$BatchDir\sample_a.pdf" -Force
Copy-Item work\sample_sensitive.pdf "$BatchDir\sample_b.pdf" -Force

& .\.venv\Scripts\python.exe -m pdf_guard batch `
  --input $BatchDir `
  --output-dir $BatchOut `
  --owner-password "owner-pass" `
  --redact-mobile `
  --redact-id-card `
  --redact-email `
  --keyword Alpha

& .\.venv\Scripts\python.exe -m pdf_guard --help
Write-Host "v1.1 smoke passed"

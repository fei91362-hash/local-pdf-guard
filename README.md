# Local PDF Guard

Windows local PDF redaction, watermark, flattening, permissions, OCR candidate detection, and batch processing tool.

## Status

Current development version: `1.1.0-dev`.

v1.1 adds:

- Editable redaction boxes in the GUI: select, drag, resize, delete.
- Output actions: open output file, open output folder, open report.
- Better page navigation, zoom, and scrolling.
- Optional local OCR provider abstraction with PaddleOCR support for OCR Full builds.
- Batch processing with per-file reports and a batch report.
- Stronger verification report with `PASS/WARN/FAIL`, permission status, and structure warnings.
- GitHub Actions release workflow for Windows portable and installer packages.

## Development

```powershell
py -3 -m venv .venv
.\.venv\Scripts\pip.exe install -r requirements.lock.txt
.\.venv\Scripts\pip.exe install -r requirements-dev.lock.txt
.\.venv\Scripts\pip.exe install -e .
.\.venv\Scripts\python.exe -m pytest -q
```

## CLI

Single file:

```powershell
.\.venv\Scripts\python.exe -m pdf_guard process `
  --input work\sample_sensitive.pdf `
  --output work\sample_guarded.pdf `
  --owner-password "change-me" `
  --watermark "Internal Use Only" `
  --redact-mobile `
  --redact-id-card `
  --redact-email `
  --report-json work\sample_guarded.report.json
```

Batch:

```powershell
.\.venv\Scripts\python.exe -m pdf_guard batch `
  --input work\batch `
  --output-dir work\batch_out `
  --owner-password "change-me" `
  --redact-mobile `
  --recursive
```

## GUI

```powershell
.\.venv\Scripts\python.exe -m pdf_guard.gui
```

Portable GUI build:

```powershell
.\scripts\build_portable_gui.ps1 -Edition standard
```

OCR Full build requires `requirements.ocr.lock.txt` dependencies and local PaddleOCR model files to be available before packaging.

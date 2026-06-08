# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

ROOT = Path.cwd()
EDITION = os.environ.get("LOCAL_PDF_GUARD_EDITION", "standard").lower()
datas = []
excludes = []
if EDITION == "ocrfull":
    cache_dir = ROOT / "vendor" / "ocr_cache"
    models_dir = ROOT / "vendor" / "ocr_models"
    if cache_dir.exists():
        datas.append((str(cache_dir), "vendor/ocr_cache"))
    if models_dir.exists():
        datas.append((str(models_dir), "vendor/ocr_models"))
else:
    excludes = [
        "paddle",
        "paddleocr",
        "paddlex",
        "cv2",
        "numpy",
        "pandas",
        "modelscope",
        "huggingface_hub",
    ]

a = Analysis(
    [str(ROOT / "scripts" / "local_pdf_guard_gui_launcher.py")],
    pathex=[str(ROOT / "src"), str(ROOT / "scripts")],
    binaries=[],
    datas=datas,
    hiddenimports=["pymupdf", "pikepdf", "PIL._tkinter_finder"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LocalPDFGuard",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="LocalPDFGuard",
)

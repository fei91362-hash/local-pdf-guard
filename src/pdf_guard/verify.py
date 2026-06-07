from __future__ import annotations

from pathlib import Path

from .models import VerificationResult
from .pdf_core import open_document
from .rules import Rule, find_sensitive_values
from .security import inspect_pdf_structure, is_encrypted


def extract_text(path: Path, password: str | None = "") -> str:
    doc = open_document(path, password)
    try:
        return "\n".join(page.get_text("text") for page in doc)
    finally:
        doc.close()


def verify_output(
    path: Path,
    rules: list[Rule],
    keywords: list[str],
    password: str | None = "",
    expect_encrypted: bool = True,
    verify_ocr: bool = False,
) -> VerificationResult:
    notes: list[str] = []
    structure_warnings: list[str] = []
    structure_status: dict[str, bool] = {}
    ocr_hits: dict[str, list[str]] = {}
    try:
        text = extract_text(path, password)
        residual_hits = find_sensitive_values(text, rules, keywords)
    except Exception as exc:
        residual_hits = {}
        notes.append(f"Text extraction failed: {exc}")

    encrypted = False
    try:
        encrypted = is_encrypted(path, password)
    except Exception as exc:
        notes.append(f"Encryption check failed: {exc}")

    try:
        structure_warnings, structure_status = inspect_pdf_structure(path, password)
    except Exception as exc:
        notes.append(f"Structure inspection failed: {exc}")

    if verify_ocr:
        try:
            from .ocr.detectors import detect_sensitive_ocr_candidates
            from .ocr.provider import get_default_ocr_provider

            provider = get_default_ocr_provider()
            if provider.is_available():
                ocr_hits = detect_sensitive_ocr_candidates(path, provider, rules, keywords, password=password)
            else:
                notes.append("OCR verification skipped: no local OCR provider is available.")
        except Exception as exc:
            notes.append(f"OCR verification failed: {exc}")

    permission_status = {
        "encrypted": encrypted,
        "expected_encrypted": expect_encrypted,
        "permissions_checked": encrypted,
        **structure_status,
    }
    failed = bool(residual_hits) or bool(ocr_hits) or (expect_encrypted and not encrypted)
    risk_level = "FAIL" if failed else ("WARN" if structure_warnings or notes else "PASS")
    passed = risk_level == "PASS"
    return VerificationResult(
        passed=passed,
        residual_hits=residual_hits,
        encrypted=encrypted,
        permissions_checked=encrypted,
        notes=notes,
        risk_level=risk_level,
        ocr_hits=ocr_hits,
        structure_warnings=structure_warnings,
        permission_status=permission_status,
    )


def verification_to_dict(result: VerificationResult) -> dict:
    return {
        "passed": result.passed,
        "risk_level": result.risk_level,
        "residual_hits": result.residual_hits,
        "ocr_hits": result.ocr_hits,
        "encrypted": result.encrypted,
        "permissions_checked": result.permissions_checked,
        "permission_status": result.permission_status,
        "structure_warnings": result.structure_warnings,
        "sanitized_items": result.sanitized_items,
        "notes": result.notes,
    }

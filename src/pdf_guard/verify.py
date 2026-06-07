from __future__ import annotations

from pathlib import Path

from .models import VerificationResult
from .pdf_core import open_document
from .rules import Rule, find_sensitive_values
from .security import is_encrypted


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
) -> VerificationResult:
    notes: list[str] = []
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

    passed = not residual_hits and (encrypted if expect_encrypted else True)
    return VerificationResult(
        passed=passed,
        residual_hits=residual_hits,
        encrypted=encrypted,
        permissions_checked=encrypted,
        notes=notes,
    )


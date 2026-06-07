from __future__ import annotations

from pathlib import Path

from .models import ProcessOptions, ProcessReport
from .pdf_core import build_intermediate_pdf
from .rules import Rule
from .security import encrypt_with_permissions
from .verify import verify_output


def process_pdf(options: ProcessOptions, rules_for_verify: list[Rule], keywords_for_verify: list[str]) -> ProcessReport:
    intermediate_path, pages = build_intermediate_pdf(options)
    try:
        encrypt_with_permissions(
            intermediate_path,
            options.output_path,
            owner_password=options.owner_password,
            user_password=options.user_password,
            permissions=options.permissions,
        )
    finally:
        try:
            intermediate_path.unlink()
        except FileNotFoundError:
            pass

    verification = verify_output(
        options.output_path,
        rules_for_verify,
        keywords_for_verify,
        password=options.user_password,
        expect_encrypted=True,
    )
    return ProcessReport(
        output_path=options.output_path,
        pages=pages,
        redaction_count=len(options.boxes),
        watermark_applied=bool(options.watermark.text),
        flattened=options.flatten,
        encrypted=verification.encrypted,
        verification=verification,
    )


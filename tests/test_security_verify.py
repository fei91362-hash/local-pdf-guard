from pathlib import Path

import fitz

from pdf_guard.models import PermissionOptions, ProcessOptions, WatermarkOptions
from pdf_guard.pipeline import process_pdf
from pdf_guard.rules import selected_rules


def test_output_security_report_contains_risk_level_and_structure_status(tmp_path: Path):
    input_path = tmp_path / "meta.pdf"
    output_path = tmp_path / "meta_guarded.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 120), "电话 13812345678", fontsize=14)
    doc.set_metadata({"title": "secret title"})
    doc.save(input_path)
    doc.close()

    rules = selected_rules(redact_mobile=True)
    from pdf_guard.pdf_core import detect_redactions

    _, boxes = detect_redactions(input_path, rules, [])
    report = process_pdf(
        ProcessOptions(
            input_path=input_path,
            output_path=output_path,
            owner_password="owner-pass",
            boxes=boxes,
            watermark=WatermarkOptions(text=""),
            permissions=PermissionOptions(),
        ),
        rules,
        [],
    )

    assert report.verification.risk_level in {"PASS", "WARN"}
    assert report.verification.permission_status["encrypted"] is True
    assert not report.verification.residual_hits

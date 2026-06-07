from pathlib import Path

import fitz

from pdf_guard.models import PermissionOptions, ProcessOptions, WatermarkOptions
from pdf_guard.pdf_core import detect_redactions
from pdf_guard.pipeline import process_pdf
from pdf_guard.rules import selected_rules
from pdf_guard.verify import extract_text


def _make_sample_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 120), "客户手机号 13812345678", fontsize=14)
    page.insert_text((72, 150), "身份证 110101199001011234", fontsize=14)
    page.insert_text((72, 180), "邮箱 demo@example.com", fontsize=14)
    page.insert_text((72, 210), "项目代号 Alpha", fontsize=14)
    doc.save(path)
    doc.close()


def test_process_pdf_redacts_watermarks_encrypts_and_verifies(tmp_path):
    input_path = tmp_path / "sample.pdf"
    output_path = tmp_path / "sample_guarded.pdf"
    _make_sample_pdf(input_path)

    rules = selected_rules(redact_mobile=True, redact_id_card=True, redact_email=True)
    keywords = ["Alpha"]
    detections, boxes = detect_redactions(input_path, rules, keywords)

    assert len(detections) == 4
    assert len(boxes) == 4

    options = ProcessOptions(
        input_path=input_path,
        output_path=output_path,
        owner_password="owner-pass",
        boxes=boxes,
        watermark=WatermarkOptions(text="内部资料 禁止外传", font_size=24, opacity=0.25, tile=False),
        flatten=False,
        permissions=PermissionOptions(),
    )
    report = process_pdf(options, rules, keywords)

    assert output_path.exists()
    assert report.verification.passed
    assert report.encrypted

    text = extract_text(output_path)
    assert "13812345678" not in text
    assert "110101199001011234" not in text
    assert "demo@example.com" not in text
    assert "Alpha" not in text
    assert "内部资料" in text


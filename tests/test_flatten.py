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
    page.insert_text((72, 120), "电话 13812345678", fontsize=14)
    doc.save(path)
    doc.close()


def test_flatten_mode_outputs_pdf_without_sensitive_text_layer(tmp_path):
    input_path = tmp_path / "sample.pdf"
    output_path = tmp_path / "sample_flattened.pdf"
    _make_sample_pdf(input_path)

    rules = selected_rules(redact_mobile=True)
    detections, boxes = detect_redactions(input_path, rules, [])
    assert detections

    options = ProcessOptions(
        input_path=input_path,
        output_path=output_path,
        owner_password="owner-pass",
        boxes=boxes,
        watermark=WatermarkOptions(text="内部资料", font_size=24, opacity=0.25, tile=False),
        flatten=True,
        flatten_dpi=100,
        permissions=PermissionOptions(),
    )
    report = process_pdf(options, rules, [])

    assert output_path.exists()
    assert report.verification.passed
    assert "13812345678" not in extract_text(output_path)


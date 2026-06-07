from pathlib import Path

import fitz

from pdf_guard.batch.runner import BatchOptions, BatchRunner
from pdf_guard.models import PermissionOptions, ProcessOptions, WatermarkOptions
from pdf_guard.rules import selected_rules


def _make_pdf(path: Path, text: str) -> None:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 120), text, fontsize=14)
    doc.save(path)
    doc.close()


def test_batch_runner_continues_after_failed_file(tmp_path: Path):
    input_dir = tmp_path / "inputs"
    output_dir = tmp_path / "outputs"
    input_dir.mkdir()
    good = input_dir / "good.pdf"
    broken = input_dir / "broken.pdf"
    _make_pdf(good, "电话 13812345678")
    broken.write_bytes(b"not a pdf")

    rules = selected_rules(redact_mobile=True)
    options = ProcessOptions(
        input_path=good,
        output_path=output_dir / "placeholder.pdf",
        owner_password="owner-pass",
        watermark=WatermarkOptions(text=""),
        permissions=PermissionOptions(),
    )
    report = BatchRunner(
        BatchOptions(
            input_paths=[good, broken],
            output_dir=output_dir,
            process_options=options,
            rules=rules,
            keywords=[],
            continue_on_error=True,
        )
    ).run()

    assert report.total == 2
    assert report.success == 1
    assert report.failed == 1
    assert (output_dir / "good_guarded.pdf").exists()
    assert (output_dir / "batch.report.json").exists()

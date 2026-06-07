from pathlib import Path

import fitz
from PIL import Image

from pdf_guard.models import ProcessOptions, RedactionBox, WatermarkOptions
from pdf_guard.pipeline import process_pdf


def _make_image_pdf(path: Path) -> None:
    image_path = path.with_suffix(".png")
    image = Image.new("RGB", (200, 200), "white")
    for x in range(50, 150):
        for y in range(50, 150):
            image.putpixel((x, y), (220, 20, 20))
    image.save(image_path)

    doc = fitz.open()
    page = doc.new_page(width=200, height=200)
    page.insert_image(page.rect, filename=image_path)
    doc.save(path)
    doc.close()


def test_manual_redaction_blanks_image_pixels(tmp_path):
    input_path = tmp_path / "image_scan.pdf"
    output_path = tmp_path / "image_scan_guarded.pdf"
    _make_image_pdf(input_path)

    options = ProcessOptions(
        input_path=input_path,
        output_path=output_path,
        owner_password="owner-pass",
        boxes=[
            RedactionBox(
                page_index=0,
                rect=(60, 60, 140, 140),
                source="manual",
                category="manual",
                label="manual",
            )
        ],
        watermark=WatermarkOptions(text=""),
        flatten=False,
    )
    report = process_pdf(options, [], [])
    assert report.verification.passed

    doc = fitz.open(output_path)
    page = doc[0]
    pix = page.get_pixmap(alpha=False)
    doc.close()

    center = pix.pixel(100, 100)
    outside = pix.pixel(30, 30)
    assert center == (0, 0, 0)
    assert outside == (255, 255, 255)


from __future__ import annotations

from pathlib import Path

import fitz

from pdf_guard.ocr.detectors import detect_ocr_redaction_boxes
from pdf_guard.ocr.provider import get_default_ocr_provider


def make_scan_like_pdf(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    # Rasterize the source page into an image PDF so the text layer is absent.
    page.insert_text((72, 120), "Mobile 13812345678", fontsize=24)
    page.insert_text((72, 170), "ID 110101199001011234", fontsize=24)
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    image_path = path.with_suffix(".png")
    pix.save(image_path)
    out = fitz.open()
    out_page = out.new_page(width=595, height=842)
    out_page.insert_image(out_page.rect, filename=image_path)
    out.save(path)
    out.close()
    doc.close()


def main() -> int:
    pdf_path = Path("work/ocr_smoke_scan.pdf")
    make_scan_like_pdf(pdf_path)
    provider = get_default_ocr_provider()
    print(f"provider={provider.name} available={provider.is_available()}")
    if not provider.is_available():
        return 2
    candidates, boxes = detect_ocr_redaction_boxes(pdf_path, provider, dpi=160)
    print(f"candidates={len(candidates)} boxes={len(boxes)}")
    for item in candidates[:10]:
        print(item.category, item.text, item.confidence, tuple(round(v, 2) for v in item.rect_pdf))
    categories = {item.category for item in candidates}
    return 0 if {"mobile", "id_card"} & categories else 1


if __name__ == "__main__":
    raise SystemExit(main())

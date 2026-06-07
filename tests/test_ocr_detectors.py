from pathlib import Path

import fitz

from pdf_guard.ocr.detectors import detect_candidates_from_blocks, detect_ocr_redaction_boxes
from pdf_guard.ocr.models import OcrBlock, OcrPageInput


class FakeProvider:
    name = "fake"

    def is_available(self):
        return True

    def recognize_page(self, page):
        return [
            OcrBlock(page_index=page.page_index, text="电话 13812345678", bbox_px=(100, 100, 260, 130), confidence=0.98, engine="fake"),
            OcrBlock(page_index=page.page_index, text="姓名: 张三", bbox_px=(100, 150, 220, 180), confidence=0.9, engine="fake"),
            OcrBlock(page_index=page.page_index, text="联系地址 北京市朝阳区测试路1号", bbox_px=(100, 200, 420, 230), confidence=0.88, engine="fake"),
        ]


def test_detect_candidates_from_ocr_blocks_maps_categories():
    page = OcrPageInput(
        page_index=0,
        image_path="page.png",
        image_width=1000,
        image_height=2000,
        pdf_width=500,
        pdf_height=1000,
        render_dpi=200,
    )
    blocks = [
        OcrBlock(page_index=0, text="电话 13812345678", bbox_px=(100, 100, 260, 130), confidence=0.98, engine="fake"),
        OcrBlock(page_index=0, text="身份证 110101199001011234", bbox_px=(100, 140, 360, 170), confidence=0.96, engine="fake"),
        OcrBlock(page_index=0, text="姓名: 张三", bbox_px=(100, 180, 220, 210), confidence=0.9, engine="fake"),
        OcrBlock(page_index=0, text="联系地址 北京市朝阳区测试路1号", bbox_px=(100, 220, 420, 250), confidence=0.88, engine="fake"),
    ]

    candidates = detect_candidates_from_blocks(blocks, page)
    categories = {item.category for item in candidates}

    assert {"mobile", "id_card", "name", "address"}.issubset(categories)
    mobile = next(item for item in candidates if item.category == "mobile")
    assert mobile.rect_pdf == (50, 50, 130, 65)


def test_detect_ocr_redaction_boxes_uses_provider(tmp_path: Path):
    pdf_path = tmp_path / "scan.pdf"
    doc = fitz.open()
    doc.new_page(width=500, height=700)
    doc.save(pdf_path)
    doc.close()

    candidates, boxes = detect_ocr_redaction_boxes(pdf_path, FakeProvider(), dpi=100)

    assert {item.category for item in candidates} >= {"mobile", "name", "address"}
    assert {box.source for box in boxes} == {"ocr"}
    assert any(box.category == "mobile" and box.confirmed for box in boxes)
    assert any(box.category == "name" and not box.confirmed for box in boxes)

from pdf_guard.models import RedactionBox
from pdf_guard.ui.app import _normalize_rect, _replace_box_rect


def test_normalize_rect_orders_coordinates():
    assert _normalize_rect((10, 40, 2, 3)) == (2, 3, 10, 40)


def test_replace_box_rect_preserves_metadata():
    box = RedactionBox(page_index=1, rect=(1, 2, 3, 4), source="ocr", category="mobile", label="13***78", id="box-1", confirmed=False)
    updated = _replace_box_rect(box, (5, 6, 7, 8))

    assert updated.rect == (5, 6, 7, 8)
    assert updated.id == "box-1"
    assert updated.source == "ocr"
    assert updated.confirmed is False

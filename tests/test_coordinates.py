from pdf_guard.ui.coordinates import canvas_to_pdf_rect, pdf_to_canvas_rect


def test_canvas_to_pdf_rect_normalizes_drag_direction():
    rect = canvas_to_pdf_rect((240, 120), (120, 60), 2.0)
    assert rect == (60, 30, 120, 60)


def test_pdf_to_canvas_rect_scales_values():
    rect = pdf_to_canvas_rect((10, 20, 30, 40), 1.5)
    assert rect == (15, 30, 45, 60)


from __future__ import annotations


def canvas_to_pdf_rect(start: tuple[float, float], end: tuple[float, float], zoom: float) -> tuple[float, float, float, float]:
    x0, y0 = start
    x1, y1 = end
    left = min(x0, x1) / zoom
    top = min(y0, y1) / zoom
    right = max(x0, x1) / zoom
    bottom = max(y0, y1) / zoom
    return (left, top, right, bottom)


def pdf_to_canvas_rect(rect: tuple[float, float, float, float], zoom: float) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = rect
    return (x0 * zoom, y0 * zoom, x1 * zoom, y1 * zoom)


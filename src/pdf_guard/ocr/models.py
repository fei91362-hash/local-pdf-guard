from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OcrPageInput:
    page_index: int
    image_path: str
    image_width: int
    image_height: int
    pdf_width: float
    pdf_height: float
    render_dpi: int


@dataclass(frozen=True)
class OcrBlock:
    page_index: int
    text: str
    bbox_px: tuple[float, float, float, float]
    confidence: float
    engine: str


@dataclass(frozen=True)
class OcrCandidate:
    page_index: int
    text: str
    category: str
    rect_pdf: tuple[float, float, float, float]
    confidence: float
    reason: str

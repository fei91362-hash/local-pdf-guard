from __future__ import annotations

import tempfile
from pathlib import Path

import fitz
from PIL import Image

from ..pdf_core import open_document
from .models import OcrPageInput


def render_page_for_ocr(
    pdf_path: Path,
    page_index: int,
    password: str | None = None,
    dpi: int = 200,
    temp_dir: Path | None = None,
) -> OcrPageInput:
    target_dir = temp_dir or Path(tempfile.mkdtemp(prefix="local_pdf_guard_ocr_"))
    target_dir.mkdir(parents=True, exist_ok=True)
    image_path = target_dir / f"page_{page_index + 1:04d}_{dpi}dpi.png"
    doc = open_document(pdf_path, password)
    try:
        page = doc[page_index]
        matrix = fitz.Matrix(dpi / 72.0, dpi / 72.0)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        image.save(image_path)
        return OcrPageInput(
            page_index=page_index,
            image_path=str(image_path),
            image_width=image.width,
            image_height=image.height,
            pdf_width=float(page.rect.width),
            pdf_height=float(page.rect.height),
            render_dpi=dpi,
        )
    finally:
        doc.close()


def image_bbox_to_pdf_rect(
    bbox_px: tuple[float, float, float, float],
    page: OcrPageInput,
) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = bbox_px
    scale_x = page.pdf_width / page.image_width
    scale_y = page.pdf_height / page.image_height
    return (x0 * scale_x, y0 * scale_y, x1 * scale_x, y1 * scale_y)

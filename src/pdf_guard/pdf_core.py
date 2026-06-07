from __future__ import annotations

import math
import tempfile
from pathlib import Path

import fitz

from .models import Detection, ProcessOptions, RedactionBox, WatermarkOptions
from .rules import Rule, find_sensitive_values

WATERMARK_FONT = "china-s"


def open_document(path: Path, password: str | None = None) -> fitz.Document:
    doc = fitz.open(path)
    if doc.needs_pass:
        if not password:
            doc.close()
            raise ValueError("PDF requires an open password.")
        if not doc.authenticate(password):
            doc.close()
            raise ValueError("Invalid PDF open password.")
    return doc


def detect_redactions(path: Path, rules: list[Rule], keywords: list[str], password: str | None = None) -> tuple[list[Detection], list[RedactionBox]]:
    detections: list[Detection] = []
    boxes: list[RedactionBox] = []
    doc = open_document(path, password)
    try:
        for page_index in range(doc.page_count):
            page = doc[page_index]
            text = page.get_text("text")
            hits = find_sensitive_values(text, rules, keywords)
            for category, values in hits.items():
                for value in values:
                    rects = tuple(_rect_tuple(rect) for rect in page.search_for(value))
                    detections.append(Detection(page_index=page_index, category=category, value=value, rects=rects))
                    for rect in rects:
                        boxes.append(
                            RedactionBox(
                                page_index=page_index,
                                rect=rect,
                                source="auto",
                                category=category,
                                label=_safe_label(value),
                            )
                        )
    finally:
        doc.close()
    return detections, boxes


def render_page_image(path: Path, page_index: int, zoom: float = 1.0, password: str | None = None):
    from PIL import Image

    doc = open_document(path, password)
    try:
        page = doc[page_index]
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        return image, (float(page.rect.width), float(page.rect.height)), doc.page_count
    finally:
        doc.close()


def apply_redactions(doc: fitz.Document, boxes: list[RedactionBox]) -> None:
    by_page: dict[int, list[RedactionBox]] = {}
    for box in boxes:
        by_page.setdefault(box.page_index, []).append(box)

    for page_index, page_boxes in by_page.items():
        page = doc[page_index]
        for box in page_boxes:
            rect = fitz.Rect(*box.rect)
            page.add_redact_annot(rect, fill=(0, 0, 0))
        page.apply_redactions(
            images=fitz.PDF_REDACT_IMAGE_PIXELS,
            graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED,
            text=fitz.PDF_REDACT_TEXT_REMOVE,
        )


def sanitize_document(doc: fitz.Document, clear_bookmarks: bool = True) -> None:
    doc.set_metadata({})
    try:
        doc.del_xml_metadata()
    except Exception:
        pass
    if clear_bookmarks:
        try:
            doc.set_toc([])
        except Exception:
            pass


def add_watermark(doc: fitz.Document, options: WatermarkOptions) -> None:
    if not options.text:
        return
    for page in doc:
        if options.tile:
            _add_tiled_watermark(page, options)
        else:
            _add_center_watermark(page, options)


def rasterize_to_pdf(source_path: Path, output_path: Path, dpi: int = 200, password: str | None = None) -> None:
    scale = dpi / 72.0
    matrix = fitz.Matrix(scale, scale)
    src = open_document(source_path, password)
    out = fitz.open()
    try:
        for page in src:
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            rect = page.rect
            new_page = out.new_page(width=rect.width, height=rect.height)
            new_page.insert_image(rect, pixmap=pix)
        out.save(output_path, garbage=4, deflate=True)
    finally:
        out.close()
        src.close()


def build_intermediate_pdf(options: ProcessOptions) -> tuple[Path, int]:
    with tempfile.TemporaryDirectory(prefix="local_pdf_guard_") as tmp:
        temp_dir = Path(tmp)
        watermarked_path = temp_dir / "watermarked.pdf"
        flattened_path = temp_dir / "flattened.pdf"

        doc = open_document(options.input_path, options.open_password)
        try:
            pages = doc.page_count
            apply_redactions(doc, options.boxes)
            sanitize_document(doc, options.clear_bookmarks)
            add_watermark(doc, options.watermark)
            doc.save(watermarked_path, garbage=4, deflate=True, clean=True)
        finally:
            doc.close()

        final_source = watermarked_path
        if options.flatten:
            rasterize_to_pdf(watermarked_path, flattened_path, dpi=options.flatten_dpi)
            final_source = flattened_path

        durable_path = options.output_path.with_suffix(".intermediate.pdf")
        durable_path.parent.mkdir(parents=True, exist_ok=True)
        if durable_path.exists():
            durable_path.unlink()
        final_source.replace(durable_path)
        return durable_path, pages


def _add_center_watermark(page: fitz.Page, options: WatermarkOptions) -> None:
    rect = page.rect
    point = fitz.Point(rect.width * 0.18, rect.height * 0.52)
    rotate, morph = _text_rotation(point, options.rotate)
    page.insert_text(
        point,
        options.text,
        fontsize=options.font_size,
        fontname=WATERMARK_FONT,
        rotate=rotate,
        morph=morph,
        color=options.color,
        fill_opacity=options.opacity,
        overlay=True,
    )


def _add_tiled_watermark(page: fitz.Page, options: WatermarkOptions) -> None:
    rect = page.rect
    step_x = max(options.font_size * max(len(options.text), 6) * 1.8, 240)
    step_y = max(options.font_size * 3.5, 150)
    start_x = -rect.width * 0.15
    start_y = rect.height * 0.12
    rows = int(math.ceil(rect.height / step_y)) + 3
    cols = int(math.ceil(rect.width / step_x)) + 3
    for row in range(rows):
        for col in range(cols):
            x = start_x + col * step_x
            y = start_y + row * step_y
            point = fitz.Point(x, y)
            rotate, morph = _text_rotation(point, options.rotate)
            page.insert_text(
                point,
                options.text,
                fontsize=options.font_size,
                fontname=WATERMARK_FONT,
                rotate=rotate,
                morph=morph,
                color=options.color,
                fill_opacity=options.opacity,
                overlay=True,
            )


def _text_rotation(point: fitz.Point, value: float) -> tuple[int, tuple[fitz.Point, fitz.Matrix] | None]:
    normalized = int(value) % 360 if float(value).is_integer() else value % 360
    if normalized in (0, 90, 180, 270):
        return int(normalized), None
    matrix = fitz.Matrix(1, 1).prerotate(value)
    return 0, (point, matrix)


def _rect_tuple(rect: fitz.Rect) -> tuple[float, float, float, float]:
    return (float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1))


def _safe_label(value: str) -> str:
    if len(value) <= 6:
        return "*" * len(value)
    return f"{value[:2]}***{value[-2:]}"

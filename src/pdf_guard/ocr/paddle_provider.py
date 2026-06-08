from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from .models import OcrBlock, OcrPageInput


class PaddleOcrProvider:
    name = "paddle"

    def __init__(self, model_dir: str | Path | None = None) -> None:
        base_dir = _runtime_base_dir()
        self.model_dir = _resolve_runtime_path(
            model_dir or os.environ.get("LOCAL_PDF_GUARD_PADDLE_MODEL_DIR"),
            base_dir / "vendor" / "ocr_models" / "paddleocr",
        )
        self.cache_dir = _resolve_runtime_path(
            os.environ.get("LOCAL_PDF_GUARD_OCR_CACHE_DIR"),
            base_dir / "vendor" / "ocr_cache",
        )
        self._ocr: Any | None = None
        self._available: bool | None = None

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            self._prepare_runtime_env()
            import paddleocr  # noqa: F401

            self._available = True
        except Exception:
            self._available = False
        return self._available

    def recognize_page(self, page: OcrPageInput) -> list[OcrBlock]:
        if not self.is_available():
            raise RuntimeError("PaddleOCR is not installed in this build.")
        ocr = self._get_ocr()
        raw = ocr.predict(page.image_path)
        return _parse_paddle_result(raw, page.page_index)

    def _get_ocr(self):
        if self._ocr is not None:
            return self._ocr
        self._prepare_runtime_env()
        from paddleocr import PaddleOCR

        kwargs: dict[str, Any] = {
            "use_textline_orientation": True,
            "lang": "ch",
            "device": "cpu",
        }
        if self.model_dir.exists():
            det_dir = self.model_dir / "det"
            rec_dir = self.model_dir / "rec"
            cls_dir = self.model_dir / "cls"
            if det_dir.exists():
                kwargs["text_detection_model_dir"] = str(det_dir)
            if rec_dir.exists():
                kwargs["text_recognition_model_dir"] = str(rec_dir)
            if cls_dir.exists():
                kwargs["textline_orientation_model_dir"] = str(cls_dir)
        self._ocr = PaddleOCR(**kwargs)
        return self._ocr

    def _prepare_runtime_env(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(self.cache_dir.resolve()))
        os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
        os.environ.setdefault("PADDLE_PDX_MODEL_SOURCE", "huggingface")


def _parse_paddle_result(raw, page_index: int) -> list[OcrBlock]:
    blocks: list[OcrBlock] = []
    if not raw:
        return blocks
    pages = raw if isinstance(raw, list) else [raw]
    for page_result in pages:
        if not page_result:
            continue
        parsed = _parse_paddle3_page_result(page_result, page_index)
        if parsed:
            blocks.extend(parsed)
            continue
        for item in page_result:
            try:
                points = item[0]
                text, confidence = item[1]
                xs = [float(point[0]) for point in points]
                ys = [float(point[1]) for point in points]
                blocks.append(
                    OcrBlock(
                        page_index=page_index,
                        text=str(text),
                        bbox_px=(min(xs), min(ys), max(xs), max(ys)),
                        confidence=float(confidence),
                        engine="paddle",
                    )
                )
            except Exception:
                continue
    return blocks


def _runtime_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path.cwd()


def _resolve_runtime_path(value: str | Path | None, default: Path) -> Path:
    if not value:
        return default
    path = Path(value)
    if path.is_absolute():
        return path
    return _runtime_base_dir() / path


def _parse_paddle3_page_result(page_result, page_index: int) -> list[OcrBlock]:
    try:
        rec_texts = page_result["rec_texts"]
        rec_scores = page_result["rec_scores"]
        polygons = page_result.get("rec_polys") or page_result.get("dt_polys") or page_result.get("rec_boxes")
    except Exception:
        return []
    if polygons is None:
        return []

    blocks: list[OcrBlock] = []
    for text, score, polygon in zip(rec_texts, rec_scores, polygons):
        try:
            if hasattr(polygon, "tolist"):
                polygon = polygon.tolist()
            if polygon and isinstance(polygon[0], (int, float)):
                x0, y0, x1, y1 = [float(v) for v in polygon[:4]]
                xs = [x0, x1]
                ys = [y0, y1]
            else:
                xs = [float(point[0]) for point in polygon]
                ys = [float(point[1]) for point in polygon]
            blocks.append(
                OcrBlock(
                    page_index=page_index,
                    text=str(text),
                    bbox_px=(min(xs), min(ys), max(xs), max(ys)),
                    confidence=float(score),
                    engine="paddle",
                )
            )
        except Exception:
            continue
    return blocks

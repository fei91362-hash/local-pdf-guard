from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .models import OcrBlock, OcrPageInput


class PaddleOcrProvider:
    name = "paddle"

    def __init__(self, model_dir: str | Path | None = None) -> None:
        self.model_dir = Path(model_dir or os.environ.get("LOCAL_PDF_GUARD_PADDLE_MODEL_DIR", "vendor/ocr_models/paddleocr"))
        self._ocr: Any | None = None
        self._available: bool | None = None

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            import paddleocr  # noqa: F401

            self._available = True
        except Exception:
            self._available = False
        return self._available

    def recognize_page(self, page: OcrPageInput) -> list[OcrBlock]:
        if not self.is_available():
            raise RuntimeError("PaddleOCR is not installed in this build.")
        ocr = self._get_ocr()
        raw = ocr.ocr(page.image_path, cls=True)
        return _parse_paddle_result(raw, page.page_index)

    def _get_ocr(self):
        if self._ocr is not None:
            return self._ocr
        from paddleocr import PaddleOCR

        kwargs: dict[str, Any] = {
            "use_angle_cls": True,
            "lang": "ch",
            "show_log": False,
        }
        if self.model_dir.exists():
            det_dir = self.model_dir / "det"
            rec_dir = self.model_dir / "rec"
            cls_dir = self.model_dir / "cls"
            if det_dir.exists():
                kwargs["det_model_dir"] = str(det_dir)
            if rec_dir.exists():
                kwargs["rec_model_dir"] = str(rec_dir)
            if cls_dir.exists():
                kwargs["cls_model_dir"] = str(cls_dir)
        self._ocr = PaddleOCR(**kwargs)
        return self._ocr


def _parse_paddle_result(raw, page_index: int) -> list[OcrBlock]:
    blocks: list[OcrBlock] = []
    if not raw:
        return blocks
    pages = raw if isinstance(raw, list) else [raw]
    for page_result in pages:
        if not page_result:
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

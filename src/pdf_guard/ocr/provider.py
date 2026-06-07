from __future__ import annotations

import os
from typing import Protocol

from .models import OcrBlock, OcrPageInput


class OcrProvider(Protocol):
    name: str

    def is_available(self) -> bool:
        ...

    def recognize_page(self, page: OcrPageInput) -> list[OcrBlock]:
        ...


class UnavailableOcrProvider:
    name = "unavailable"

    def is_available(self) -> bool:
        return False

    def recognize_page(self, page: OcrPageInput) -> list[OcrBlock]:
        raise RuntimeError("No local OCR provider is available.")


def get_default_ocr_provider() -> OcrProvider:
    engine = os.environ.get("LOCAL_PDF_GUARD_OCR_ENGINE", "paddle").strip().lower()
    if engine == "paddle":
        try:
            from .paddle_provider import PaddleOcrProvider

            return PaddleOcrProvider()
        except Exception:
            return UnavailableOcrProvider()
    return UnavailableOcrProvider()

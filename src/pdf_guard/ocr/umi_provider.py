from __future__ import annotations

from .models import OcrBlock, OcrPageInput


class UmiOcrProvider:
    name = "umi"

    def __init__(self, endpoint: str = "http://127.0.0.1:1224") -> None:
        self.endpoint = endpoint.rstrip("/")

    def is_available(self) -> bool:
        return False

    def recognize_page(self, page: OcrPageInput) -> list[OcrBlock]:
        raise NotImplementedError("Umi-OCR adapter is reserved for a later v1.1.x build.")

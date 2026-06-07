from __future__ import annotations

import re
import tempfile
from pathlib import Path

from ..models import RedactionBox
from ..rules import Rule, find_sensitive_values
from .models import OcrBlock, OcrCandidate, OcrPageInput
from .preprocess import image_bbox_to_pdf_rect, render_page_for_ocr
from .provider import OcrProvider

_MOBILE_WITH_SEPARATORS = re.compile(r"(?<!\d)1[3-9][0-9OIl\s-]{9,16}(?!\d)", re.IGNORECASE)
_ID_CARD_WITH_SEPARATORS = re.compile(
    r"(?<!\d)[0-9OIl\s-]{6}(?:18|19|20)[0-9OIl\s-]{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12][0-9OIl]|3[01])[0-9OIl\s-]{3}[0-9Xx](?!\d)",
    re.IGNORECASE,
)

NAME_KEYS = ("姓名", "联系人", "法定代表人", "经办人", "签字", "签名")
ADDRESS_KEYS = ("地址", "住址", "联系地址", "注册地址", "户籍地址", "通讯地址")
ADDRESS_MARKERS = ("省", "市", "区", "县", "镇", "乡", "街道", "路", "号", "室")


def detect_candidates_from_blocks(blocks: list[OcrBlock], page_input: OcrPageInput | None = None) -> list[OcrCandidate]:
    candidates: list[OcrCandidate] = []
    for block in blocks:
        normalized = _normalize_ocr_digits(block.text)
        for match in _MOBILE_WITH_SEPARATORS.finditer(normalized):
            value = _digits_only(match.group(0))
            if re.fullmatch(r"1[3-9]\d{9}", value):
                candidates.append(_candidate(block, page_input, "mobile", value, 0.95, "ocr_mobile_regex"))
        for match in _ID_CARD_WITH_SEPARATORS.finditer(normalized):
            value = _compact_id_card(match.group(0))
            if _looks_like_id_card(value):
                candidates.append(_candidate(block, page_input, "id_card", value, 0.92, "ocr_id_card_regex"))

        text = block.text.strip()
        if _looks_like_name_context(text):
            candidates.append(_candidate(block, page_input, "name", text, 0.68, "ocr_name_keyword"))
        if _looks_like_address_context(text):
            candidates.append(_candidate(block, page_input, "address", text, 0.7, "ocr_address_keyword"))
    return _dedupe_candidates(candidates)


def detect_sensitive_ocr_candidates(
    pdf_path: Path,
    provider: OcrProvider,
    rules: list[Rule],
    keywords: list[str],
    password: str | None = None,
    dpi: int = 200,
) -> dict[str, list[str]]:
    import fitz

    hits: dict[str, set[str]] = {}
    doc = fitz.open(pdf_path)
    try:
        if doc.needs_pass and password:
            doc.authenticate(password)
        page_count = doc.page_count
    finally:
        doc.close()

    with tempfile.TemporaryDirectory(prefix="local_pdf_guard_ocr_verify_") as tmp:
        temp_dir = Path(tmp)
        for page_index in range(page_count):
            page_input = render_page_for_ocr(pdf_path, page_index, password=password, dpi=dpi, temp_dir=temp_dir)
            blocks = provider.recognize_page(page_input)
            text = "\n".join(block.text for block in blocks)
            text_hits = find_sensitive_values(text, rules, keywords)
            for category, values in text_hits.items():
                hits.setdefault(category, set()).update(values)
            for candidate in detect_candidates_from_blocks(blocks, page_input):
                hits.setdefault(candidate.category, set()).add(candidate.text)
    return {category: sorted(values) for category, values in hits.items() if values}


def detect_ocr_redaction_boxes(
    pdf_path: Path,
    provider: OcrProvider,
    password: str | None = None,
    dpi: int = 200,
) -> tuple[list[OcrCandidate], list[RedactionBox]]:
    import fitz

    candidates: list[OcrCandidate] = []
    boxes: list[RedactionBox] = []
    doc = fitz.open(pdf_path)
    try:
        if doc.needs_pass and password:
            doc.authenticate(password)
        page_count = doc.page_count
    finally:
        doc.close()

    with tempfile.TemporaryDirectory(prefix="local_pdf_guard_ocr_detect_") as tmp:
        temp_dir = Path(tmp)
        for page_index in range(page_count):
            page_input = render_page_for_ocr(pdf_path, page_index, password=password, dpi=dpi, temp_dir=temp_dir)
            blocks = provider.recognize_page(page_input)
            page_candidates = detect_candidates_from_blocks(blocks, page_input)
            candidates.extend(page_candidates)
            for candidate in page_candidates:
                boxes.append(
                    RedactionBox(
                        page_index=candidate.page_index,
                        rect=candidate.rect_pdf,
                        source="ocr",
                        category=candidate.category,
                        label=_preview(candidate.text),
                        confidence=candidate.confidence,
                        confirmed=candidate.category in {"mobile", "id_card"},
                    )
                )
    return candidates, boxes


def _candidate(
    block: OcrBlock,
    page_input: OcrPageInput | None,
    category: str,
    text: str,
    confidence: float,
    reason: str,
) -> OcrCandidate:
    rect_pdf = image_bbox_to_pdf_rect(block.bbox_px, page_input) if page_input else block.bbox_px
    return OcrCandidate(
        page_index=block.page_index,
        text=text,
        category=category,
        rect_pdf=rect_pdf,
        confidence=min(block.confidence, confidence),
        reason=reason,
    )


def _normalize_ocr_digits(value: str) -> str:
    return value.translate(str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1"}))


def _digits_only(value: str) -> str:
    return re.sub(r"\D", "", value)


def _compact_id_card(value: str) -> str:
    value = _normalize_ocr_digits(value)
    return re.sub(r"[^0-9Xx]", "", value)


def _looks_like_id_card(value: str) -> bool:
    if not re.fullmatch(r"\d{17}[\dXx]", value):
        return False
    month = int(value[10:12])
    day = int(value[12:14])
    return 1 <= month <= 12 and 1 <= day <= 31


def _looks_like_name_context(text: str) -> bool:
    if not any(key in text for key in NAME_KEYS):
        return False
    chinese = re.findall(r"[\u4e00-\u9fff]{2,4}", text)
    return bool(chinese)


def _looks_like_address_context(text: str) -> bool:
    if any(key in text for key in ADDRESS_KEYS):
        return True
    return sum(1 for marker in ADDRESS_MARKERS if marker in text) >= 2 and len(text) >= 8


def _dedupe_candidates(candidates: list[OcrCandidate]) -> list[OcrCandidate]:
    seen: set[tuple[int, str, str, tuple[int, int, int, int]]] = set()
    unique: list[OcrCandidate] = []
    for item in candidates:
        rect_key = tuple(int(round(v)) for v in item.rect_pdf)
        key = (item.page_index, item.category, item.text, rect_key)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _preview(value: str) -> str:
    if len(value) <= 6:
        return "*" * len(value)
    return f"{value[:2]}***{value[-2:]}"

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RedactionBox:
    page_index: int
    rect: tuple[float, float, float, float]
    source: str
    category: str
    label: str
    confidence: float = 1.0
    id: str = ""
    confirmed: bool = True


@dataclass(frozen=True)
class WatermarkOptions:
    text: str = "内部资料 禁止外传"
    font_size: float = 42
    opacity: float = 0.18
    rotate: float = 45
    color: tuple[float, float, float] = (0.6, 0.6, 0.6)
    tile: bool = True


@dataclass(frozen=True)
class PermissionOptions:
    allow_print: bool = False
    allow_copy: bool = False
    allow_modify: bool = False
    allow_annotate: bool = False
    allow_form: bool = False
    allow_assemble: bool = False


@dataclass(frozen=True)
class ProcessOptions:
    input_path: Path
    output_path: Path
    open_password: str | None = None
    owner_password: str = ""
    user_password: str = ""
    boxes: list[RedactionBox] = field(default_factory=list)
    watermark: WatermarkOptions = field(default_factory=WatermarkOptions)
    flatten: bool = False
    flatten_dpi: int = 200
    permissions: PermissionOptions = field(default_factory=PermissionOptions)
    clear_bookmarks: bool = True
    verify_ocr: bool = False
    sanitize_links: bool = True
    sanitize_annotations: bool = True
    sanitize_attachments: bool = True
    sanitize_javascript: bool = True


@dataclass(frozen=True)
class Detection:
    page_index: int
    category: str
    value: str
    rects: tuple[tuple[float, float, float, float], ...]


@dataclass(frozen=True)
class VerificationResult:
    passed: bool
    residual_hits: dict[str, list[str]]
    encrypted: bool
    permissions_checked: bool
    notes: list[str] = field(default_factory=list)
    risk_level: str = "PASS"
    ocr_hits: dict[str, list[str]] = field(default_factory=dict)
    structure_warnings: list[str] = field(default_factory=list)
    sanitized_items: list[str] = field(default_factory=list)
    permission_status: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProcessReport:
    output_path: Path
    pages: int
    redaction_count: int
    watermark_applied: bool
    flattened: bool
    encrypted: bool
    verification: VerificationResult


@dataclass(frozen=True)
class BatchItemReport:
    input_path: Path
    output_path: Path
    status: str
    page_count: int | None = None
    detected_count: int = 0
    redacted_count: int = 0
    risk_level: str | None = None
    error_message: str | None = None
    report_json_path: Path | None = None


@dataclass(frozen=True)
class BatchReport:
    total: int
    success: int
    failed: int
    canceled: int
    items: list[BatchItemReport] = field(default_factory=list)

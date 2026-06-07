from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class RedactionBox:
    page_index: int
    rect: tuple[float, float, float, float]
    source: str
    category: str
    label: str
    confidence: float = 1.0


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


@dataclass(frozen=True)
class ProcessReport:
    output_path: Path
    pages: int
    redaction_count: int
    watermark_applied: bool
    flattened: bool
    encrypted: bool
    verification: VerificationResult


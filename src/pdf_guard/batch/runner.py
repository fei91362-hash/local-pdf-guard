from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ..models import BatchItemReport, BatchReport, ProcessOptions
from ..pdf_core import detect_redactions
from ..pipeline import process_pdf, process_report_to_dict
from ..rules import Rule

ProgressCallback = Callable[[str, BatchItemReport | BatchReport | None], None]


@dataclass(frozen=True)
class BatchOptions:
    input_paths: list[Path]
    output_dir: Path
    process_options: ProcessOptions
    rules: list[Rule]
    keywords: list[str]
    recursive: bool = False
    enable_ocr: bool = False
    continue_on_error: bool = True
    report_dir: Path | None = None


class BatchRunner:
    def __init__(self, options: BatchOptions, progress: ProgressCallback | None = None) -> None:
        self.options = options
        self.progress = progress
        self._canceled = False

    def cancel(self) -> None:
        self._canceled = True

    def run(self) -> BatchReport:
        inputs = expand_inputs(self.options.input_paths, recursive=self.options.recursive)
        items: list[BatchItemReport] = []
        self._emit("batch_started", None)
        for input_path in inputs:
            if self._canceled:
                items.append(BatchItemReport(input_path=input_path, output_path=build_output_path(input_path, self.options.output_dir), status="canceled"))
                continue
            output_path = build_output_path(input_path, self.options.output_dir)
            started = BatchItemReport(input_path=input_path, output_path=output_path, status="running")
            self._emit("item_started", started)
            try:
                detections, boxes = detect_redactions(
                    input_path,
                    self.options.rules,
                    self.options.keywords,
                    self.options.process_options.open_password,
                )
                if self.options.enable_ocr:
                    from ..ocr.detectors import detect_ocr_redaction_boxes
                    from ..ocr.provider import get_default_ocr_provider

                    provider = get_default_ocr_provider()
                    if not provider.is_available():
                        raise RuntimeError("OCR is enabled, but no local OCR provider is available.")
                    _, ocr_boxes = detect_ocr_redaction_boxes(input_path, provider, self.options.process_options.open_password)
                    boxes.extend(box for box in ocr_boxes if box.confirmed)
                process_options = _copy_process_options(
                    self.options.process_options,
                    input_path=input_path,
                    output_path=output_path,
                    boxes=boxes,
                )
                report = process_pdf(process_options, self.options.rules, self.options.keywords)
                report_path = write_item_report(
                    report_payload={
                        **process_report_to_dict(report),
                        "input_path": str(input_path),
                        "detections": len(detections),
                    },
                    input_path=input_path,
                    output_path=output_path,
                    report_dir=self.options.report_dir or self.options.output_dir,
                )
                item = BatchItemReport(
                    input_path=input_path,
                    output_path=output_path,
                    status="success",
                    page_count=report.pages,
                    detected_count=len(detections),
                    redacted_count=report.redaction_count,
                    risk_level=report.verification.risk_level,
                    report_json_path=report_path,
                )
                items.append(item)
                self._emit("item_success", item)
            except Exception as exc:
                item = BatchItemReport(input_path=input_path, output_path=output_path, status="failed", error_message=str(exc))
                items.append(item)
                self._emit("item_failed", item)
                if not self.options.continue_on_error:
                    break
        summary = BatchReport(
            total=len(items),
            success=sum(1 for item in items if item.status == "success"),
            failed=sum(1 for item in items if item.status == "failed"),
            canceled=sum(1 for item in items if item.status == "canceled"),
            items=items,
        )
        write_batch_report(summary, self.options.report_dir or self.options.output_dir)
        self._emit("batch_finished", summary)
        return summary

    def _emit(self, event: str, payload: BatchItemReport | BatchReport | None) -> None:
        if self.progress:
            self.progress(event, payload)


def expand_inputs(paths: list[Path], recursive: bool = False) -> list[Path]:
    result: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix.lower() == ".pdf":
            result.append(path)
        elif path.is_dir():
            pattern = "**/*.pdf" if recursive else "*.pdf"
            result.extend(sorted(path.glob(pattern)))
    return sorted(dict.fromkeys(result))


def build_output_path(input_path: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    base = output_dir / f"{input_path.stem}_guarded.pdf"
    if not base.exists():
        return base
    for index in range(2, 10000):
        candidate = output_dir / f"{input_path.stem}_guarded_{index}.pdf"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Cannot find a free output name for {input_path.name}.")


def write_item_report(report_payload: dict, input_path: Path, output_path: Path, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{output_path.stem}.report.json"
    report_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return report_path


def write_batch_report(report: BatchReport, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "total": report.total,
        "success": report.success,
        "failed": report.failed,
        "canceled": report.canceled,
        "items": [
            {
                "input_path": str(item.input_path),
                "output_path": str(item.output_path),
                "status": item.status,
                "page_count": item.page_count,
                "detected_count": item.detected_count,
                "redacted_count": item.redacted_count,
                "risk_level": item.risk_level,
                "error_message": item.error_message,
                "report_json_path": str(item.report_json_path) if item.report_json_path else None,
            }
            for item in report.items
        ],
    }
    report_path = report_dir / "batch.report.json"
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return report_path


def _copy_process_options(
    options: ProcessOptions,
    input_path: Path,
    output_path: Path,
    boxes,
) -> ProcessOptions:
    return ProcessOptions(
        input_path=input_path,
        output_path=output_path,
        open_password=options.open_password,
        owner_password=options.owner_password,
        user_password=options.user_password,
        boxes=boxes,
        watermark=options.watermark,
        flatten=options.flatten,
        flatten_dpi=options.flatten_dpi,
        permissions=options.permissions,
        clear_bookmarks=options.clear_bookmarks,
        verify_ocr=options.verify_ocr,
        sanitize_links=options.sanitize_links,
        sanitize_annotations=options.sanitize_annotations,
        sanitize_attachments=options.sanitize_attachments,
        sanitize_javascript=options.sanitize_javascript,
    )

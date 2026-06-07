from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .batch.runner import BatchOptions, BatchRunner
from .models import PermissionOptions, ProcessOptions, WatermarkOptions
from .ocr.detectors import detect_ocr_redaction_boxes
from .ocr.provider import get_default_ocr_provider
from .pdf_core import detect_redactions
from .pipeline import process_pdf, process_report_to_dict
from .rules import selected_rules


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="local-pdf-guard")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    process = subparsers.add_parser("process", help="redact, watermark, protect, and verify a PDF")
    process.add_argument("--input", required=True, type=Path)
    process.add_argument("--output", required=True, type=Path)
    process.add_argument("--open-password", default=None)
    process.add_argument("--owner-password", required=True)
    process.add_argument("--user-password", default="")
    process.add_argument("--watermark", default="内部资料 禁止外传")
    process.add_argument("--watermark-font-size", type=float, default=42)
    process.add_argument("--watermark-opacity", type=float, default=0.18)
    process.add_argument("--no-tile-watermark", action="store_true")
    process.add_argument("--flatten", action="store_true")
    process.add_argument("--flatten-dpi", type=int, default=200)
    process.add_argument("--keyword", action="append", default=[])
    process.add_argument("--redact-mobile", action="store_true")
    process.add_argument("--redact-id-card", action="store_true")
    process.add_argument("--redact-email", action="store_true")
    process.add_argument("--redact-bank-card", action="store_true")
    process.add_argument("--redact-uscc", action="store_true")
    process.add_argument("--enable-ocr", action="store_true")
    process.add_argument("--verify-ocr", action="store_true")
    process.add_argument("--allow-print", action="store_true")
    process.add_argument("--allow-copy", action="store_true")
    process.add_argument("--allow-modify", action="store_true")
    process.add_argument("--report-json", type=Path, default=None)

    batch = subparsers.add_parser("batch", help="process multiple PDFs with the same settings")
    batch.add_argument("--input", action="append", required=True, type=Path, help="PDF file or folder. Can be repeated.")
    batch.add_argument("--output-dir", required=True, type=Path)
    batch.add_argument("--recursive", action="store_true")
    batch.add_argument("--open-password", default=None)
    batch.add_argument("--owner-password", required=True)
    batch.add_argument("--user-password", default="")
    batch.add_argument("--watermark", default="内部资料 禁止外传")
    batch.add_argument("--flatten", action="store_true")
    batch.add_argument("--flatten-dpi", type=int, default=200)
    batch.add_argument("--keyword", action="append", default=[])
    batch.add_argument("--redact-mobile", action="store_true")
    batch.add_argument("--redact-id-card", action="store_true")
    batch.add_argument("--redact-email", action="store_true")
    batch.add_argument("--redact-bank-card", action="store_true")
    batch.add_argument("--redact-uscc", action="store_true")
    batch.add_argument("--enable-ocr", action="store_true")
    batch.add_argument("--verify-ocr", action="store_true")
    batch.add_argument("--allow-print", action="store_true")
    batch.add_argument("--allow-copy", action="store_true")
    batch.add_argument("--allow-modify", action="store_true")
    batch.add_argument("--stop-on-error", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "process":
        return _process(args)
    if args.command == "batch":
        return _batch(args)
    parser.print_help()
    return 2


def _process(args: argparse.Namespace) -> int:
    rules = selected_rules(
        redact_mobile=args.redact_mobile,
        redact_id_card=args.redact_id_card,
        redact_email=args.redact_email,
        redact_bank_card=args.redact_bank_card,
        redact_uscc=args.redact_uscc,
    )
    keywords = list(args.keyword or [])
    detections, boxes = detect_redactions(args.input, rules, keywords, args.open_password)
    ocr_candidates = []
    if args.enable_ocr:
        provider = get_default_ocr_provider()
        if not provider.is_available():
            raise SystemExit("OCR is not available in this build. Use OCR Full or install PaddleOCR dependencies.")
        ocr_candidates, ocr_boxes = detect_ocr_redaction_boxes(args.input, provider, args.open_password)
        boxes.extend(box for box in ocr_boxes if box.confirmed)

    options = ProcessOptions(
        input_path=args.input,
        output_path=args.output,
        open_password=args.open_password,
        owner_password=args.owner_password,
        user_password=args.user_password,
        boxes=boxes,
        watermark=WatermarkOptions(
            text=args.watermark,
            font_size=args.watermark_font_size,
            opacity=args.watermark_opacity,
            tile=not args.no_tile_watermark,
        ),
        flatten=args.flatten,
        flatten_dpi=args.flatten_dpi,
        verify_ocr=args.verify_ocr,
        permissions=PermissionOptions(
            allow_print=args.allow_print,
            allow_copy=args.allow_copy,
            allow_modify=args.allow_modify,
        ),
    )
    report = process_pdf(options, rules, keywords)
    payload = _report_payload(report, detections)
    payload["ocr_candidates"] = [
        {
            "page_index": item.page_index,
            "category": item.category,
            "text_preview": _preview(item.text),
            "confidence": item.confidence,
            "reason": item.reason,
        }
        for item in ocr_candidates
    ]

    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if report.verification.passed else 1


def _batch(args: argparse.Namespace) -> int:
    rules = _rules_from_args(args)
    keywords = list(args.keyword or [])
    process_options = ProcessOptions(
        input_path=Path("__batch_placeholder__.pdf"),
        output_path=args.output_dir / "__batch_placeholder__.pdf",
        open_password=args.open_password,
        owner_password=args.owner_password,
        user_password=args.user_password,
        boxes=[],
        watermark=WatermarkOptions(text=args.watermark),
        flatten=args.flatten,
        flatten_dpi=args.flatten_dpi,
        verify_ocr=args.verify_ocr,
        permissions=PermissionOptions(
            allow_print=args.allow_print,
            allow_copy=args.allow_copy,
            allow_modify=args.allow_modify,
        ),
    )
    batch_options = BatchOptions(
        input_paths=list(args.input),
        output_dir=args.output_dir,
        process_options=process_options,
        rules=rules,
        keywords=keywords,
        recursive=args.recursive,
        enable_ocr=args.enable_ocr,
        continue_on_error=not args.stop_on_error,
    )
    report = BatchRunner(batch_options).run()
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
                "risk_level": item.risk_level,
                "error_message": item.error_message,
            }
            for item in report.items
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if report.failed == 0 else 1


def _rules_from_args(args: argparse.Namespace):
    return selected_rules(
        redact_mobile=args.redact_mobile,
        redact_id_card=args.redact_id_card,
        redact_email=args.redact_email,
        redact_bank_card=args.redact_bank_card,
        redact_uscc=args.redact_uscc,
    )


def _report_payload(report, detections) -> dict:
    payload = process_report_to_dict(report)
    payload.update(
        {
        "detections": [
            {
                "page_index": item.page_index,
                "category": item.category,
                "value_preview": _preview(item.value),
                "rect_count": len(item.rects),
            }
            for item in detections
        ],
        }
    )
    payload["verification"]["residual_hits"] = {
        key: [_preview(v) for v in values] for key, values in report.verification.residual_hits.items()
    }
    payload["verification"]["ocr_hits"] = {
        key: [_preview(v) for v in values] for key, values in report.verification.ocr_hits.items()
    }
    return payload


def _preview(value: str) -> str:
    if len(value) <= 6:
        return "*" * len(value)
    return f"{value[:2]}***{value[-2:]}"


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .models import PermissionOptions, ProcessOptions, WatermarkOptions
from .pdf_core import detect_redactions
from .pipeline import process_pdf
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
    process.add_argument("--allow-print", action="store_true")
    process.add_argument("--allow-copy", action="store_true")
    process.add_argument("--allow-modify", action="store_true")
    process.add_argument("--report-json", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "process":
        return _process(args)
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
        permissions=PermissionOptions(
            allow_print=args.allow_print,
            allow_copy=args.allow_copy,
            allow_modify=args.allow_modify,
        ),
    )
    report = process_pdf(options, rules, keywords)
    payload = _report_payload(report, detections)

    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if report.verification.passed else 1


def _report_payload(report, detections) -> dict:
    return {
        "output_path": str(report.output_path),
        "pages": report.pages,
        "detections": [
            {
                "page_index": item.page_index,
                "category": item.category,
                "value_preview": _preview(item.value),
                "rect_count": len(item.rects),
            }
            for item in detections
        ],
        "redaction_count": report.redaction_count,
        "watermark_applied": report.watermark_applied,
        "flattened": report.flattened,
        "encrypted": report.encrypted,
        "verification": {
            "passed": report.verification.passed,
            "residual_hits": {key: [_preview(v) for v in values] for key, values in report.verification.residual_hits.items()},
            "permissions_checked": report.verification.permissions_checked,
            "notes": report.verification.notes,
        },
    }


def _preview(value: str) -> str:
    if len(value) <= 6:
        return "*" * len(value)
    return f"{value[:2]}***{value[-2:]}"


if __name__ == "__main__":
    raise SystemExit(main())


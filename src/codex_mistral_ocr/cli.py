"""Command-line interface for local testing outside Codex."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from . import __version__
from .client import MistralOCRError
from .processor import OCRProcessorError, list_cached_results, parse_pdf, read_result, search_result


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codex-mistral-ocr",
        description="Parse PDFs with Mistral OCR and expose cached Markdown for Codex.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    parse_cmd = sub.add_parser("parse", help="Run OCR on a PDF path or URL.")
    parse_cmd.add_argument("pdf", help="Local PDF path or public PDF URL.")
    parse_cmd.add_argument("--model", default="mistral-ocr-latest", help="Mistral OCR model to use. Default: mistral-ocr-latest.")
    parse_cmd.add_argument("--pages", help="Human page range, e.g. '1', '2-4', '1,3-5'.")
    parse_cmd.add_argument("--force-refresh", action="store_true", help="Ignore the local cache.")
    parse_cmd.add_argument("--include-images", action="store_true", help="Ask Mistral to return extracted image regions.")
    parse_cmd.add_argument("--table-format", choices=["markdown", "html"], help="Return tables separately in this format.")
    parse_cmd.add_argument("--extract-header", action="store_true", help="Separate detected headers when supported by the OCR model.")
    parse_cmd.add_argument("--extract-footer", action="store_true", help="Separate detected footers when supported by the OCR model.")
    parse_cmd.add_argument("--confidence-scores", choices=["page", "word"], help="Request OCR confidence scores.")
    parse_cmd.add_argument("--image-limit", type=int, help="Maximum image regions to extract when images are enabled.")
    parse_cmd.add_argument("--image-min-size", type=int, help="Minimum image height/width to extract when images are enabled.")
    parse_cmd.add_argument("--transport", choices=["data_uri", "file_upload"], default="data_uri", help="How to send local PDFs to Mistral. Default: data_uri.")
    parse_cmd.add_argument("--max-excerpt-chars", type=int, default=8000, help="Preview size printed in JSON output.")

    read_cmd = sub.add_parser("read", help="Read cached OCR Markdown.")
    read_cmd.add_argument("result_id_or_path", help="Result ID from parse, or cache directory path.")
    read_cmd.add_argument("--pages", help="Human page range to read.")
    read_cmd.add_argument("--max-chars", type=int, default=12000, help="Maximum characters to print.")

    search_cmd = sub.add_parser("search", help="Search cached OCR Markdown.")
    search_cmd.add_argument("result_id_or_path")
    search_cmd.add_argument("query")
    search_cmd.add_argument("--max-matches", type=int, default=10)
    search_cmd.add_argument("--context-chars", type=int, default=300)

    sub.add_parser("list", help="List cached OCR results.")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "parse":
            _print_json(
                parse_pdf(
                    args.pdf,
                    model=args.model,
                    pages=args.pages,
                    force_refresh=args.force_refresh,
                    include_images=args.include_images,
                    table_format=args.table_format,
                    extract_header=args.extract_header,
                    extract_footer=args.extract_footer,
                    confidence_scores=args.confidence_scores,
                    image_limit=args.image_limit,
                    image_min_size=args.image_min_size,
                    transport=args.transport,
                    max_excerpt_chars=args.max_excerpt_chars,
                )
            )
            return 0
        if args.command == "read":
            _print_json(read_result(args.result_id_or_path, pages=args.pages, max_chars=args.max_chars))
            return 0
        if args.command == "search":
            _print_json(
                search_result(
                    args.result_id_or_path,
                    query=args.query,
                    max_matches=args.max_matches,
                    context_chars=args.context_chars,
                )
            )
            return 0
        if args.command == "list":
            _print_json(list_cached_results())
            return 0
    except (MistralOCRError, OCRProcessorError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

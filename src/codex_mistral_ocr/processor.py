"""High-level OCR orchestration for CLI and MCP tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .cache import (
    cache_exists,
    cached_paths,
    default_cache_dir,
    list_results,
    make_result_id,
    read_json,
    resolve_result_id_or_path,
    write_result,
)
from .client import MistralOCRClient
from .formatting import (
    excerpt_text,
    export_image_assets_and_strip_base64,
    response_to_markdown,
    search_markdown,
    select_markdown_pages,
)
from .page_ranges import human_pages_to_display, parse_human_pages
from .source import display_source_for_agent, source_info
from .types import ConfidenceGranularity, OCRRequestOptions, TableFormat, TransportMode


class OCRProcessorError(RuntimeError):
    """Raised when the processor cannot satisfy a request."""


def build_options(
    *,
    model: str = "mistral-ocr-latest",
    pages: str | None = None,
    include_images: bool = False,
    table_format: TableFormat | None = None,
    extract_header: bool = False,
    extract_footer: bool = False,
    confidence_scores: ConfidenceGranularity | None = None,
    image_limit: int | None = None,
    image_min_size: int | None = None,
    transport: TransportMode = "data_uri",
) -> OCRRequestOptions:
    parsed_pages = parse_human_pages(pages)
    return OCRRequestOptions(
        model=model,
        pages=tuple(parsed_pages) if parsed_pages is not None else None,
        include_image_base64=include_images,
        table_format=table_format,
        extract_header=extract_header,
        extract_footer=extract_footer,
        confidence_scores_granularity=confidence_scores,
        image_limit=image_limit,
        image_min_size=image_min_size,
        transport=transport,
    )


def parse_pdf(
    source: str,
    *,
    model: str = "mistral-ocr-latest",
    pages: str | None = None,
    force_refresh: bool = False,
    include_images: bool = False,
    table_format: TableFormat | None = None,
    extract_header: bool = False,
    extract_footer: bool = False,
    confidence_scores: ConfidenceGranularity | None = None,
    image_limit: int | None = None,
    image_min_size: int | None = None,
    transport: TransportMode = "data_uri",
    store_image_base64: bool = False,
    max_excerpt_chars: int = 8000,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    """OCR a PDF, cache the result, and return agent-friendly metadata."""

    src = source_info(source)
    options = build_options(
        model=model,
        pages=pages,
        include_images=include_images,
        table_format=table_format,
        extract_header=extract_header,
        extract_footer=extract_footer,
        confidence_scores=confidence_scores,
        image_limit=image_limit,
        image_min_size=image_min_size,
        transport=transport,
    )
    result_id = make_result_id(src, options)
    result = cached_paths(result_id, cache_dir=cache_dir)

    cache_hit = cache_exists(result) and not force_refresh
    if cache_hit:
        markdown = result.markdown_path.read_text(encoding="utf-8")
        response = read_json(result.response_path)
        metadata = read_json(result.metadata_path)
    else:
        with MistralOCRClient() as client:
            raw_response = client.process_source(src, options)
        response = export_image_assets_and_strip_base64(
            raw_response,
            result.assets_dir,
            store_image_base64=store_image_base64,
        )
        options_display = {
            **options.stable_dict(),
            "requested_pages_human": human_pages_to_display(pages),
            "store_image_base64": store_image_base64,
        }
        markdown = response_to_markdown(
            response,
            source=src,
            result_id=result_id,
            options_display=options_display,
        )
        metadata = {
            "result_id": result_id,
            "source": display_source_for_agent(src),
            "source_label": src.label,
            "source_kind": src.kind,
            "source_fingerprint": src.fingerprint,
            "source_size_bytes": src.size_bytes,
            "mime_type": src.mime_type,
            "options": options_display,
            "model_returned": response.get("model"),
            "page_count": len(response.get("pages") or []),
            "cache_dir": str(default_cache_dir() if cache_dir is None else cache_dir),
        }
        write_result(result, response=response, markdown=markdown, metadata=metadata)

    selected_preview = select_markdown_pages(markdown, pages)
    return {
        "status": "ok",
        "cache_hit": cache_hit,
        "result_id": result_id,
        "source": display_source_for_agent(src),
        "source_label": src.label,
        "page_count": len(response.get("pages") or []),
        "model": response.get("model") or options.model,
        "markdown_path": str(result.markdown_path),
        "response_json_path": str(result.response_path),
        "metadata_path": str(result.metadata_path),
        "assets_dir": str(result.assets_dir),
        "usage_info": response.get("usage_info"),
        "markdown_excerpt": excerpt_text(selected_preview, max_excerpt_chars),
        "next_steps_for_agent": (
            "Use read_ocr_result(result_id, pages=...) to load specific pages, or "
            "search_ocr_result(result_id, query=...) to locate terms without re-running OCR. "
            "Cite page numbers from the OCR Markdown headings when answering."
        ),
        "metadata": metadata,
    }


def read_result(
    result_id_or_path: str,
    *,
    pages: str | None = None,
    max_chars: int = 12000,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    result = resolve_result_id_or_path(result_id_or_path, cache_dir=cache_dir)
    if not result.markdown_path.exists():
        raise OCRProcessorError(
            f"No cached OCR markdown found for {result_id_or_path!r}. Run parse_pdf first."
        )
    markdown = result.markdown_path.read_text(encoding="utf-8")
    selected = select_markdown_pages(markdown, pages)
    metadata = read_json(result.metadata_path) if result.metadata_path.exists() else {}
    return {
        "status": "ok",
        "result_id": result.result_id,
        "pages": pages or "all",
        "markdown_path": str(result.markdown_path),
        "content": excerpt_text(selected, max_chars),
        "truncated": len(selected) > max_chars,
        "metadata": metadata,
    }


def search_result(
    result_id_or_path: str,
    *,
    query: str,
    max_matches: int = 10,
    context_chars: int = 300,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    result = resolve_result_id_or_path(result_id_or_path, cache_dir=cache_dir)
    if not result.markdown_path.exists():
        raise OCRProcessorError(
            f"No cached OCR markdown found for {result_id_or_path!r}. Run parse_pdf first."
        )
    markdown = result.markdown_path.read_text(encoding="utf-8")
    matches = search_markdown(
        markdown,
        query,
        max_matches=max_matches,
        context_chars=context_chars,
    )
    return {
        "status": "ok",
        "result_id": result.result_id,
        "query": query,
        "match_count": len(matches),
        "matches": matches,
        "markdown_path": str(result.markdown_path),
    }


def list_cached_results(*, cache_dir: Path | None = None) -> dict[str, Any]:
    entries = list_results(cache_dir=cache_dir)
    return {"status": "ok", "count": len(entries), "results": entries}

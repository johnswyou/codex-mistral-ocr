"""MCP server for Codex PDF OCR with Mistral."""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from . import __version__
from .processor import list_cached_results, parse_pdf, read_result, search_result

mcp = FastMCP("mistral-pdf-ocr")


@mcp.tool()
def mistral_ocr_parse_pdf(
    pdf_path_or_url: str,
    model: str = "mistral-ocr-latest",
    pages: str | None = None,
    force_refresh: bool = False,
    include_images: bool = False,
    table_format: Literal["markdown", "html"] | None = None,
    extract_header: bool = False,
    extract_footer: bool = False,
    confidence_scores: Literal["page", "word"] | None = None,
    image_limit: int | None = None,
    image_min_size: int | None = None,
    transport: Literal["data_uri", "file_upload"] = "data_uri",
    max_excerpt_chars: int = 8000,
) -> dict[str, Any]:
    """Parse a PDF with Mistral OCR and cache full Markdown/JSON locally.

    Use this whenever Codex needs to read, summarize, inspect, or answer
    questions about a PDF. `pages` uses human 1-based ranges like "1", "2-4",
    or "1,3-5". The returned `result_id` can be passed to the read/search tools
    without re-running OCR.
    """

    return parse_pdf(
        pdf_path_or_url,
        model=model,
        pages=pages,
        force_refresh=force_refresh,
        include_images=include_images,
        table_format=table_format,
        extract_header=extract_header,
        extract_footer=extract_footer,
        confidence_scores=confidence_scores,
        image_limit=image_limit,
        image_min_size=image_min_size,
        transport=transport,
        max_excerpt_chars=max_excerpt_chars,
    )


@mcp.tool()
def mistral_ocr_read_result(
    result_id_or_path: str,
    pages: str | None = None,
    max_chars: int = 12000,
) -> dict[str, Any]:
    """Read cached OCR Markdown from a previous parse.

    Use `pages` for human 1-based ranges such as "1" or "2-4" to avoid loading
    huge PDFs into context. `result_id_or_path` is normally the `result_id`
    returned by `mistral_ocr_parse_pdf`.
    """

    return read_result(result_id_or_path, pages=pages, max_chars=max_chars)


@mcp.tool()
def mistral_ocr_search_result(
    result_id_or_path: str,
    query: str,
    max_matches: int = 10,
    context_chars: int = 300,
) -> dict[str, Any]:
    """Search a cached OCR Markdown result by literal text.

    Use this to find relevant pages or terms in a parsed PDF before loading
    selected pages with `mistral_ocr_read_result`.
    """

    return search_result(
        result_id_or_path,
        query=query,
        max_matches=max_matches,
        context_chars=context_chars,
    )


@mcp.tool()
def mistral_ocr_list_cached_results() -> dict[str, Any]:
    """List locally cached Mistral OCR results and their metadata."""

    return list_cached_results()


@mcp.tool()
def mistral_ocr_health() -> dict[str, Any]:
    """Check that the MCP server process is alive and which package version is running."""

    return {"status": "ok", "server": "mistral-pdf-ocr", "version": __version__}


def main() -> None:
    """Run the MCP server over stdio."""

    mcp.run()


if __name__ == "__main__":
    main()

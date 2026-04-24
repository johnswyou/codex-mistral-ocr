"""Utilities for translating human page ranges into Mistral OCR page indexes."""

from __future__ import annotations

import re

_RANGE_RE = re.compile(r"^\s*(\d+)\s*(?:[-:]\s*(\d+)\s*)?$")


class PageRangeError(ValueError):
    """Raised when a page range string cannot be parsed."""


def parse_human_pages(pages: str | None) -> list[int] | None:
    """Parse 1-based page ranges and return 0-based page indexes for Mistral.

    The public MCP and CLI interfaces use human page numbers because users and
    agents naturally refer to PDFs by visible page number. Mistral's OCR API
    expects zero-based page indexes in the `pages` request field.

    Examples:
        "1" -> [0]
        "1, 3-5" -> [0, 2, 3, 4]
        None or "" -> None
    """

    if pages is None:
        return None
    text = str(pages).strip()
    if not text:
        return None

    indexes: set[int] = set()
    for raw_part in text.split(","):
        part = raw_part.strip()
        if not part:
            continue
        match = _RANGE_RE.match(part)
        if not match:
            raise PageRangeError(
                f"Invalid page range segment {part!r}. Use forms like '1', '2-4', or '1,3-5'."
            )
        start = int(match.group(1))
        end = int(match.group(2) or start)
        if start < 1 or end < 1:
            raise PageRangeError("Page numbers are 1-based and must be positive.")
        if end < start:
            raise PageRangeError(f"Invalid descending page range {part!r}.")
        indexes.update(range(start - 1, end))

    return sorted(indexes) if indexes else None


def human_page_label(page_index: int | None, ordinal: int, first_response_index: int | None) -> int:
    """Return the best human-facing page number for an OCR page object.

    Mistral examples usually return page indexes as 1-based values, while the
    request `pages` parameter is documented as zero-based. This function keeps
    returned labels stable across either convention.
    """

    if page_index is None:
        return ordinal + 1
    if first_response_index == 0:
        return page_index + 1
    return page_index


def human_pages_to_display(pages: str | None) -> str:
    """Normalize a human page range string for metadata display."""

    parsed = parse_human_pages(pages)
    if parsed is None:
        return "all"
    return ",".join(str(index + 1) for index in parsed)

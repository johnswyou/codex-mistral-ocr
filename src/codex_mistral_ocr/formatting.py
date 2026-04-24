"""Formatting helpers for OCR responses."""

from __future__ import annotations

import base64
import copy
import mimetypes
import re
from pathlib import Path
from typing import Any

from .page_ranges import human_page_label, parse_human_pages
from .source import display_source_for_agent
from .types import SourceInfo

_PAGE_HEADING_RE = re.compile(r"^## Page (\d+)\s*$", re.MULTILINE)


def _page_index(page: dict[str, Any]) -> int | None:
    value = page.get("index")
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def response_to_markdown(
    response: dict[str, Any],
    *,
    source: SourceInfo,
    result_id: str,
    options_display: dict[str, Any],
) -> str:
    """Convert a Mistral OCR response to agent-friendly Markdown."""

    pages = list(response.get("pages") or [])
    first_index = _page_index(pages[0]) if pages else None

    lines: list[str] = [
        f"# OCR result: {source.label}",
        "",
        f"- Result ID: `{result_id}`",
        f"- Source: `{display_source_for_agent(source)}`",
        f"- Source SHA-256/fingerprint: `{source.fingerprint}`",
        f"- Model: `{response.get('model') or options_display.get('model') or 'unknown'}`",
        f"- Page objects returned: {len(pages)}",
        f"- Options: `{options_display}`",
    ]
    usage = response.get("usage_info")
    if usage is not None:
        lines.append(f"- Usage info: `{usage}`")
    lines.extend(["", "---", ""])

    for ordinal, page in enumerate(pages):
        if not isinstance(page, dict):
            continue
        label = human_page_label(_page_index(page), ordinal, first_index)
        lines.append(f"## Page {label}")
        lines.append("")

        header = page.get("header")
        if header:
            lines.extend(["### Header", "", str(header).strip(), ""])

        markdown = str(page.get("markdown") or "").strip()
        lines.append(markdown if markdown else "[No OCR markdown returned for this page.]")
        lines.append("")

        footer = page.get("footer")
        if footer:
            lines.extend(["### Footer", "", str(footer).strip(), ""])

        tables = page.get("tables") or []
        if tables:
            lines.extend(["### Extracted tables", ""])
            for table_index, table in enumerate(tables, start=1):
                if not isinstance(table, dict):
                    continue
                table_id = table.get("id") or f"table-{table_index}"
                lines.extend([f"#### {table_id}", ""])
                table_text = table.get("markdown") or table.get("html") or table.get("content")
                if table_text:
                    lines.extend([str(table_text).strip(), ""])

        images = page.get("images") or []
        if images:
            lines.extend(["### Extracted image regions", ""])
            for image in images:
                if not isinstance(image, dict):
                    continue
                image_id = image.get("id") or "image"
                coords = [
                    image.get("top_left_x"),
                    image.get("top_left_y"),
                    image.get("bottom_right_x"),
                    image.get("bottom_right_y"),
                ]
                saved_path = image.get("saved_path")
                coord_text = ", ".join("?" if c is None else str(c) for c in coords)
                if saved_path:
                    lines.append(f"- `{image_id}` bbox=({coord_text}), saved at `{saved_path}`")
                else:
                    lines.append(f"- `{image_id}` bbox=({coord_text})")
            lines.append("")

    document_annotation = response.get("document_annotation")
    if document_annotation:
        lines.extend(["---", "", "## Document annotation", "", str(document_annotation).strip(), ""])

    return "\n".join(lines).rstrip() + "\n"


def export_image_assets_and_strip_base64(
    response: dict[str, Any],
    assets_dir: Path,
    *,
    store_image_base64: bool = False,
) -> dict[str, Any]:
    """Save any returned image_base64 values as files and optionally strip them from JSON."""

    cloned = copy.deepcopy(response)
    assets_dir.mkdir(parents=True, exist_ok=True)

    for page in cloned.get("pages") or []:
        if not isinstance(page, dict):
            continue
        for image in page.get("images") or []:
            if not isinstance(image, dict):
                continue
            data = image.get("image_base64")
            if not data or not isinstance(data, str):
                continue
            image_id = str(image.get("id") or "image")
            suffix = Path(image_id).suffix
            payload = data
            mime_type = None
            if data.startswith("data:") and ";base64," in data:
                meta, payload = data.split(";base64,", 1)
                mime_type = meta.removeprefix("data:")
                suffix = mimetypes.guess_extension(mime_type) or suffix or ".bin"
            if not suffix:
                suffix = ".bin"
            safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(image_id).stem or "image")
            path = assets_dir / f"{safe_stem}{suffix}"
            try:
                path.write_bytes(base64.b64decode(payload, validate=False))
                image["saved_path"] = str(path.relative_to(assets_dir.parent))
                if mime_type:
                    image["mime_type"] = mime_type
            except Exception:
                image["saved_path"] = None
            if not store_image_base64:
                image["image_base64"] = "[stripped; image saved to saved_path when decoding succeeded]"
    return cloned


def excerpt_text(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + f"\n\n[Excerpt truncated at {max_chars} characters.]"


def split_markdown_pages(markdown: str) -> dict[int, str]:
    """Split a cached OCR markdown file by `## Page N` headings."""

    matches = list(_PAGE_HEADING_RE.finditer(markdown))
    if not matches:
        return {1: markdown}
    pages: dict[int, str] = {}
    for idx, match in enumerate(matches):
        page_no = int(match.group(1))
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(markdown)
        pages[page_no] = markdown[start:end].strip() + "\n"
    return pages


def select_markdown_pages(markdown: str, pages: str | None) -> str:
    wanted = parse_human_pages(pages)
    if wanted is None:
        return markdown
    available = split_markdown_pages(markdown)
    selected: list[str] = []
    for zero_based in wanted:
        page_no = zero_based + 1
        if page_no in available:
            selected.append(available[page_no])
    if not selected:
        return f"[No requested pages found. Requested {pages}; available pages: {sorted(available)}]\n"
    return "\n".join(selected).rstrip() + "\n"


def search_markdown(markdown: str, query: str, *, max_matches: int = 10, context_chars: int = 300) -> list[dict[str, Any]]:
    """Case-insensitive literal search with page-aware snippets."""

    needle = query.strip()
    if not needle:
        return []
    lower = markdown.lower()
    needle_lower = needle.lower()
    pages = split_markdown_pages(markdown)
    matches: list[dict[str, Any]] = []

    for page_no, page_text in pages.items():
        page_lower = page_text.lower()
        start = 0
        while True:
            index = page_lower.find(needle_lower, start)
            if index < 0:
                break
            snippet_start = max(0, index - context_chars)
            snippet_end = min(len(page_text), index + len(needle) + context_chars)
            snippet = page_text[snippet_start:snippet_end].strip()
            matches.append({"page": page_no, "offset": index, "snippet": snippet})
            if len(matches) >= max_matches:
                return matches
            start = index + max(1, len(needle_lower))
    return matches

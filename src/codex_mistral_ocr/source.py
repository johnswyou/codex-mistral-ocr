"""Source discovery and fingerprinting."""

from __future__ import annotations

import hashlib
import mimetypes
import re
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from .types import SourceInfo

_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


class SourceError(ValueError):
    """Raised when a source cannot be used for OCR."""


def is_url(source: str) -> bool:
    return bool(_URL_RE.match(source.strip()))


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_info(source: str) -> SourceInfo:
    """Build normalized source metadata for a local path or public URL."""

    raw_source = str(source).strip()
    if not raw_source:
        raise SourceError("PDF source is empty.")

    if is_url(raw_source):
        parsed = urlparse(raw_source)
        label = Path(parsed.path).name or parsed.netloc or "remote-document"
        fingerprint = hashlib.sha256(f"url:{raw_source}".encode("utf-8")).hexdigest()
        mime_type = mimetypes.guess_type(parsed.path)[0] or "application/pdf"
        return SourceInfo(
            source=raw_source,
            kind="url",
            label=label,
            fingerprint=fingerprint,
            mime_type=mime_type,
        )

    path = Path(raw_source).expanduser().resolve()
    if not path.exists():
        raise SourceError(f"File does not exist: {path}")
    if not path.is_file():
        raise SourceError(f"Source is not a file: {path}")

    mime_type = mimetypes.guess_type(path.name)[0] or "application/pdf"
    if path.suffix.lower() != ".pdf" and mime_type != "application/pdf":
        raise SourceError(
            f"This tool is designed for PDFs. Got {path.name!r}. "
            "Mistral OCR supports other document formats, but this Codex workflow intentionally "
            "keeps the MCP tool PDF-focused."
        )

    size = path.stat().st_size
    return SourceInfo(
        source=str(path),
        kind="local",
        label=path.name,
        fingerprint=sha256_file(path),
        size_bytes=size,
        mime_type="application/pdf",
        local_path=path,
    )


def display_source_for_agent(source: SourceInfo) -> str:
    """Return a source string safe to show in Markdown and cache metadata.

    Public/signed PDF URLs can contain query tokens. The client still uses the
    exact URL for OCR, but cached user-facing metadata redacts query strings and
    fragments to avoid persisting bearer-like material in Markdown.
    """

    if source.kind != "url":
        return source.source
    parsed = urlparse(source.source)
    clean = parsed._replace(query="", fragment="")
    display = urlunparse(clean)
    if parsed.query or parsed.fragment:
        display += " [query/fragment redacted]"
    return display

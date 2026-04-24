"""Shared dataclasses for OCR processing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

TransportMode = Literal["data_uri", "file_upload"]
TableFormat = Literal["markdown", "html"]
ConfidenceGranularity = Literal["page", "word"]


@dataclass(frozen=True)
class OCRRequestOptions:
    """Options that affect the content of a Mistral OCR response."""

    model: str = "mistral-ocr-latest"
    pages: tuple[int, ...] | None = None
    include_image_base64: bool = False
    table_format: TableFormat | None = None
    extract_header: bool = False
    extract_footer: bool = False
    confidence_scores_granularity: ConfidenceGranularity | None = None
    image_limit: int | None = None
    image_min_size: int | None = None
    transport: TransportMode = "data_uri"

    def to_payload_options(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "include_image_base64": self.include_image_base64,
            "extract_header": self.extract_header,
            "extract_footer": self.extract_footer,
        }
        if self.pages is not None:
            payload["pages"] = list(self.pages)
        if self.table_format is not None:
            payload["table_format"] = self.table_format
        if self.confidence_scores_granularity is not None:
            payload["confidence_scores_granularity"] = self.confidence_scores_granularity
        if self.image_limit is not None:
            payload["image_limit"] = self.image_limit
        if self.image_min_size is not None:
            payload["image_min_size"] = self.image_min_size
        return payload

    def stable_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "pages": list(self.pages) if self.pages is not None else None,
            "include_image_base64": self.include_image_base64,
            "table_format": self.table_format,
            "extract_header": self.extract_header,
            "extract_footer": self.extract_footer,
            "confidence_scores_granularity": self.confidence_scores_granularity,
            "image_limit": self.image_limit,
            "image_min_size": self.image_min_size,
            "transport": self.transport,
        }


@dataclass(frozen=True)
class SourceInfo:
    """Information about a local or remote document source."""

    source: str
    kind: Literal["local", "url"]
    label: str
    fingerprint: str
    size_bytes: int | None = None
    mime_type: str = "application/pdf"
    local_path: Path | None = None


@dataclass(frozen=True)
class CachedResult:
    """Paths for a cached OCR result."""

    result_id: str
    root: Path
    markdown_path: Path
    response_path: Path
    metadata_path: Path
    assets_dir: Path

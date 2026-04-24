"""Local OCR result cache."""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .types import CachedResult, OCRRequestOptions, SourceInfo

APP_DIR_NAME = "codex-mistral-ocr"


def default_cache_dir() -> Path:
    """Return the cache directory, honoring MISTRAL_OCR_CACHE_DIR."""

    configured = os.getenv("MISTRAL_OCR_CACHE_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    xdg_cache = os.getenv("XDG_CACHE_HOME")
    if xdg_cache:
        return Path(xdg_cache).expanduser().resolve() / APP_DIR_NAME
    return Path.home() / ".cache" / APP_DIR_NAME


def make_result_id(source: SourceInfo, options: OCRRequestOptions) -> str:
    stable = {
        "source_fingerprint": source.fingerprint,
        "source_kind": source.kind,
        "source_label": source.label,
        "mime_type": source.mime_type,
        "options": options.stable_dict(),
        "schema_version": 1,
    }
    encoded = json.dumps(stable, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return __import__("hashlib").sha256(encoded).hexdigest()[:32]


def cached_paths(result_id: str, cache_dir: Path | None = None) -> CachedResult:
    root = (cache_dir or default_cache_dir()) / result_id
    return CachedResult(
        result_id=result_id,
        root=root,
        markdown_path=root / "document.md",
        response_path=root / "response.json",
        metadata_path=root / "metadata.json",
        assets_dir=root / "assets",
    )


def cache_exists(result: CachedResult) -> bool:
    return result.markdown_path.exists() and result.response_path.exists() and result.metadata_path.exists()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_result(
    result: CachedResult,
    *,
    response: dict[str, Any],
    markdown: str,
    metadata: dict[str, Any],
) -> None:
    result.root.mkdir(parents=True, exist_ok=True)
    result.markdown_path.write_text(markdown, encoding="utf-8")
    write_json(result.response_path, response)
    metadata = dict(metadata)
    metadata.setdefault("cached_at", datetime.now(timezone.utc).isoformat())
    write_json(result.metadata_path, metadata)


def clear_result(result_id: str, cache_dir: Path | None = None) -> bool:
    result = cached_paths(result_id, cache_dir=cache_dir)
    if result.root.exists():
        shutil.rmtree(result.root)
        return True
    return False


def list_results(cache_dir: Path | None = None) -> list[dict[str, Any]]:
    base = cache_dir or default_cache_dir()
    if not base.exists():
        return []
    entries: list[dict[str, Any]] = []
    for item in sorted(base.iterdir()):
        if not item.is_dir():
            continue
        metadata_path = item / "metadata.json"
        if not metadata_path.exists():
            continue
        try:
            metadata = read_json(metadata_path)
        except Exception:
            continue
        metadata["result_id"] = item.name
        metadata["markdown_path"] = str(item / "document.md")
        entries.append(metadata)
    return entries


def resolve_result_id_or_path(value: str, cache_dir: Path | None = None) -> CachedResult:
    """Accept either a result_id or a direct path to a cached result directory/markdown file."""

    text = str(value).strip()
    if not text:
        raise ValueError("result_id is empty")

    candidate = Path(text).expanduser()
    if candidate.exists():
        if candidate.is_file():
            root = candidate.parent
        else:
            root = candidate
        result_id = root.name
        return CachedResult(
            result_id=result_id,
            root=root,
            markdown_path=root / "document.md",
            response_path=root / "response.json",
            metadata_path=root / "metadata.json",
            assets_dir=root / "assets",
        )

    return cached_paths(text, cache_dir=cache_dir)

"""HTTP client for Mistral OCR.

The default local-file path uses a data URI because Mistral's OCR documentation
shows base64 PDF input directly in the `document_url` field. An optional
`file_upload` transport uploads to the `/v1/files` API, asks for a signed URL,
and then submits that signed URL to the OCR endpoint.
"""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

import httpx

from .types import OCRRequestOptions, SourceInfo


class MistralOCRError(RuntimeError):
    """Raised for Mistral OCR request failures."""


def _error_from_response(response: httpx.Response) -> MistralOCRError:
    try:
        body = response.json()
    except ValueError:
        body = response.text
    return MistralOCRError(
        f"Mistral API error {response.status_code} for {response.request.method} "
        f"{response.request.url}: {body}"
    )


class MistralOCRClient:
    """Small, dependency-light client for the Mistral OCR API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise MistralOCRError(
                "MISTRAL_API_KEY is not set. Create a Mistral API key and export it before running OCR."
            )
        self.base_url = (base_url or os.getenv("MISTRAL_OCR_API_BASE") or "https://api.mistral.ai/v1").rstrip("/")
        timeout = timeout_seconds or float(os.getenv("MISTRAL_OCR_TIMEOUT_SECONDS", "300"))
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout, connect=30.0),
            headers={"Authorization": f"Bearer {self.api_key}"},
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "MistralOCRClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def process_source(
        self,
        source: SourceInfo,
        options: OCRRequestOptions,
        *,
        delete_remote_file_after_ocr: bool = True,
        fallback_to_data_uri: bool = True,
    ) -> dict[str, Any]:
        """Run OCR on a source using the requested transport."""

        if source.kind == "url":
            return self.process_document_url(source.source, options)

        if source.local_path is None:
            raise MistralOCRError("Local source metadata is missing local_path.")

        if options.transport == "file_upload":
            try:
                file_info = self.upload_file(source.local_path, purpose="ocr")
                file_id = str(file_info.get("id") or "")
                if not file_id:
                    raise MistralOCRError(f"Mistral file upload response did not contain an id: {file_info}")
                try:
                    signed = self.get_signed_url(file_id)
                    signed_url = str(signed.get("url") or "")
                    if not signed_url:
                        raise MistralOCRError(f"Mistral signed URL response did not contain a url: {signed}")
                    return self.process_document_url(signed_url, options)
                finally:
                    if delete_remote_file_after_ocr:
                        self.delete_file(file_id)
            except Exception:
                if not fallback_to_data_uri:
                    raise
                # Data URI is the documented and simple fallback for local PDFs.
                return self.process_local_file_data_uri(source.local_path, source.mime_type, options)

        return self.process_local_file_data_uri(source.local_path, source.mime_type, options)

    def process_document_url(self, document_url: str, options: OCRRequestOptions) -> dict[str, Any]:
        payload = options.to_payload_options()
        payload["document"] = {"type": "document_url", "document_url": document_url}
        return self._post_ocr(payload)

    def process_local_file_data_uri(
        self,
        path: Path,
        mime_type: str,
        options: OCRRequestOptions,
    ) -> dict[str, Any]:
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        data_uri = f"data:{mime_type};base64,{encoded}"
        return self.process_document_url(data_uri, options)

    def upload_file(self, path: Path, *, purpose: str = "ocr", visibility: str = "user") -> dict[str, Any]:
        """Upload a file to Mistral's Files API.

        This uses multipart form data, which is the standard wire format for file
        uploads and matches the SDK examples that pass an open file object.
        """

        with path.open("rb") as handle:
            response = self._client.post(
                "/files",
                data={"purpose": purpose, "visibility": visibility},
                files={"file": (path.name, handle, "application/pdf")},
            )
        if response.status_code >= 400:
            raise _error_from_response(response)
        return response.json()

    def get_signed_url(self, file_id: str, *, expiry_hours: int = 24) -> dict[str, Any]:
        response = self._client.get(f"/files/{file_id}/url", params={"expiry": expiry_hours})
        if response.status_code >= 400:
            raise _error_from_response(response)
        return response.json()

    def delete_file(self, file_id: str) -> dict[str, Any] | None:
        response = self._client.delete(f"/files/{file_id}")
        if response.status_code >= 400:
            # Deletion should not hide a successful OCR result.
            return None
        return response.json()

    def _post_ocr(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._client.post("/ocr", json=payload)
        if response.status_code >= 400:
            raise _error_from_response(response)
        try:
            return response.json()
        except ValueError as exc:
            raise MistralOCRError("Mistral OCR response was not JSON.") from exc

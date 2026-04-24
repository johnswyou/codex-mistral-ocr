import json

import httpx

from codex_mistral_ocr.client import MistralOCRClient
from codex_mistral_ocr.processor import build_options


def test_process_document_url_payload_uses_mistral_ocr_options():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["payload"] = json.loads(request.content.decode())
        return httpx.Response(200, json={"model": "mistral-ocr-latest", "pages": []})

    client = MistralOCRClient(
        api_key="test-key",
        base_url="https://api.mistral.ai/v1",
        transport=httpx.MockTransport(handler),
    )
    options = build_options(
        pages="1,3-4",
        include_images=True,
        table_format="markdown",
        extract_header=True,
        extract_footer=True,
        confidence_scores="page",
        image_limit=2,
        image_min_size=64,
    )
    result = client.process_document_url("https://example.com/file.pdf", options)
    client.close()

    assert result["model"] == "mistral-ocr-latest"
    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.mistral.ai/v1/ocr"
    assert captured["payload"] == {
        "model": "mistral-ocr-latest",
        "include_image_base64": True,
        "extract_header": True,
        "extract_footer": True,
        "pages": [0, 2, 3],
        "table_format": "markdown",
        "confidence_scores_granularity": "page",
        "image_limit": 2,
        "image_min_size": 64,
        "document": {"type": "document_url", "document_url": "https://example.com/file.pdf"},
    }


def test_file_upload_transport_uses_signed_url_then_deletes(tmp_path):
    pdf = tmp_path / "file.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path, dict(request.url.params)))
        if request.method == "POST" and request.url.path == "/v1/files":
            return httpx.Response(200, json={"id": "file-123"})
        if request.method == "GET" and request.url.path == "/v1/files/file-123/url":
            return httpx.Response(200, json={"url": "https://signed.example.com/file.pdf?sig=abc"})
        if request.method == "POST" and request.url.path == "/v1/ocr":
            payload = json.loads(request.content.decode())
            assert payload["document"] == {
                "type": "document_url",
                "document_url": "https://signed.example.com/file.pdf?sig=abc",
            }
            return httpx.Response(200, json={"model": "mistral-ocr-latest", "pages": []})
        if request.method == "DELETE" and request.url.path == "/v1/files/file-123":
            return httpx.Response(200, json={"id": "file-123", "deleted": True})
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    client = MistralOCRClient(
        api_key="test-key",
        base_url="https://api.mistral.ai/v1",
        transport=httpx.MockTransport(handler),
    )
    from codex_mistral_ocr.source import source_info

    options = build_options(transport="file_upload")
    result = client.process_source(source_info(str(pdf)), options, fallback_to_data_uri=False)
    client.close()

    assert result["model"] == "mistral-ocr-latest"
    assert [(m, p) for m, p, _params in requests] == [
        ("POST", "/v1/files"),
        ("GET", "/v1/files/file-123/url"),
        ("POST", "/v1/ocr"),
        ("DELETE", "/v1/files/file-123"),
    ]

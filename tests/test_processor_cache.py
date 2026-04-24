from codex_mistral_ocr import processor


class FakeClient:
    calls = 0

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return None

    def process_source(self, _src, _options):
        FakeClient.calls += 1
        return {
            "model": "mistral-ocr-latest",
            "pages": [
                {"index": 0, "markdown": "Cached OCR page one"},
                {"index": 1, "markdown": "Cached OCR page two"},
            ],
            "usage_info": {"pages_processed": 2},
        }


def test_parse_pdf_writes_and_reuses_cache(tmp_path, monkeypatch):
    FakeClient.calls = 0
    monkeypatch.setattr(processor, "MistralOCRClient", FakeClient)
    pdf = tmp_path / "cached.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    cache_dir = tmp_path / "cache"

    first = processor.parse_pdf(str(pdf), cache_dir=cache_dir)
    second = processor.parse_pdf(str(pdf), cache_dir=cache_dir)

    assert FakeClient.calls == 1
    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert "Cached OCR page one" in first["markdown_excerpt"]
    assert (cache_dir / first["result_id"] / "document.md").exists()

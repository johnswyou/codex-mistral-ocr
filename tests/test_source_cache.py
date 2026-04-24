from codex_mistral_ocr.cache import make_result_id
from codex_mistral_ocr.processor import build_options
from codex_mistral_ocr.source import display_source_for_agent, source_info


def test_local_pdf_source_info_and_result_id_stability(tmp_path):
    pdf = tmp_path / "example.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    src = source_info(str(pdf))
    opts = build_options(pages="1-2", table_format="markdown")

    first = make_result_id(src, opts)
    second = make_result_id(src, opts)
    assert first == second
    assert src.kind == "local"
    assert src.mime_type == "application/pdf"

    different_opts = build_options(pages="1", table_format="markdown")
    assert make_result_id(src, different_opts) != first


def test_url_display_source_redacts_query_and_fragment():
    src = source_info("https://example.com/report.pdf?token=secret#frag")
    assert src.source.endswith("token=secret#frag")
    assert display_source_for_agent(src) == "https://example.com/report.pdf [query/fragment redacted]"

from codex_mistral_ocr.formatting import response_to_markdown, search_markdown, select_markdown_pages, split_markdown_pages
from codex_mistral_ocr.source import source_info


def test_response_to_markdown_and_page_selection(tmp_path):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    src = source_info(str(pdf))
    response = {
        "model": "mistral-ocr-latest",
        "pages": [
            {"index": 0, "markdown": "First page text"},
            {"index": 1, "markdown": "Second page text", "tables": [{"id": "t1", "markdown": "| A | B |\n| - | - |"}]},
        ],
        "usage_info": {"pages_processed": 2},
    }
    md = response_to_markdown(response, source=src, result_id="abc", options_display={"pages": None})

    assert "# OCR result: doc.pdf" in md
    assert "## Page 1" in md
    assert "## Page 2" in md
    assert "| A | B |" in md

    pages = split_markdown_pages(md)
    assert set(pages) == {1, 2}
    assert "First page text" in select_markdown_pages(md, "1")
    assert "Second page text" in select_markdown_pages(md, "2")
    assert "First page text" not in select_markdown_pages(md, "2")


def test_search_markdown_returns_page_aware_snippets():
    markdown = "# OCR\n\n## Page 1\nAlpha beta\n\n## Page 2\nGamma Beta delta\n"
    matches = search_markdown(markdown, "beta", max_matches=5, context_chars=10)
    assert [m["page"] for m in matches] == [1, 2]
    assert all("snippet" in m for m in matches)

# PDF workflow guidance for Codex

When a task requires reading, summarizing, searching, citing, or extracting tables from a PDF, prefer the Mistral OCR MCP tools over ad-hoc local PDF extraction.

Recommended flow:

1. Call `mistral_ocr_parse_pdf` with the PDF path or URL. Use `pages` when the task only needs a subset.
2. Use `mistral_ocr_search_result` to find relevant terms before loading large sections.
3. Use `mistral_ocr_read_result` to load only the pages needed for the answer.
4. Cite page numbers from the `## Page N` headings in the cached OCR Markdown.
5. Do not re-run OCR unless `force_refresh=true` is needed.

Remember that OCR sends the document to Mistral and caches extracted text locally.

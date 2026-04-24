---
name: mistral-pdf-ocr
description: Use when Codex needs to read, summarize, search, cite, extract tables from, or answer questions about a PDF. Prefer this for scanned PDFs, complex layouts, tables, multi-column papers, image-heavy PDFs, or any PDF where normal text extraction may be incomplete.
---

# Mistral PDF OCR workflow

Use the Mistral OCR MCP tools whenever a task depends on understanding a PDF.

## Trigger conditions

Use this skill when the user asks you to:

- read or summarize a PDF,
- answer questions about a PDF,
- extract tables, citations, figures, headers, or footers from a PDF,
- inspect a scanned or image-heavy PDF,
- compare information across pages in a PDF,
- cite PDF page numbers.

Do not use this skill for non-PDF files unless the user explicitly asks to adapt the workflow.

## Tool workflow

1. Call `mistral_ocr_parse_pdf` with the PDF path or URL.
   - Use `pages` when the user identifies a specific page range.
   - `pages` is human-facing and 1-based, such as `"1"`, `"2-4"`, or `"1,3-5"`.
   - Use `table_format="markdown"` when table extraction matters.
   - Use `extract_header=true` or `extract_footer=true` when headers/footers matter.
   - Keep `include_images=false` unless visual regions are needed.
2. Save the returned `result_id` mentally for the task.
3. For large PDFs, call `mistral_ocr_search_result` to locate relevant pages before reading broad sections.
4. Call `mistral_ocr_read_result` with selected pages to load only the needed Markdown.
5. Cite page numbers from the `## Page N` headings in answers.
6. Do not re-run OCR for the same document/options unless the user asks for a refresh or the cache appears stale.

## Privacy reminders

OCR sends the PDF to Mistral and stores extracted text in a local cache. Do not use the tool on documents that should not be sent to an external OCR provider. Mention this limitation when it is relevant to the user's task.

## Answering guidance

When reporting findings, distinguish OCR-derived content from your interpretation. If OCR output is unclear, say so and identify the page. Use exact page citations when making claims about the PDF.

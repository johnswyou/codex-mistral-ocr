# Design notes

## Problem

Codex can receive PDF context, but direct PDF extraction is often unreliable for scanned documents, multi-column layouts, tables, image-heavy pages, and documents with headers/footers. The workflow should give Codex a high-quality OCR path without stuffing the entire PDF into the prompt.

## Chosen architecture

This repo uses an MCP server plus a Codex skill/plugin wrapper.

- The **MCP server** is the integration point that lets Codex call deterministic tools.
- The **skill** is the policy layer that tells Codex when to use the tool and how to cite page numbers.
- The **plugin manifest** is the distribution layer for bundling the skill and MCP server configuration.

## Data flow

```text
Codex task involving PDF
        |
        v
mistral-pdf-ocr skill triggers
        |
        v
mistral_ocr_parse_pdf(pdf_path_or_url, options)
        |
        v
Mistral OCR API
        |
        v
local cache: document.md, response.json, metadata.json, assets/
        |
        +--> compact preview returned to Codex
        +--> result_id returned to Codex

Codex then calls:
  mistral_ocr_search_result(result_id, query)
  mistral_ocr_read_result(result_id, pages="...")
```

## Why cache locally

OCR can be slow and expensive. The cache prevents repeated API calls for the same source/options and lets Codex load only the relevant pages. The cache key uses the source fingerprint and OCR options, so changing page ranges, table format, image extraction, or model generates a distinct result.

## Page numbering

Mistral's OCR API accepts zero-based page indexes. Users and Codex normally refer to PDF pages using one-based numbers. The public CLI/MCP interface is one-based and converts internally.

## Local file transport

The default local-file transport is `data_uri`: the PDF is base64 encoded and sent through the OCR `document_url` field. This is simple and directly matches Mistral's documented base64 PDF flow.

An optional `file_upload` transport is also included for large/local PDFs. It uploads the PDF with purpose `ocr`, requests a signed URL from the files endpoint, submits that signed URL to OCR, and deletes the uploaded file afterward when possible. If upload flow fails, it falls back to `data_uri` unless fallback is disabled in code.

## Context management

The parse tool returns only a preview. Full OCR Markdown lives on disk. Codex should search cached results first and read specific pages second. This keeps answers grounded while avoiding large context dumps.

## Privacy defaults

- Images are not requested by default.
- Image base64 is stripped from cached JSON after saving files.
- Signed URL query strings are redacted from cached Markdown/metadata.
- Cache location is configurable through `MISTRAL_OCR_CACHE_DIR`.

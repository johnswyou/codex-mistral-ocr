# Security and privacy

## What leaves the machine

When `mistral_ocr_parse_pdf` is used, the PDF is sent to the Mistral OCR API. Local PDFs are sent as a base64 data URI by default. Public PDF URLs are sent as URLs.

## Local cache

The cache stores:

- `document.md`: Markdown text extracted from the PDF.
- `response.json`: the structured OCR response.
- `metadata.json`: source label, fingerprint, options, model, and cache metadata.
- `assets/`: optional extracted image regions when image extraction is enabled.

Default location:

```text
~/.cache/codex-mistral-ocr
```

Set `MISTRAL_OCR_CACHE_DIR` to move it.

## URL redaction

If a PDF URL contains a query string or fragment, the cached Markdown/metadata redacts those parts. The exact URL is still sent to Mistral during the OCR request because the API needs the real source.

## Recommended practices

- Do not use this tool on documents you are not permitted to send to Mistral.
- Treat the cache like the original document.
- Clear cached results after sensitive work.
- Prefer page ranges when only part of a document is needed.
- Leave `include_images=false` unless the visual content is required.
- Review `.codex-plugin/plugin.json` and `.mcp.json` before distributing a plugin build.

## Clearing cache manually

```bash
rm -rf ~/.cache/codex-mistral-ocr
```

Or remove a single result directory by `result_id`.

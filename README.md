# codex-mistral-ocr

A GitHub-ready Codex extension that gives Codex an MCP tool for parsing PDFs with Mistral's `mistral-ocr-latest` API, plus a Codex skill/plugin wrapper that teaches Codex when to use it.

The goal is simple: when Codex needs to read a PDF, it should prefer a purpose-built OCR workflow over brittle local text extraction. The MCP server sends a local PDF or public PDF URL to Mistral OCR, stores the full structured OCR result in a local cache, and returns Codex a compact preview plus a `result_id`. Codex can then read specific pages or search the cached OCR Markdown without flooding its context window.

## Why this design

This repository ships three layers:

1. **MCP server**: the actual callable tool Codex can use over stdio.
2. **Codex skill**: instructions that make Codex choose the OCR tool when the task involves reading, summarizing, extracting tables from, or answering questions about PDFs.
3. **Codex plugin manifest**: packaging metadata so the skill and MCP configuration can be distributed together.

Codex cannot literally intercept every possible attempt to open a PDF. Instead, this project makes the desired behavior explicit and reusable: configure the MCP server, install or copy the skill, and Codex has both the tool and the workflow guidance to use Mistral OCR when PDF visibility matters.

## Features

- Uses `mistral-ocr-latest` by default.
- Accepts local PDF paths and public PDF URLs.
- Supports optional page ranges using human page numbers like `1`, `2-4`, or `1,3-5`.
- Converts Mistral OCR page output into agent-friendly Markdown with `## Page N` headings.
- Provides cached `parse`, `read`, `search`, and `list` workflows.
- Avoids returning huge PDFs into Codex context; Codex can search first, then read selected pages.
- Defaults to not requesting extracted images. When images are requested, returned base64 is saved as files and stripped from cached JSON unless explicitly changed in code.
- Redacts query strings and fragments from URL sources in cached Markdown/metadata so signed URLs are not persisted verbatim.
- Includes tests and local CLI commands for development.

## Quick start for Codex CLI / IDE

### 1. Clone and install

```bash
git clone https://github.com/your-org/codex-mistral-ocr.git
cd codex-mistral-ocr
python -m pip install -e .
```

For development:

```bash
python -m pip install -e '.[dev]'
```

### 2. Export your Mistral API key

```bash
export MISTRAL_API_KEY='your_mistral_api_key_here'
```

Optional environment variables:

```bash
export MISTRAL_OCR_CACHE_DIR="$HOME/.cache/codex-mistral-ocr"
export MISTRAL_OCR_TIMEOUT_SECONDS=300
export MISTRAL_OCR_API_BASE='https://api.mistral.ai/v1'
```

### 3. Add the MCP server to Codex

Edit `~/.codex/config.toml`:

```toml
[mcp_servers.mistral_ocr]
command = "codex-mistral-ocr-mcp"
env_vars = [
  "MISTRAL_API_KEY",
  "MISTRAL_OCR_CACHE_DIR",
  "MISTRAL_OCR_TIMEOUT_SECONDS",
  "MISTRAL_OCR_API_BASE"
]
startup_timeout_sec = 20
tool_timeout_sec = 900
enabled = true
```

Then start Codex and run `/mcp` to confirm that `mistral_ocr` is active.

### 4. Install the skill instructions

For local/user-wide skill discovery:

```bash
mkdir -p ~/.agents/skills
cp -R skills/mistral-pdf-ocr ~/.agents/skills/
```

For a project-scoped workflow, copy the skill into a repository:

```bash
mkdir -p /path/to/repo/.agents/skills
cp -R skills/mistral-pdf-ocr /path/to/repo/.agents/skills/
```

The repository also includes `.agents/skills/mistral-pdf-ocr` for testing the skill when you open Codex in this repo.

### 5. Ask Codex to use a PDF

Example prompt:

```text
Use the Mistral PDF OCR skill to read ./paper.pdf and summarize the argument with page citations.
```

Codex should call `mistral_ocr_parse_pdf`, then use `mistral_ocr_search_result` or `mistral_ocr_read_result` as needed.

## CLI usage outside Codex

```bash
codex-mistral-ocr parse ./paper.pdf --pages '1-3' --table-format markdown
codex-mistral-ocr read <result_id> --pages '2'
codex-mistral-ocr search <result_id> 'methodology'
codex-mistral-ocr list
```

Common parse options:

```bash
codex-mistral-ocr parse ./paper.pdf \
  --model mistral-ocr-latest \
  --pages '1,3-5' \
  --table-format markdown \
  --extract-header \
  --extract-footer \
  --confidence-scores page
```

## MCP tools exposed

| Tool | Purpose |
| --- | --- |
| `mistral_ocr_parse_pdf` | OCR a PDF path/URL, cache full Markdown/JSON, return preview and `result_id`. |
| `mistral_ocr_read_result` | Read cached Markdown by `result_id` and optional page range. |
| `mistral_ocr_search_result` | Search cached Markdown for a literal query and return page-aware snippets. |
| `mistral_ocr_list_cached_results` | List local cached OCR results. |
| `mistral_ocr_health` | Confirm the MCP server is alive and show package version. |

## Cache layout

By default, results are cached under:

```text
~/.cache/codex-mistral-ocr/<result_id>/
  document.md
  response.json
  metadata.json
  assets/
```

Set `MISTRAL_OCR_CACHE_DIR` to move this location. The cache may contain extracted text from sensitive PDFs, so treat it like the original document.

## Privacy and data handling

This tool sends PDF contents to the Mistral API. Do not use it for documents you are not allowed to send to an external OCR provider. Local cache files contain extracted document text and metadata. URL query strings and fragments are redacted from cached Markdown/metadata, but the exact URL is still used in memory when calling the API.

See [`docs/security-and-privacy.md`](docs/security-and-privacy.md) for the full checklist.

## Plugin packaging

The plugin files are included for distribution:

```text
.codex-plugin/plugin.json
.mcp.json
skills/mistral-pdf-ocr/SKILL.md
```

The `.mcp.json` assumes the `codex-mistral-ocr-mcp` command is installed on the user's machine. For marketplace-style distribution, update the `repository`, `homepage`, and legal URLs in `.codex-plugin/plugin.json` after publishing your GitHub repository.

## Development

```bash
python -m pip install -e '.[dev]'
pytest
ruff check .
```

The tests do not call the live Mistral API. HTTP client tests use a mock transport.

## Repository publishing checklist

1. Replace `your-org` in `pyproject.toml`, `.codex-plugin/plugin.json`, and docs.
2. Confirm the package name is available if you plan to publish to PyPI.
3. Run `pytest` and `ruff check .`.
4. Add a real privacy policy URL if distributing as a public Codex plugin.
5. Push to GitHub.

## License

MIT. See [`LICENSE`](LICENSE).

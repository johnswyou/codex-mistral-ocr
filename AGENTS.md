# Repository instructions for Codex

This repository builds a Codex MCP server and skill for PDF OCR with Mistral.

When working on PDFs in this repository, use the `mistral-pdf-ocr` skill or the Mistral OCR MCP tools instead of relying on local PDF text extraction. Keep documentation clear for end users who will install the MCP server through `~/.codex/config.toml` and copy/install the skill.

Run tests before changing packaging or API behavior:

```bash
pytest
```

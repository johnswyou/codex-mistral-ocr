# Codex setup guide

This project is meant to be used from Codex through MCP and a skill.

## Install the Python command

From a cloned repository:

```bash
python -m pip install -e .
```

Verify the CLI command:

```bash
codex-mistral-ocr --version
```

`codex-mistral-ocr-mcp` is a stdio MCP server. It normally runs under Codex, not as a human-facing shell command; launching it directly will wait for MCP protocol messages on stdin.

## Configure Codex MCP

Add this to `~/.codex/config.toml`:

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

Set your key before launching Codex:

```bash
export MISTRAL_API_KEY='your_mistral_api_key_here'
```

In Codex, run `/mcp` and confirm that the server is listed.

## Install the skill

User-wide install:

```bash
mkdir -p ~/.agents/skills
cp -R skills/mistral-pdf-ocr ~/.agents/skills/
```

Repository-scoped install:

```bash
mkdir -p .agents/skills
cp -R skills/mistral-pdf-ocr .agents/skills/
```

Restart Codex if the skill does not appear.

## Prompt examples

```text
Use Mistral PDF OCR to read ./docs/spec.pdf and extract the API requirements with page citations.
```

```text
Parse ./report.pdf with Mistral OCR, search for "revenue recognition", and summarize only the relevant pages.
```

```text
OCR pages 10-14 of ./manual.pdf and extract any tables as Markdown.
```

## Operational notes

- `pages` in the Codex tool is human-facing and 1-based. The server converts it to Mistral's 0-based `pages` parameter.
- `table_format` can be `markdown` or `html`.
- `include_images` defaults to `false` to reduce token/cache bloat and privacy exposure.
- The full OCR result is cached locally; Codex should prefer reading/searching cached results over re-running OCR.

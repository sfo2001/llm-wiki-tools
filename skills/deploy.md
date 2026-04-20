# Deploy Workflow Skill

## When to use

When the user asks you to deploy or serve the wiki externally.

## Always confirm before deploying

Ask the user which target and confirm before running. For Confluence, always
confirm `--no-dry-run` explicitly — the default is dry-run.

## Target reference

### MkDocs Material (recommended for personal use)

```bash
# Serve (blocking — runs until Ctrl-C):
lwt deploy --target mkdocs --wiki-dir wiki [--port 8000]

# Build static site:
lwt deploy --target mkdocs --wiki-dir wiki --build
```

Auto-generates `mkdocs.yml` beside `wiki/` on first run (skips if already present).
The site name is derived from the data-repo directory name. To customise, edit `mkdocs.yml` directly.
Requires `mkdocs-material` installed: `pip install "llm-wiki-tools[mkdocs]"`.

### Local HTTP server (fallback, no install required)

```bash
lwt deploy --target local --wiki-dir wiki [--port 8080]
```

Detects mkdocs → grip → stdlib http.server (priority order). Blocking — runs until Ctrl-C.
Serves raw markdown — no search, no rendered navigation.

### Docker

```bash
# Volume mode (live updates — wiki/ on disk):
lwt deploy --target docker --wiki-dir wiki --mode volume [--port 8443]

# Image mode (baked snapshot — requires Dockerfile in wiki/):
lwt deploy --target docker --wiki-dir wiki --mode image [--port 8443]
```

### Confluence Data Centre

```bash
# Dry-run (safe — default):
lwt deploy --target confluence --wiki-dir wiki

# Live push (requires user confirmation):
lwt deploy --target confluence --wiki-dir wiki --no-dry-run
```

Requires in `.lwt.env`: `CONFLUENCE_URL`, `CONFLUENCE_TOKEN`, `CONFLUENCE_SPACE`.

**Confluence is a stub.** Full markdown-to-storage-format conversion not yet implemented.

## Traceability check before deploy

Run `lwt lint --structural --wiki-dir wiki` and fix all findings before deploying.

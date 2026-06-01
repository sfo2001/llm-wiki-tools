# llm-wiki-tools

[![CI](https://github.com/sfo2001/llm-wiki-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/sfo2001/llm-wiki-tools/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

A design pattern and CLI toolchain (`lwt`) for **personal knowledge bases that an LLM
incrementally builds and maintains** — a persistent wiki of interlinked markdown files,
grown from curated raw sources.

## Why

Plain RAG re-derives knowledge on every query. Humans who try to maintain wikis abandon
them because the bookkeeping — updating cross-references, reconciling contradictions,
keeping summaries current — grows faster than the value. LLMs don't get bored and can
touch 10–15 pages in a single pass, so the wiki keeps **compounding** instead of being
re-derived.

`llm-wiki-tools` handles the dumb plumbing (binary → markdown conversion, BM25 indexing,
structural lint, deployment) while the LLM owns everything inside `wiki/`.

> Inspired by Andrej Karpathy's "LLM wiki" idea
> ([original gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) ·
> [local copy](docs/karpathy-llm-wiki.md)).

## How it works

| Directory   | Owner | Rule                                              |
|-------------|-------|---------------------------------------------------|
| `raw/`      | human | Immutable curated sources. Never modified.        |
| `wiki/`     | LLM   | Owned entirely by the agent — created & maintained.|
| `templates/`| shared| Page templates with traceability frontmatter.     |
| `output/`   | `lwt` | Generated deploy artifacts. Not hand-edited.      |

The human curates sources and asks questions; the LLM summarizes, cross-references, files,
and keeps the bookkeeping current. See [`AGENTS.md`](AGENTS.md) for the full agent contract.

## Install

Requires **Python 3.10+**.

> The PyPI distribution name is **`lwt-wiki`** (the import package is `llm_wiki`,
> the command is `lwt`). It is not yet published to PyPI — install from Git for now.
> Note: an unrelated project owns the name `llm-wiki-tools` on PyPI; do **not**
> `pip install llm-wiki-tools`.

```bash
pip install git+https://github.com/sfo2001/llm-wiki-tools.git
```

Or from a clone, into a virtualenv:

```bash
git clone https://github.com/sfo2001/llm-wiki-tools.git
cd llm-wiki-tools
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"        # add ",mkdocs" for the MkDocs deploy backend
```

## Quick start

```bash
# 1. Scaffold a new knowledge-base repo
lwt init ~/my-wiki

# 2. Drop sources into raw/, then convert one to markdown
lwt ingest raw/some-paper.pdf       # → wiki/.tmp/<date>_some-paper.md

# 3. (the LLM reads the temp file and writes wiki/ pages)

# 4. Find things and keep the wiki healthy
lwt search "retrieval augmented generation"
lwt lint --structural

# 5. Publish
lwt deploy --target mkdocs
```

## The `lwt` CLI

| Command                       | What it does                                                          |
|-------------------------------|----------------------------------------------------------------------|
| `lwt init <path>`             | Scaffold a new data repo (`raw/`, `wiki/`, templates, agent files).   |
| `lwt ingest <file-or-url>`    | Convert PDF / DOCX / PPTX / web URL / markdown → `wiki/.tmp/*.md`.    |
| `lwt search "<terms>"`        | BM25 keyword search over `wiki/`; returns ranked `file:line` hits.    |
| `lwt lint --structural`       | Structural lint — broken links, orphans, missing referenced pages.   |
| `lwt deploy --target <t>`     | Publish `wiki/`: `local`, `docker`, `mkdocs`, or `confluence`.        |
| `lwt update <path>`           | Update an existing data repo's bundled tooling/templates.            |
| `lwt log-entry ...`           | Append a structured entry to `wiki/log.md`.                          |

Supported ingest formats: PDF, DOCX, PPTX, web pages, and raw markdown.
Deploy backends: local files, Docker, [MkDocs Material](https://squidfunk.github.io/mkdocs-material/), and Confluence (dry-run stub).

## Documentation

- [Overview](docs/overview.md) — what it is and why it exists
- [Architecture](docs/architecture.md) — components and data flow
- [Runbook](docs/runbook.md) — day-to-day operations
- [Decisions](docs/decisions.md) — design decision log
- [Roadmap](ROADMAP.md) — planned phases and deferred items

## Development

```bash
pip install -e ".[dev]"
pytest                 # full suite
```

## License

[MIT](LICENSE) © Stefan Förster

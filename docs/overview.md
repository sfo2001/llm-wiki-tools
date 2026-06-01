---
project: llm-wiki-tools
last_updated: 2026-04-26
---

# llm-wiki-tools — Overview

## What this is

A design pattern and CLI toolchain (`lwt`, from `llm-wiki-tools`) for personal knowledge bases where an LLM incrementally builds and maintains a persistent wiki of interlinked markdown files from curated raw sources.

## Why it exists

Plain RAG re-derives knowledge on every query. Humans who try to maintain wikis abandon them because the bookkeeping — updating cross-references, reconciling contradictions, keeping summaries current — grows faster than the value. LLMs don't get bored and can touch 10–15 pages in one pass, so the wiki can be kept compounding instead of re-derived. `llm-wiki-tools` provides `lwt`, a Python CLI that handles the dumb plumbing (binary → markdown conversion, BM25 indexing, structural lint, deployment) while the LLM owns everything inside `wiki/`. Without it, personal knowledge accumulates in browser tabs, scattered notes, and one-shot LLM chats that nothing compounds over.

## Status

- **Active development** — `llm-wiki-tools` v0.1.0 is implemented and tested (102 tests). All four implementation plans are complete. The CLI is usable today.

## The `lwt` CLI

Installed from `llm-wiki-tools` (`/path/to/llm-wiki-tools`):

| Command | What it does |
|---------|-------------|
| `lwt ingest <source>` | Convert PDF / DOCX / PPTX / web URL / markdown to `.tmp/<date>_<name>.md` with traceability frontmatter |
| `lwt search <query>` | BM25 keyword search over `wiki/` pages; returns ranked file:line hits |
| `lwt lint` | Structural lint — broken links, orphaned pages, missing pages referenced in index |
| `lwt deploy --target mkdocs` | Build/serve `wiki/` as a MkDocs Material site (recommended) |
| `lwt init <path>` | Scaffold a new data repo (`raw/`, `wiki/`, templates, AGENTS.md, CLAUDE.md, run.sh, README.md) |

Deploy also supports `--target local`, `--target docker`, `--target confluence`.

## Where the details live

- Architecture: [architecture.md](architecture.md)
- Operations: [runbook.md](runbook.md)
- Decisions: [decisions.md](decisions.md)
- Source pattern: [`karpathy-llm-wiki.md`](karpathy-llm-wiki.md) (Karpathy's original)

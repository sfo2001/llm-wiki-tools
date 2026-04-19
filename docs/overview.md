---
project: llm-wiki-tools
last_updated: 2026-04-19
---

# llm-wiki-tools — Overview

## What this is

A Python CLI (`lwt`) that ingests source documents, searches, lints, and deploys an LLM-maintained markdown wiki.

## Why it exists

I wanted a personal knowledge base where the LLM owns the writing and I own the raw inputs and questions. Off-the-shelf wikis assume a human author; off-the-shelf agent memory is opaque and non-reviewable. `lwt` splits the concerns: raw sources stay immutable under `raw/`, the agent writes markdown into `wiki/`, and deploy targets (local HTTP, Docker nginx, Confluence DC) render it. Without it, every new ingest would be a bespoke script and every query would re-parse sources from scratch.

## Status

- **Active** — in regular use, maintained.

## Where the details live

- Architecture: [architecture.md](architecture.md)
- Operations: [runbook.md](runbook.md)
- Decisions: [decisions.md](decisions.md)

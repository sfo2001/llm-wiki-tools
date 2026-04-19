---
project: llm-wiki-tools
last_updated: 2026-04-19
---

# llm-wiki-tools — Decisions

Append-only log of non-obvious choices. Newest at the top.

## 2026-04-19 — initial setup

**Decision:** Created this project as a CLI (`lwt`) that the LLM drives,
with a separate "data repo" (scaffolded via `lwt init`) holding
`raw/`, `wiki/`, `templates/`, and `AGENTS.md`/`CLAUDE.md`. The tools
live here; the content lives elsewhere.

**Why:** Keeps the code repo small and stable while each knowledge base
evolves on its own git history. Lets one `lwt` install serve any number
of wikis.

**Alternatives considered:**
- Single repo with code + one wiki — rejected; doesn't scale past one
  topic.
- Monolithic agent with in-memory state — rejected; no review surface,
  no git audit trail.
- Confluence-first with a thin CLI wrapper — rejected; wanted markdown
  primary, Confluence as a deploy target (the current
  `ConfluenceBackend` is a stub with dry-run default).

**How this could age badly:** If `lwt` grows enough data-repo-specific
logic that every wiki needs a matching CLI version, the version-pinning
will get painful. The `__version__` + git-hash footer in every page is
the escape hatch — reproducing an old render requires checking out that
tool version.

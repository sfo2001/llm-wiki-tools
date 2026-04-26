# LLM Wiki — System Design

**Date:** 2026-04-15
**Status:** Draft — pending user approval
**Based on:** Karpathy's llm-wiki.md pattern
**Council review:** Passed (4-agent debate, 3 rounds)

---

## Overview

A personal/team knowledge base where an LLM coding assistant (Claude Code or
OpenCode) incrementally builds and maintains a persistent wiki of markdown files.
The LLM owns the wiki layer entirely. The human curates sources, asks questions,
and directs analysis. Python tooling (`lwt`) handles only dumb plumbing: binary
format conversion, BM25 search indexing, structural lint, and deployment sync.

The key differentiator from RAG: knowledge is compiled once and kept current.
Every ingest and every good query answer permanently enriches the wiki. Nothing is
re-derived from scratch on every question.

---

## Repository Structure

### Two repos

**`llm-wiki-tools`** — toolchain (versioned, shared across all wiki instances)

```
llm-wiki-tools/
├── src/
│   └── llm_wiki/
│       ├── __init__.py          # exposes: __version__, __git_hash__
│       ├── ingest/
│       │   ├── pdf.py           # PDF → md (pdftotext → pdfminer → pypdf)
│       │   ├── docx.py          # docx → md (pandoc → python-docx)
│       │   ├── pptx.py          # pptx → md (pandoc → python-pptx)
│       │   ├── confluence.py    # Confluence page → md (REST API)
│       │   ├── web.py           # URL → md (trafilatura → requests+html2text)
│       │   └── raw.py           # .md/.txt/.rst/.org → md (passthrough/pandoc)
│       ├── search/
│       │   └── bm25.py          # BM25 index over wiki/*.md
│       ├── deploy/
│       │   ├── base.py          # WikiBackend ABC (write/deploy only)
│       │   ├── local.py         # serve wiki/ via local HTTP
│       │   ├── docker.py        # wiki/ in Docker container with HTTPS
│       │   └── confluence.py    # push to Confluence DC (stub → real)
│       ├── lint/
│       │   ├── structural.py    # broken links, orphans, missing pages
│       │   └── report.py        # file:line actionable findings output
│       ├── log.py               # shared append-only log writer
│       └── common.py            # frontmatter schema, footer injection, output format
├── scripts/
│   └── lwt.py                   # thin CLI entry point (console_script)
├── pyproject.toml               # lwt entry point, dependencies
├── skills/
│   ├── query.md                 # LLM skill: query workflow, filing answers back
│   ├── ingest.md                # LLM skill: native vs CLI, large doc strategy
│   ├── lint.md                  # LLM skill: structural first, then semantic
│   └── deploy.md                # LLM skill: per-target workflow
├── AGENTS.md                    # canonical schema (provider-agnostic)
└── CLAUDE.md                    # @includes AGENTS.md + Claude Code skill @paths
```

**`llm-wiki-<project>`** — data repo (one per wiki instance)

```
llm-wiki-myproject/
├── raw/                         # immutable source files — never modified
├── wiki/                        # LLM-maintained markdown pages
│   ├── index.md                 # content catalog — updated on every write
│   ├── log.md                   # append-only chronological operation log
│   ├── lint-report.md           # output of lwt lint --structural
│   ├── .tmp/                    # lwt ingest temp files (gitignored)
│   ├── .lwt_cache/              # BM25 index cache (gitignored)
│   └── queries/                 # filed query answers
├── templates/
│   ├── default.md
│   ├── entity.md                # person, system, product, ...
│   ├── concept.md               # topic/concept pages
│   ├── source-summary.md        # per-source ingest summary
│   └── query-answer.md          # filed query answer pages
├── output/                      # deployment artifacts (gitignored or not)
├── .lwt.env                     # credentials/config (gitignored)
├── AGENTS.md                    # default: symlink → llm-wiki-tools/AGENTS.md
│                                # to customise: copy + extend (lwt init handles this)
└── CLAUDE.md                    # project-specific overrides
```

---

## Data Flow

### Ingest flow

```
raw/<file>
  → lwt ingest raw/<file>
  → wiki/.tmp/<date>_<file>.md   (frontmatter + converted body)
  → [LLM reads temp file in chunks if large]
  → [LLM writes/updates wiki pages with traceability frontmatter]
  → wiki/index.md updated
  → wiki/log.md appended
```

`lwt ingest` never writes to `wiki/` — that is exclusively the LLM's job.

Output of `lwt ingest` to stdout (short summary only):

```
Ingested:  wiki/.tmp/2026-04-15_report.pdf.md
Lines:     1847
Sections:  34
Backend:   pdf.pdftotext
Source-SHA: a3f9c12b
```

For large documents (> 200 lines): LLM reads in chunks using `offset`/`limit`,
or dispatches sub-agents to digest specific sections before synthesizing.

Opt-in stdout for small sources: `lwt ingest <file> --output -`

### Wiki page frontmatter (traceability)

Every wiki page carries traceability fields copied from the ingest temp file:

```yaml
---
title: "Report Title"
template: source-summary.md
source: raw/report.pdf
source-sha: "a3f9c12b"
ingest-command: "lwt ingest raw/report.pdf"
ingest-backend: "pdf.pdftotext"
lwt-version: "1.2.0"
lwt-git-hash: "a3f9c12"
ingested-at: "2026-04-15T09:00:00Z"
---
```

Entity and concept pages updated by multiple ingests append to a `sources:` list
rather than overwriting — full provenance lineage is preserved.

### Wiki page footer

Every page ends with:

```markdown
---
*Generated by [llm-wiki-tools v1.2.0](https://github.com/…/commit/a3f9c12)
· 2026-04-15 · template: source-summary.md*
```

### Query flow (compounding loop)

The LLM coding assistant IS the query engine. No CLI tool.

```
[human asks question]
  → LLM reads wiki/index.md
  → [if large wiki] lwt search "<terms>" → ranked page paths
  → LLM reads top candidates with Read/Grep
  → synthesizes answer with [[wiki-page]] citations
  → [if valuable] LLM writes wiki/queries/<slug>.md
  → wiki/index.md updated, wiki/log.md appended
```

This is the compounding loop: every filed query answer enriches the wiki
permanently, the same as an ingested source.

### Lint flow

```
lwt lint --structural wiki/
  → wiki/lint-report.md (file:line:issue format)
  → [LLM reads report]
  → structural fixes first
  → semantic check on flagged pages vs source frontmatter lineage
  → contradictions/gaps reported to user
```

### Deploy flow

```
lwt deploy --target local|docker|confluence [options]
```

Deploy is deprioritized — built after query workflow and ingest are solid.

**Build priority order:** query workflow (AGENTS.md + skills) → lwt ingest →
lwt search → lwt lint → lwt deploy

---

## Format Handlers (`ingest/`, flat — no ABC)

Each handler is a single function: `convert(path) -> (backend_name, markdown_body)`.
The `lwt.py` CLI calls the handler, then writes the result to `wiki/.tmp/<date>_<file>.md`
and prints the summary to stdout. Handlers never write files — only the CLI does.

| Handler        | Primary              | Fallback 1          | Fallback 2     |
|----------------|----------------------|---------------------|----------------|
| `pdf.py`       | pdftotext (poppler)  | pdfminer.six        | pypdf          |
| `docx.py`      | pandoc               | python-docx         | —              |
| `pptx.py`      | pandoc               | python-pptx         | —              |
| `confluence.py`| REST API + html2text | —                   | —              |
| `web.py`       | trafilatura          | requests + html2text| —              |
| `raw.py`       | passthrough          | pandoc (rst/org)    | —              |

Format dispatch: file extension → handler. URL → `web.py`. `--format` overrides.

Native capability hints (in `skills/ingest.md`):
- PDF: Claude can read natively via vision — use for complex layouts
- Web: Claude can fetch natively — use for JS-heavy pages trafilatura misses
- DOCX/PPTX: always use `lwt ingest` — binary formats

---

## BM25 Search (`search/bm25.py`)

```
lwt search "<terms>"   →   ranked list of wiki page paths + snippets
```

- Library: `rank_bm25` (pure Python)
- Index: built on demand over `wiki/**/*.md`, cached in `wiki/.lwt_cache/bm25.pkl`
- Cache invalidated by mtime: any `.md` file newer than cache triggers rebuild
- Tokenization: lowercase, strip markdown syntax, split on whitespace
- Output: tab-separated `path  score  snippet`, top 10 by default
- `--reindex` flag: force rebuild without a query

The LLM uses `lwt search` as one tool among many: `lwt search` for concept
discovery, `Grep` for exact matches, `Read` for page content.

---

## WikiBackend ABC (`deploy/base.py`)

Write/deploy only. No query method — the LLM is the query engine.

```python
class WikiBackend(ABC):

    @property
    @abstractmethod
    def target_name(self) -> str: ...

    @abstractmethod
    def write_page(self, rel_path: str, content: str) -> None:
        """Write a wiki page. Footer injected by common.py before this call."""

    @abstractmethod
    def delete_page(self, rel_path: str) -> None: ...

    @abstractmethod
    def deploy(self, wiki_dir: Path) -> None:
        """Full sync of wiki_dir to the backend target."""
```

### LocalBackend

`deploy()`: detects mkdocs → grip → stdlib http.server; starts server pointing
at `wiki/`. `write_page()`: direct filesystem write — LLM page edits are
immediately visible in the running server.

### DockerBackend

Two modes: volume (wiki/ mounted, live updates) and image (baked snapshot).
`write_page()` writes to wiki/ on disk; volume mount propagates to container.
Constructor accepts optional `compose_file: Path`.

### ConfluenceBackend (stub → real)

Converts markdown to Confluence storage format via `md2cf`. Pushes via
Confluence DC v1 REST API (`/rest/api/content`). Creates page if absent
(matched by title), updates if present. Internal `[[page]]` links resolved
to Confluence page links within the configured space.

`deploy()` is dry-run by default — prints diff of create/update operations.
Actual REST calls require `--dry-run=false` plus user confirmation.

Config (from `.lwt.env`): `CONFLUENCE_URL`, `CONFLUENCE_TOKEN`,
`CONFLUENCE_SPACE`, `CONFLUENCE_PARENT`.

---

## AGENTS.md (canonical schema)

```markdown
# LLM Wiki — Agent Schema

## What this is
A persistent, compounding knowledge base maintained entirely by the LLM.
You write and maintain all wiki pages. The human curates sources, asks questions,
and directs the analysis. You do the summarizing, cross-referencing, filing,
and bookkeeping.

## Directory conventions
| Directory    | Owner  | Rule                                           |
|--------------|--------|------------------------------------------------|
| raw/         | human  | Immutable. Never modify, never delete.         |
| wiki/        | you    | You own this entirely. Create, update, maintain.|
| wiki/.tmp/   | lwt    | Temp ingest files. Read, never commit.         |
| templates/   | shared | Use the closest matching template for new pages.|
| output/      | lwt    | Generated. Do not hand-edit.                   |

## Tool surface
| Command                         | Purpose                                       |
|---------------------------------|-----------------------------------------------|
| lwt ingest <file-or-url>        | Convert source → wiki/.tmp/<name>.md          |
| lwt ingest <file> --output -    | Convert small source → stdout (opt-in only)   |
| lwt search "<terms>"            | BM25 keyword search over wiki/ → ranked paths |
| lwt lint --structural wiki/     | Structural check → wiki/lint-report.md        |
| lwt deploy --target <t>         | Push wiki/ to output target                   |

## Workflows

### Query (you are the query engine — no CLI tool)
1. Read wiki/index.md to identify candidate pages
2. If wiki is large or index is ambiguous: run `lwt search "<key terms>"`
3. Read top candidates with Read/Grep tools
4. Synthesize answer with [[wiki-page]] citations
5. Ask user: "Worth filing this as a wiki page?"
6. If yes: write wiki/queries/<slug>.md using query-answer.md template
7. Update wiki/index.md, append to wiki/log.md

### Ingest
1. Run: lwt ingest <file-or-url>
2. Read the summary line (path, lines, sections, backend)
3. Small doc (< 200 lines): read full temp file
4. Large doc: read in chunks (offset/limit) or dispatch sub-agent to digest sections
5. Discuss key takeaways with user before writing anything
6. Select template from templates/ — source-summary.md for ingested sources
7. Write/update wiki pages — copy traceability frontmatter from temp file header
8. One source typically touches 5–15 wiki pages (summary + entity/concept updates)
9. Update wiki/index.md, append to wiki/log.md:
   `## [YYYY-MM-DD] ingest | <source title>`

### Lint
1. Run: lwt lint --structural wiki/
2. Read wiki/lint-report.md — work through findings top to bottom
3. Fix structural issues first (broken links, orphans, missing pages)
4. Semantic lint: for flagged pages, read page + check source frontmatter lineage
5. Flag contradictions, stale claims, unresolvable gaps to user
6. Append to wiki/log.md: `## [YYYY-MM-DD] lint | <finding count>`

### Deploy
1. Confirm target with user before running
2. Run: lwt deploy --target <local|docker|confluence> [options]
3. Confluence is stub — dry-run only unless user confirms --dry-run=false

## Wiki page conventions
- Every page uses a template from templates/
- Every page has YAML frontmatter with traceability fields
- Every page footer: lwt version, git hash, date, template name
- Cross-links: [[page-name]] syntax
- wiki/index.md: updated on every write, one line per page with summary
- wiki/log.md: append-only, entries prefixed ## [YYYY-MM-DD] <op> | <title>

## Schema evolution
This file is a living contract. Propose additions when you discover conventions
that work well. Human approves. Changes are git commits, not chat messages.
```

---

## CLAUDE.md (thin wrapper)

```markdown
# LLM Wiki — Claude Code additions
@path skills/query.md
@path skills/ingest.md
@path skills/lint.md
@path skills/deploy.md

---
# (paste full AGENTS.md content here, OR use your agent's @include mechanism
#  if supported — e.g. @file:AGENTS.md in Claude Code)
```

---

## Skills Scaffold

### `skills/query.md`
- Decision tree: < 50 pages → index + Read; 50–200 → lwt search first;
  > 200 → lwt search + Grep
- When to file answers back: synthesis across 3+ pages, comparisons,
  analysis the user will want again, discovered connections
- When NOT to file: one-sentence lookups, navigation answers

### `skills/ingest.md`
- Native capability hints per format (PDF/web: native possible; DOCX/PPTX: always lwt)
- Large doc strategy: sub-agent delegation for > 500 lines
- What to write per ingest: source-summary + entity updates + concept updates +
  contradiction notes

### `skills/lint.md`
- Phase 1 structural: fix order = broken links → missing pages → orphans → stale index
- Phase 2 semantic: only on flagged pages; check wiki page vs source frontmatter lineage;
  report to user before making changes

### `skills/deploy.md`
- Per-target commands and options
- Traceability check before deploy (verify lwt-version frontmatter present)
- Confluence stub warning + confirmation gate

---

## Credentials & Config

All backend config from `.lwt.env` in data repo root (gitignored):

```
CONFLUENCE_URL=https://confluence.example.com
CONFLUENCE_TOKEN=...
CONFLUENCE_SPACE=MYSPACE
CONFLUENCE_PARENT=Wiki Home
DOCKER_PORT=8443
LOCAL_PORT=8080
```

---

## Open Items / Deferred

- `lwt init` command to scaffold a new data repo (symlink AGENTS.md, create
  directory structure, write .gitignore)
- Optional `qmd` integration as alternative to `lwt search` at large scale
- Confluence storage format edge cases (tables, code blocks, image attachments)
- Multi-user data repo workflow (branch-per-ingest? review gates?)

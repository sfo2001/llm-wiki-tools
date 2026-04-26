# LLM Wiki — Agent Schema

## What this is

A persistent, compounding knowledge base maintained entirely by the LLM.
You write and maintain all wiki pages. The human curates sources, asks
questions, and directs the analysis. You do the summarizing,
cross-referencing, filing, and bookkeeping.

## Directory conventions

| Directory    | Owner  | Rule                                            |
|--------------|--------|-------------------------------------------------|
| raw/         | human  | Immutable. Never modify, never delete.          |
| wiki/        | you    | You own this entirely. Create, update, maintain.|
| wiki/.tmp/   | lwt    | Temp ingest files. Read, never commit.          |
| templates/   | shared | Use the closest matching template for new pages.|
| output/      | lwt    | Generated. Do not hand-edit.                    |

## Tool surface

| Command                          | Purpose                                        |
|----------------------------------|------------------------------------------------|
| lwt ingest <file-or-url>         | Convert source → wiki/.tmp/<name>.md           |
| lwt ingest <file> --output -     | Convert small source → stdout (opt-in only)    |
| lwt search "<terms>"             | BM25 keyword search over wiki/ → ranked paths  |
| lwt lint --structural            | Broken-link / orphan / missing-page check      |
| lwt lint --newlines              | Every wiki/**/*.md ends with one trailing `\n` |
| lwt lint --append-only           | No prior log.md `## [date]` header was changed |
| lwt lint --all                   | Run every check above                          |
| lwt log-entry --op X --title Y   | Atomically append to wiki/log.md (never edit)  |
| lwt deploy --target <t>          | Push wiki/ to output target                    |
| lwt init <path>                  | Scaffold a new data repo                       |
| lwt update [--apply] [--force]   | Refresh bundled assets (AGENTS.md, skills/, run.sh) from current lwt |

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

The human typically runs `lwt ingest` themselves, then opens Claude and says
"I ingested raw/file.pdf" or "process the file I just ingested". Either path
leads to the same workflow:

1. If `lwt ingest` not yet run: `lwt ingest <file-or-url> --wiki-dir wiki`
2. Read the summary output (path, lines, sections, backend)
3. **Small doc (< 200 lines):** read full temp file in one pass
4. **Large doc (200–500 lines):** read in chunks using offset/limit
5. **Very large doc (> 500 lines):** dispatch sub-agents per section, synthesize
6. Discuss key takeaways with user before writing anything
7. Select template: source-summary.md for ingested sources
8. Write/update wiki pages — copy traceability frontmatter from temp file header
9. Typical scope: 1 source-summary + 3–10 entity/concept page updates
10. Update wiki/index.md (purely additive — never remove prior entries)
11. **Append to wiki/log.md using `lwt log-entry`** — do not hand-edit the file:
    ```
    lwt log-entry --op ingest --title "<source title>" --body-file - <<'EOF'
    - Source: <path-or-url>
    - Backend: <ingest-backend>
    - Wiki pages created (N): ...
    EOF
    ```
    Hand-editing risks overwriting prior `## [date]` headers. `lwt log-entry`
    always appends at the end of file and never touches existing content.
12. Verify: `lwt lint --append-only --newlines --wiki-dir wiki` → exit 0

### Lint

1. Run: `lwt lint --all` (or any subset of `--structural`, `--newlines`, `--append-only`)
2. Read wiki/lint-report.md — work through findings top to bottom
3. Fix structural issues first (broken links, orphans, missing pages)
4. Fix `missing_newline` / `extra_newline` findings — every file ends with one `\n`
5. Resolve `log_header_modified` findings by restoring the prior `## [date]` header
   and using `lwt log-entry` to add the new entry instead of hand-editing
6. Semantic lint: for flagged pages, read page + check source frontmatter lineage
7. Flag contradictions, stale claims, unresolvable gaps to user
8. Record the lint via `lwt log-entry --op lint --title "<N> findings"`

### Deploy

1. Confirm target with user before running
2. Run the appropriate command:
   - `lwt deploy --target mkdocs --wiki-dir wiki` — MkDocs Material site (recommended, requires `pip install "llm-wiki-tools[mkdocs]"`)
   - `lwt deploy --target mkdocs --wiki-dir wiki --build` — build static site to `.build/site/`
   - `lwt deploy --target local --wiki-dir wiki` — plain HTTP fallback
   - `lwt deploy --target docker --wiki-dir wiki --mode volume`
3. Confluence is a stub — dry-run only unless user confirms `--no-dry-run`

## Wiki page conventions

- Every page uses a template from templates/
- Every page has YAML frontmatter with traceability fields
- Frontmatter key for template traceability: `lwt_template: <template-name>.md` (**not** `template:` — that key is reserved by MkDocs and will break the site)
- Every page footer: lwt version, git hash, date, template name
- Cross-links: [[page-name]] syntax
- Every file ends with exactly one trailing newline (enforced by `lwt lint --newlines`)
- wiki/index.md: updated on every write, one line per page with summary; additive only
- wiki/log.md: append-only, entries prefixed `## [YYYY-MM-DD] <op> | <title>`.
  Always grow it with `lwt log-entry`, never with manual Edit/Write — the CLI
  guarantees prior entries stay intact (verified by `lwt lint --append-only`)

## Schema evolution

This file is a living contract. Propose additions when you discover conventions
that work well. Human approves. Changes are git commits, not chat messages.

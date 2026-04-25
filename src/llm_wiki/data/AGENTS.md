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
| lwt lint --structural            | Structural check → wiki/lint-report.md         |
| lwt deploy --target <t>          | Push wiki/ to output target                    |
| lwt init <path>                  | Scaffold a new data repo                       |

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
10. Update wiki/index.md, append to wiki/log.md:
    `## [YYYY-MM-DD] ingest | <source title>`

### Lint

1. Run: `lwt lint --structural`
2. Read wiki/lint-report.md — work through findings top to bottom
3. Fix structural issues first (broken links, orphans, missing pages)
4. Semantic lint: for flagged pages, read page + check source frontmatter lineage
5. Flag contradictions, stale claims, unresolvable gaps to user
6. Append to wiki/log.md: `## [YYYY-MM-DD] lint | <finding count> findings`

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
- Every page footer: lwt version, git hash, date, template name
- Cross-links: [[page-name]] syntax
- wiki/index.md: updated on every write, one line per page with summary
- wiki/log.md: append-only, entries prefixed `## [YYYY-MM-DD] <op> | <title>`

## Schema evolution

This file is a living contract. Propose additions when you discover conventions
that work well. Human approves. Changes are git commits, not chat messages.

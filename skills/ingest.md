# Ingest Workflow Skill

## When to use

When a user adds a source to raw/ and asks you to process it.

## Native capability hints

| Format | Strategy |
|--------|----------|
| PDF | Try `lwt ingest` first. For complex layouts, use native vision (Read tool on PDF path). |
| Web URL | Try `lwt ingest <url>` first. For JS-heavy pages trafilatura misses, fetch natively. |
| DOCX / PPTX | Always use `lwt ingest` — binary formats, no native support. |
| MD / TXT | `lwt ingest` or Read directly — both work. |
| Confluence page | `lwt ingest <rest-api-url>` — requires CONFLUENCE_TOKEN in .lwt.env. |

## Steps

1. Run: `lwt ingest <file-or-url> --wiki-dir wiki`
2. Read the summary output (path, lines, sections, backend)
3. **Small doc (< 200 lines):** read full temp file in one pass
4. **Large doc (200–500 lines):** read in chunks using offset/limit
5. **Very large doc (> 500 lines):** dispatch sub-agents per section, then synthesize
6. Discuss key takeaways with user before writing anything
7. Select template: `source-summary.md` for ingested sources
8. Write/update wiki pages — copy traceability frontmatter from temp file header
9. Typical scope: 1 source-summary page + 3–10 entity/concept updates
10. **Self-review before finalizing** — no new tooling, do this yourself before moving on:
    - **Duplicate check:** re-read `wiki/index.md`. If a page you just wrote covers the same
      concept as an existing entry, merge into the existing page instead of leaving both.
    - **Link check:** for every `[[page-name]]` you wrote, confirm a file with that basename
      exists under `wiki/` (a page you just created in this pass counts) —
      `lwt lint --structural` catches any that don't.
    - **Frontmatter check:** confirm every field from "Traceability frontmatter" below is
      present on every page you wrote, with no placeholder value left in.

    If self-review finds nothing to fix, say so explicitly rather than skipping the step
    silently.
11. Update `wiki/index.md`, append to `wiki/log.md`:
    `## [YYYY-MM-DD] ingest | <source title>`

## Traceability frontmatter

Copy these fields from the temp file header to every wiki page you write:

```yaml
source: raw/filename.ext
source-sha: "a3f9c12b"
ingest-command: "lwt ingest raw/filename.ext"
ingest-backend: "pdf.pdftotext"
lwt-version: "0.1.0"
lwt-git-hash: "abc1234"
ingested-at: "2026-04-15T09:00:00Z"
```

For pages updated by multiple ingests, use a `sources:` list.

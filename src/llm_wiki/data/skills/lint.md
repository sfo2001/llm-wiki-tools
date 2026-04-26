# Lint Workflow Skill

## When to use

When the user asks you to health-check or clean up the wiki.

## Phase 1: Mechanical lint (automated)

Run: `lwt lint --all --wiki-dir wiki`

This combines three independent checks and writes `wiki/lint-report.md`
with `file:line: [type] message` findings:

| Flag | Issue types caught |
|------|--------------------|
| `--structural` | `broken_link`, `missing_page`, `orphan` |
| `--newlines`   | `missing_newline`, `extra_newline` |
| `--append-only`| `log_header_modified` (prior log entry overwritten or removed since HEAD) |

Fix order:
1. **log_header_modified** — restore the missing `## [date]` header in `wiki/log.md`
   and re-add the new entry with `lwt log-entry` (never by hand-editing the file)
2. **missing_newline / extra_newline** — every file ends with exactly one `\n`
3. **broken_link** — page links to non-existent page → create page or fix link
4. **missing_page** — index.md references non-existent page → same fix
5. **orphan** — page has no inbound links → add link from related page, or delete

Re-run `lwt lint --all` to verify zero findings.

## Phase 2: Semantic lint (LLM judgment)

Only run on pages flagged by structural lint or pages you have reason to doubt.

For each flagged page:
1. Read the wiki page
2. Read source pages listed in its `source:` / `sources:` frontmatter
3. Compare claims against source content
4. Flag contradictions, stale claims, or missing coverage to user

**Do not make semantic changes without reporting to the user first.**

## Completing lint

Record the lint via the CLI (never hand-edit `wiki/log.md`):

```
lwt log-entry --op lint --title "<N> structural findings fixed, <M> semantic issues flagged"
```

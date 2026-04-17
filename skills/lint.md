# Lint Workflow Skill

## When to use

When the user asks you to health-check or clean up the wiki.

## Phase 1: Structural lint (automated)

Run: `lwt lint --structural --wiki-dir wiki`

This writes `wiki/lint-report.md` with `file:line: [type] message` findings.

Fix order:
1. **broken_link** — page links to non-existent page → create page or fix link
2. **missing_page** — index.md references non-existent page → same fix
3. **orphan** — page has no inbound links → add link from related page, or delete

Re-run `lwt lint --structural` to verify zero findings.

## Phase 2: Semantic lint (LLM judgment)

Only run on pages flagged by structural lint or pages you have reason to doubt.

For each flagged page:
1. Read the wiki page
2. Read source pages listed in its `source:` / `sources:` frontmatter
3. Compare claims against source content
4. Flag contradictions, stale claims, or missing coverage to user

**Do not make semantic changes without reporting to the user first.**

## Completing lint

Append to `wiki/log.md`:
`## [YYYY-MM-DD] lint | <N> structural findings fixed, <M> semantic issues flagged`

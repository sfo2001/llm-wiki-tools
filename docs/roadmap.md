---
project: llm-wiki-tools
last_updated: 2026-07-20
---

# llm-wiki-tools — Roadmap

**Decisions not yet made, and work known to be coming.**

This is the complement of `docs/adr/`: that store holds what was **decided**, this one holds
what is **still open**. The two share a lifecycle — when an open question here gets settled,
it graduates into an ADR and is removed from this file. Nothing should appear in both.

What does *not* belong here:

- A consequence or known weakness of a decision already made → the `Consequences` section of
  that decision's ADR.
- A permanent "we will never do this" → `docs/charter.md` under Non-goals.
- Something that broke and how it was fixed → `docs/runbook.md`.
- Current structure → `docs/architecture.md`.

## Open questions

Decisions that will have to be made, with the options as they stand today. Each becomes an
ADR when it is settled.

Nothing open.

## Known future work

Things already decided in principle but not built, and deferred cleanups. Include why it was
deferred — a deferral without a reason is indistinguishable from an oversight.

### Update / distribution flow

#### Phase 2 — manifest-tracked updates

**What.** Add `.lwt-manifest.yaml` to every scaffolded wiki, recording `{file → bundled SHA}` at install / last-update time. `lwt update` reclassifies each tracked file as one of:

- *unchanged from bundle, bundle changed* → safe to update silently
- *user-modified since last update* → ask before overwriting
- *bundle and user both changed* → conflict (handled by Phase 3)

**Why.** Today's two-class taxonomy (ADR-0005) can't distinguish "user customised CLAUDE.md" from "bundled CLAUDE.md drifted since last update" — both look like a diff. Manifest fixes that.

**Deferred because.** Ships after real usage shows which files people actually customise. **Trigger:** either the user reports a false-positive `differs` on customisable files ≥3 times in a session, or the bundle ships a CLAUDE.md / template change that needs to flow into wikis without `--force` clobbering real customisations.

**Rough effort.** ~250 LOC + tests + bootstrap migration for existing wikis.

#### Phase 3 — three-way merge for customisable files

**What.** When both the bundle and the working copy have diverged from the manifest's known-base SHA, run `git merge-file --diff3` to attempt a clean merge. On conflict, write `<file>.merge-conflict` with markers and exit non-zero so the user resolves explicitly.

**Why.** Forces the user to choose only when there's genuine conflict; clean-mergeable bundle changes flow silently into customised files.

**Deferred because.** Depends on Phase 2 shipping first. **Trigger:** the first time a merge conflict on a customisable file (e.g. CLAUDE.md, AGENTS.md if reclassified) actually annoys someone.

**Rough effort.** ~100 LOC if `git merge-file` is on `$PATH` (assumed); pure-Python `merge3` otherwise.

#### Phase 4 — content migrations (not just file copies)

**What.** Versioned, idempotent migration scripts under `src/llm_wiki/migrations/` rewrite content inside `wiki/**`. Manifest records `applied_migrations: [0001, 0002]`. `lwt update` runs unapplied migrations after the asset refresh.

**Why.** Some upgrades aren't file copies — e.g. the `template:` → `lwt_template:` frontmatter rename had to touch every wiki page. Future schema changes (cross-link syntax, frontmatter shape, directory restructure) need a runner that can transform content, not just overwrite files.

**Deferred because.** No concrete migration exists yet to seed the runner. **Trigger:** the first concrete schema change that can't be handled by a file copy.

**Rough effort.** ~200 LOC for the runner + the first migration.

#### Phase 5 — `lwt doctor` and deploy awareness

**What.** Two pieces:

1. `lwt doctor` reports installed lwt version vs manifest's expected, drift summary (counts of identical/outdated/customised files), pending migrations. Exits 0 / 1 for CI use.
2. `lwt update` detects a running `mkdocs serve` (pidfile or `pgrep`) and a running docker container; surfaces guidance ("live-reload will pick this up" / "rebuild with `lwt deploy --target docker --mode image`").

**Why.** Tells users "your wiki is N versions behind" without them asking. Prevents shipping updates that break a running server.

**Deferred because.** Only one active wiki exists today, so drift-tracking has no real signal yet. **Trigger:** ≥3 active wikis (more than test-wiki + one other), or the first time CI/automation needs to gate on update status.

**Rough effort.** ~150 LOC.

### Search & retrieval

#### qmd integration — semantic search for large wikis

**What.** Adopt [qmd](https://github.com/tobi/qmd) (Tobi Lütke's hybrid search tool — BM25 + vector ANN + LLM reranking, ships with an MCP server) as the scaling path for `lwt search`. Three increments, ship in order:

1. **Documentation only.** Update `docs/runbook.md` and the bundled `AGENTS.md` / `skills/query.md` so a wiki maintainer knows when to switch from `lwt search` to qmd and how to install it (`claude mcp add --scope user qmd -- npx -y @tobi/qmd`).
2. **Wrapper command.** `lwt search --backend qmd <query>` shells out to `npx @tobi/qmd query` and returns the same `path:line:score` shape as the BM25 backend, so Claude's `query.md` skill is identical regardless of backend.
3. **Bundled MCP config (optional).** `lwt init` (or a separate `lwt search-stack qmd`) drops a `.mcp.json` into the wiki repo configuring qmd as a Claude MCP server, so Claude calls qmd directly rather than via `lwt`. Wiki repo becomes the install surface.

**Why.** `lwt search` is BM25Plus only — keyword search with no semantic understanding. Once a wiki has hundreds of pages, synonyms and paraphrasing start missing relevant content. Karpathy's gist names qmd as the recommended scaling tool, and the comparison table in [`test-wiki/wiki/entities/qmd.md`](http://localhost:8000/entities/qmd) makes the tradeoff explicit (~2 GB model footprint + 1-3 s startup latency in exchange for vector + rerank quality).

**Deferred because.** No wiki is currently large enough to need it. **Trigger:** either a wiki crosses ~200-300 pages and missed-search complaints surface, or the first user wants Claude to call search via MCP rather than `lwt search` shell-out.

**Rough effort.** Step 1 (docs): ~1 hour. Step 2 (wrapper): ~150 LOC + tests. Step 3 (MCP config bundle): ~50 LOC + a templated `.mcp.json`.

**Resources already available locally:**
- qmd repo cloned at `/path/to/qmd` — read README directly for current architecture and CLI shape before specifying.
- Entity page at `test-wiki/wiki/entities/qmd.md` — full comparison vs `lwt search` already documented.

## Watch items

Assumptions that are fine today but would need revisiting if some condition changes. Name
the condition, not just the worry — an unfalsifiable worry never gets closed.

- **`print()` instead of `click.echo()` in deploy backends** — current `print()` is correct for user-visible CLI status; converting buys little today. Revisit if anyone reports broken output redirection, or wants a `--quiet` flag.
- **No `CHANGELOG.md`** — annotated git tags (`git log v0.1.0..v0.2.0`) substitute today; minimal personal audience. Revisit if an external audience grows, or release notes get long enough that `git log` is unwieldy.
- **Confluence `ConfluenceClient` not shared between `ingest` and `deploy` modules** — a DRY win identified in a prior audit; both currently work standalone. Revisit if either side gains a second piece of duplicated logic, or auth/header handling needs to evolve.
- **Pandoc subprocess pattern not factored into a shared helper across `ingest/{docx,pptx,raw}.py`** — the pattern repeats 4× but each instance is short. Revisit if a new pandoc-using ingest handler is added (N=5+), or the call shape changes.
- **`run.sh` / `run.ps1` wrappers drifting from the `lwt` CLI** — if the wrapper commands diverge from the actual CLI they become misleading. Safe today because the wrappers are thin: they add `--wiki-dir "$SCRIPT_DIR/wiki"` and delegate everything else to `lwt`. Revisit if a wrapper ever grows logic of its own beyond that delegation. _(Recovered from the 2026-04-25 "Plan 4: human-facing scaffold additions" entry, which was dropped in the 2026-07-20 decisions.md migration and has no corresponding ADR.)_

---

_If a section has nothing in it, say so explicitly ("Nothing open." / "Nothing deferred.")
rather than leaving the placeholder text. An empty heading reads as an unfinished document;
an explicit "nothing" reads as a considered one._

# llm-wiki-tools — Roadmap

Tracks the deploy / update / distribution story. Each phase has a **Trigger** that says when to actually build it — the cost of speculative implementation is higher than the cost of waiting.

Newest at the top.

---

## Already shipped

| Tag | Date | What |
|---|---|---|
| **v0.2.0** | 2026-04-26 | **Phase 0** — `hatch-vcs` versioning, `release.sh` wheel pipeline, `run.sh` / `run.ps1` self-bootstrap from `tools/*.whl`, `lwt update --tools <wheel>`, `lwt init --wheel <path>`. **Phase 1** — `lwt update [--apply] [--force]` refreshes bundled assets using a hardcoded canonical / customisable taxonomy. |
| **v0.1.0** | 2026-04-26 | Initial CLI: ingest, search, lint, deploy, init, log-entry. Four deploy backends (local, mkdocs, docker, confluence). Six ingest handlers (pdf, docx, pptx, raw, web, confluence). |

Plans for shipped work live under `docs/superpowers/plans/`. Decisions live in `docs/decisions.md`.

---

## Planned

### Phase 2 — manifest-tracked updates

**What.** Add `.lwt-manifest.yaml` to every scaffolded wiki, recording `{file → bundled SHA}` at install / last-update time. `lwt update` reclassifies each tracked file as one of:

- *unchanged from bundle, bundle changed* → safe to update silently
- *user-modified since last update* → ask before overwriting
- *bundle and user both changed* → conflict (handled by Phase 3)

**Why.** Today's two-class taxonomy can't distinguish "user customised CLAUDE.md" from "bundled CLAUDE.md drifted since last update" — both look like a diff. Manifest fixes that.

**Trigger.** Either: user reports false-positive `differs` on customisable files ≥3 times in a session; or the bundle ships a CLAUDE.md / template change that needs to flow into wikis without `--force` clobbering real customisations.

**Rough effort.** ~250 LOC + tests + bootstrap migration for existing wikis.

---

### Phase 3 — three-way merge for customisable files

**What.** When both the bundle and the working copy have diverged from the manifest's known-base SHA, run `git merge-file --diff3` to attempt a clean merge. On conflict, write `<file>.merge-conflict` with markers and exit non-zero so the user resolves explicitly.

**Why.** Forces the user to choose only when there's genuine conflict; clean-mergeable bundle changes flow silently into customised files.

**Trigger.** Ships after Phase 2, the first time a merge conflict on a customisable file (e.g. CLAUDE.md, AGENTS.md if reclassified) actually annoys someone.

**Rough effort.** ~100 LOC if `git merge-file` is on `$PATH` (assumed); pure-Python `merge3` otherwise.

---

### Phase 4 — content migrations (not just file copies)

**What.** Versioned, idempotent migration scripts under `src/llm_wiki/migrations/` rewrite content inside `wiki/**`. Manifest records `applied_migrations: [0001, 0002]`. `lwt update` runs unapplied migrations after the asset refresh.

**Why.** Some upgrades aren't file copies — e.g. the `template:` → `lwt_template:` frontmatter rename had to touch every wiki page. Future schema changes (cross-link syntax, frontmatter shape, directory restructure) need a runner that can transform content, not just overwrite files.

**Trigger.** The first concrete schema change that can't be handled by a file copy. Don't build the runner until there's a real first migration to seed it.

**Rough effort.** ~200 LOC for the runner + the first migration.

---

### Phase 5 — `lwt doctor` and deploy awareness

**What.** Two pieces:

1. `lwt doctor` reports installed lwt version vs manifest's expected, drift summary (counts of identical/outdated/customised files), pending migrations. Exits 0 / 1 for CI use.
2. `lwt update` detects a running `mkdocs serve` (pidfile or `pgrep`) and a running docker container; surfaces guidance ("live-reload will pick this up" / "rebuild with `lwt deploy --target docker --mode image`").

**Why.** Tells users "your wiki is N versions behind" without them asking. Prevents shipping updates that break a running server.

**Trigger.** ≥3 active wikis (more than test-wiki + one other), or the first time CI/automation needs to gate on update status.

**Rough effort.** ~150 LOC.

---

## Other deferred items

| Item | Why deferred | Revisit when |
|---|---|---|
| `print()` → `click.echo()` in deploy backends | Audit recommendation; current `print()` is correct for user-visible CLI status; converting buys little | Anyone reports broken output redirection or wants `--quiet` |
| `CHANGELOG.md` | Annotated git tags substitute (`git log v0.1.0..v0.2.0`); minimal personal audience | External audience grows or release notes get long enough that `git log` is unwieldy |
| CI / pre-push test gate | Personal repo; full local suite runs in 4 s; `release.sh` rejects dirty trees | First regression slips past local discipline |
| Confluence `ConfluenceClient` shared between ingest + deploy modules | DRY win identified in audit; both currently work | Either side gains its second piece of duplicated logic, or auth/header handling needs to evolve |
| Pandoc subprocess pattern shared helper across `ingest/{docx,pptx,raw}.py` | DRY win identified in audit; pattern repeats 4× but is short | A new pandoc-using ingest handler is added (N=5+) or the call shape changes |

---

## How to use this file

- **Adding a phase:** prefer extending an existing phase to creating a new one. Each phase is one focused capability with a clear trigger; resist roadmap inflation.
- **Shipping a phase:** move it from *Planned* to *Already shipped* with the version tag and date; keep the original "what" / "why" sentences as the historical record.
- **Killing a phase:** move it under *Other deferred items* with a one-line note on why it never happened.

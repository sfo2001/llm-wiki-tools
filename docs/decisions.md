---
project: llm-wiki-tools
last_updated: 2026-04-26
---

# llm-wiki-tools — Decisions

Append-only log of non-obvious choices. Newest at the top.

## 2026-04-26 — Phase 0: hatch-vcs versioning + wheel-in-tools/ distribution

**Decision:** `llm-wiki-tools` is distributed as a Python wheel. The version is derived from annotated git tags via `hatch-vcs` (no static `version =` in `pyproject.toml`). Each scaffolded wiki repo carries the wheel under `tools/llm_wiki_tools-X.Y.Z-py3-none-any.whl`; `run.sh` and `run.ps1` create a per-wiki `venv/` on first run and pip-install the wheel into it. Updates flow via `lwt update --tools <new.whl>` which drops the new wheel into `tools/` and prunes older ones.

**Why:** The previous "editable install on the developer's machine" model meant wikis silently depended on a path nobody else had. Recipients with no access to PyPI, GitHub, or the internal gitea need a single self-contained tarball — `git clone <wiki-repo>` plus Python 3.11+ should suffice. The wheel-in-`tools/` design satisfies that without introducing a network bootstrap step.

**Alternatives considered:** PyPI publish — rejected (personal tool, no audience there). `pip install git+ssh://gitea/...` — rejected (recipients may have no network access to the gitea). Git bundle (`.bundle` file) — rejected (recipients don't need the source history; wheel is smaller and standard). Vendoring lwt source into each wiki — rejected (no version discipline; multiplies maintenance).

**How this could age badly:** Wheels accumulate in the wiki repo's git history (~30 KB per release × N releases). Mitigation: `--prune` removes the working-tree wheel; git history can be filter-repo'd later if it ever bites. `hatch-vcs` requires git history at build time, so a shallow clone can't build — fine, since recipients install the wheel and never build. Tag discipline is human-enforced; `release.sh` rejects untagged builds, so the only way to ship a `.dev` is to bypass `release.sh` deliberately.

## 2026-04-26 — `lwt update` Phase 1: hardcoded canonical/customisable taxonomy

**Decision:** `lwt update` uses a two-class file taxonomy hardcoded in `src/llm_wiki/update.py` — **canonical** files (AGENTS.md, skills/, run.sh, run.ps1) overwrite silently on `--apply`; **customisable** files (CLAUDE.md, README.md, templates/, .gitignore, .lwt.env.example) are left alone unless `--force`. No state file, no manifest.

**Why:** Drift between the tools repo and deployed wikis was previously a manual `cp` exercise, which scales badly and is easy to forget. Hardcoded taxonomy ships in a day and covers the 80% case (refreshing the agent contract + skills) without the bookkeeping cost of a per-file manifest. Phase 2 (planned) adds `.lwt-manifest.yaml` so we can distinguish "user-modified" from "bundle-drift" reliably; Phase 3 adds 3-way merge. Doing the simple version first lets us learn whether the taxonomy boundary (e.g. should `skills/` be customisable too?) is correct before committing to a manifest format.

**Alternatives considered:** Manifest from day one — rejected as premature; we don't yet know which files users actually customise. Single-class "always overwrite, with `--diff` only" — rejected; too easy to clobber a customised CLAUDE.md.

**How this could age badly:** If users routinely customise `skills/*` (currently canonical), they'll lose changes silently on `--apply`. The mitigation is the Phase 2 manifest; the canary is user feedback. README.md substitution name is recovered from line 1 of the deployed README — fragile if the user rewrites the title format.

## 2026-04-26 — docs migrated from ~/devel/llm-wiki

**Decision:** Moved design artifacts (pattern doc, system-design spec, implementation plans, decisions log) from `~/devel/llm-wiki` into `llm-wiki-tools/docs/`. The `~/devel/llm-wiki` repo served as the planning space while the tools were being built.

**Why:** The planning repo is now effectively done — all four plans are complete. Having the docs split across two repos creates confusion about which version is current. `llm-wiki-tools` is the canonical home of the project; its `docs/` is the natural home for all project documentation.

**How this could age badly:** Design artifacts describing the `~/devel/llm-wiki` repo (e.g. references to that path) will be stale. The repo still exists as an archive.

## 2026-04-25 — Plan 4: human-facing scaffold additions

**Decision:** `lwt init` now bundles `README.md`, `run.sh`, `run.ps1`, and `skills/` in the scaffolded data repo. Skills are copied from the bundled `data/skills/` directory; `README.md` is generated from a template with `__NAME__` substitution.

**Why:** The scaffold was LLM-facing only (AGENTS.md, templates). A human picking up a fresh wiki repo had no entry point — no instructions, no wrapper scripts. The `run.sh/run.ps1` wrappers anchor all `lwt` paths to the repo directory so `./run.sh serve` works from any CWD.

**How this could age badly:** If `run.sh` commands diverge from the actual `lwt` CLI, the wrappers become misleading. Mitigation: `run.sh` is thin — it just adds `--wiki-dir "$SCRIPT_DIR/wiki"` and delegates everything else to `lwt`.

## 2026-04-20 — MkdocsBackend replaces LocalBackend as recommended deploy target

**Decision:** `lwt deploy --target mkdocs` (MkDocs Material) is the recommended deploy target for personal use, replacing `--target local`. Plans 1, 2, and 3 are complete; `llm-wiki-tools` v0.1.0 ships 5 commands and 4 deploy targets.

**Why:** MkDocs Material gives full-text search, Material theme, code highlighting, and anchor navigation — everything a personal research wiki needs — with zero configuration beyond `pip install llm-wiki-tools[mkdocs]`. The `LocalBackend` (raw HTTP server) had no search and rendered raw markdown. The `MkdocsBackend` auto-generates `mkdocs.yml` on first run and never overwrites a user-customised one.

**Alternatives considered:** Keep `LocalBackend` as default, add mkdocs as extra. Rejected — the local server is too bare-bones to be the recommended path; calling it "local" already implies "fallback".

**How this could age badly:** If the user customises `mkdocs.yml` heavily, `lwt deploy` will use it as-is (correct). If `mkdocs-material` changes its config schema, the bundled template may need updating.

## 2026-04-19 — documented in the knowledge base

**Decision:** Added overview / architecture / runbook / decisions to `docs/` and opted the project into the central knowledge base.

**Why:** The idea is captured in a single `llm-wiki.md` plus two plans under `docs/superpowers/`. Without a KB entry, the pattern and design intent are invisible from the wiki index and easy to lose.

**Alternatives considered:** Wait until `lwt` has code to document. Rejected — the design phase is itself worth indexing; the KB handles "Experiment" status explicitly.

**How this could age badly:** Design evolves faster than the docs. Mitigation: architecture.md references the spec files rather than inlining them, so the canonical content stays in `docs/superpowers/specs/`.

## 2026-04-15 — two-repo split: tools vs. data

**Decision:** Separate `llm-wiki-tools` (Python package, versioned, shared) from `llm-wiki-<project>` (per-wiki data repo). The CLI (`lwt`) lives in tools; `raw/` and `wiki/` live in data repos. Captured in `docs/superpowers/specs/2026-04-15-llm-wiki-design.md`.

**Why:** One toolchain, many wiki instances. Upgrading the CLI should not force-sync every data repo; changing a wiki's content should not require touching the tooling.

**Alternatives considered:** Monorepo with `tools/` + `wikis/` subdirs. Rejected — makes version pinning per wiki awkward and conflates tool evolution with content evolution.

**How this could age badly:** Bundled `AGENTS.md` / templates in `llm-wiki-tools` drift from what individual wikis actually use. Mitigation: `lwt init` copies schema once; wikis customise from there; tool upgrades never rewrite an existing wiki's `AGENTS.md`.

## 2026-04-15 — LLM owns `wiki/`, CLI does not

**Decision:** `lwt ingest` writes only to `wiki/.tmp/`, never to `wiki/` itself. All wiki-page creation and editing is done by the LLM agent. Captured in `docs/superpowers/specs/2026-04-15-llm-wiki-design.md`.

**Why:** The value of the wiki is the synthesis, cross-referencing, and editorial judgement — exactly the work the LLM is meant to do. If the CLI writes pages, it competes with the agent and produces low-quality content. The CLI's job is the dumb plumbing (format conversion, indexing, linting) that the LLM would do slowly and inefficiently.

**Alternatives considered:** Let `lwt ingest` auto-generate a stub page. Rejected — stubs become dead pages that nobody updates.

**How this could age badly:** If the LLM ever becomes unreliable at page maintenance, we'll need human or CLI-assisted fallbacks. Revisit if the "wiki stays fresh" assumption breaks.

## 2026-04-15 — initial setup

**Decision:** Started `~/devel/llm-wiki` as a thinking space for the pattern described in Karpathy's `llm-wiki.md`.

**Why:** Need a durable place to iterate on design before writing code.

**Alternatives considered:** Start in `llm-wiki-tools` directly. Rejected — no design to implement yet.

**How this could age badly:** This directory becomes a graveyard if the pattern never ships. Mitigation: the plans under `docs/superpowers/plans/` are task-ordered and actionable; either execute them or archive the project.

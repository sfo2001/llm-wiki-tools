# Split `llm-wiki-tools` (package) from per-wiki data repos

*Date: 2026-04-15*

Separate `llm-wiki-tools` (the versioned, shared Python package containing the `lwt` CLI) from `llm-wiki-<project>` (a per-wiki data repo holding `raw/` and `wiki/`). One toolchain serves many wiki instances, so upgrading the CLI never forces a sync of every data repo, and editing a wiki's content never requires touching the tooling.

## Considered Options

A monorepo with `tools/` + `wikis/` subdirs was rejected — it makes version pinning per wiki awkward and conflates tool evolution with content evolution.

## Consequences

Bundled `AGENTS.md` / templates in `llm-wiki-tools` drift from what individual wikis actually use. Mitigation: `lwt init` copies schema once; wikis customise from there; tool upgrades never rewrite an existing wiki's `AGENTS.md`.

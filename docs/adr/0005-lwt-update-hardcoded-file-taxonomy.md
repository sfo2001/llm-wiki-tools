# `lwt update` uses a hardcoded canonical/customisable file taxonomy, not a manifest

*Date: 2026-04-26*

`lwt update` classifies files via a two-class taxonomy hardcoded in `src/llm_wiki/update.py`: **canonical** files (`AGENTS.md`, `skills/`, `run.sh`, `run.ps1`) overwrite silently on `--apply`; **customisable** files (`CLAUDE.md`, `README.md`, `templates/`, `.gitignore`, `.lwt.env.example`) are left alone unless `--force`. There is no manifest or state file yet — this covers the 80% case (refreshing the agent contract + skills) in a day, and lets us learn whether the taxonomy boundary itself is right before committing to a manifest format.

## Considered Options

A `.lwt-manifest.yaml` distinguishing user-modified from bundle-drift files from day one was rejected as premature — we don't yet know which files users actually customise. A single-class "always overwrite, with `--diff` only" model was also rejected — too easy to silently clobber a customised `CLAUDE.md`.

## Consequences

If users routinely customise `skills/*` (currently canonical), they'll lose changes silently on `--apply`. The mitigation is the Phase 2 manifest; the canary is user feedback. `README.md` substitution name is recovered from line 1 of the deployed README — fragile if the user rewrites the title format.

# Write-time validation is mandatory, and maintenance passes prefer the strongest available model, once a weaker model can author `wiki/` directly

*Date: 2026-09-05*

> **The model-tiering clause below (semantic quality → prefer Claude Code) is superseded by
> [ADR-0007](0007-provider-agnostic-llm-client-for-unattended-lwt-jobs.md)** — it assumed reaching
> a stronger model was free-ish, ignoring that Claude Code shares a paid budget with all
> interactive coding work. The write-time-validation clause (structural conformance) still stands.

ADR-0002 ("LLM owns `wiki/`; the CLI does not") assumed the calling agent reliably provides
"synthesis, cross-referencing, and editorial judgement" without saying which model — that
assumption held implicitly because Claude Code was the only calling agent. Local models
(currently Qwen3-30B-A3B via OpenCode/Ollama) now author `wiki/` pages directly, which is
exactly the condition ADR-0002's own `Consequences` section named as revisit-worthy: *"If the
LLM ever becomes unreliable at page maintenance, we'll need human or CLI-assisted fallbacks."*

We're activating that fallback now, split by what it can and can't catch:

- **Structural conformance** (missing/malformed frontmatter, broken wikilinks) is deterministically
  checkable, so it becomes load-bearing CLI infrastructure rather than deferred work — tracked as
  [Gitea #2](http://192.168.178.3:3000/stefan/llm-wiki-tools/issues/2).
- **Semantic quality** (duplicated concepts, missed cross-references, weak synthesis) is not
  deterministically checkable. Rather than embed a second LLM into `lwt` itself (rejected — see
  below), the periodic consolidation pass (orphans, likely-duplicate concepts, cross-link repair —
  [Gitea #3](http://192.168.178.3:3000/stefan/llm-wiki-tools/issues/3)) should run preferentially
  under the strongest available model (today: Claude Code) even when day-to-day ingest/authoring
  runs on a weaker local model. This is a workflow/convention choice (which skill invokes which
  model for which `lwt` operation), not a change to the CLI's own architecture.

## Considered Options

Embedding a second "librarian" LLM agent into `lwt` itself (understory's architecture: every
write mediated by an internal agent turn) was rejected. It solves the semantic-quality gap, but
at the cost of a second LLM call, its own provider/fallback plumbing, and a second failure mode —
baked in as permanent infrastructure regardless of which model is authoring. Model-tiering the
existing periodic maintenance pass gets the same semantic-quality catch without that fixed cost,
and preserves ADR-0002's original split (CLI stays content-agnostic; agents provide judgement).

## Consequences

Whichever skill/workflow triggers the maintenance pass needs to know how to prefer a
stronger-model session when one is available, rather than always running under whatever model
happens to be active — this is a new coordination requirement `skills/lint.md` doesn't have today.
If Claude Code isn't available when maintenance is needed, the pass falls back to the local model,
which only partially closes the semantic-quality gap this ADR exists to address; revisit if that
turns out to happen often enough to matter.

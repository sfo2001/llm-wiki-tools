# Maintenance (and optionally ingest review) runs as an unattended, provider-agnostic job — not tiered to Claude Code

*Date: 2026-09-05*

ADR-0006's semantic-quality clause said the periodic maintenance pass should "run
preferentially under the strongest available model (today: Claude Code)." That's wrong: Claude
Code is billed against the same subscription as all interactive coding work, and maintenance is
meant to run **routinely** (a cron-style job, not something triggered inside a coding session) —
tiering it to Claude Code means the more the wiki gets used, the more it costs the thing it's
supposed to be independent of.

Decision: `lwt maintain` (and, if needed, an ingest-time review step) calls an LLM directly,
through a provider-agnostic client — the same shape as understory's `providers/index.ts`
(`LLM_API_BASE_URL` / `LLM_API_KEY` / `LLM_API_FORMAT` / `LLM_MODEL`, optional
`LLM_FALLBACK_*`). **Default target is the local model already running for ingest/authoring**
(Ollama, currently Qwen3-30B-A3B) reached directly via its API — zero marginal cost out of the
box. The endpoint is swappable later (a bigger local model, a cheap external API, or the
Anthropic API billed separately from the Code subscription) without an architecture change.

This is a narrower, corrected version of the same principle from ADR-0006's rejected option:
embedding an LLM caller *inside* `lwt` is right specifically where no interactive agent is
present to call it — an unattended job — not for interactive authoring, where a caller (local
model or Claude Code) already exists and already does this work for free (relative to the task
at hand). ADR-0002's split (CLI is content-agnostic during interactive use) is unaffected;
this only concerns the one operation that has no interactive caller by design.

**Ingest-time quality** is a separate, cheaper problem — don't reach for the same client
reflexively. Try sharpening `skills/ingest.md` so the model already authoring the page
self-reviews before writing (no new infrastructure, zero marginal cost, works today) before
building a second `lwt ingest --review` pass through the provider client. Escalate only if
self-review proves insufficient in practice.

## Considered Options

Tiering to Claude Code (ADR-0006's original clause) was rejected — see above. Running
maintenance only under whatever model happens to be interactively active was also rejected: it
makes "how good is my maintenance pass" depend on which session the user happens to be in when
they remember to run it, and doesn't support running it as an actual scheduled job at all, which
is the stated goal ("routine task").

## Consequences

`lwt` gains a real LLM-calling config surface (API key, base URL, model) for the first time —
previously nothing in the CLI held a credential. Needs documenting alongside the existing
`.lwt.env.example` pattern, with the same caution understory gives its own optional
`AUTH_TOKEN`. Both `lwt maintain` and any future `--review` step must degrade to
structural-lint-only when no provider is configured, so a user who never sets this up loses
nothing versus today. Default-to-local-model means maintenance quality is capped at whatever the
authoring model already does — a real limitation, not fully closing the semantic-quality gap
ADR-0006 raised — but it's strictly additive over no maintenance pass, and the ceiling is a
config change (point `LLM_MODEL` elsewhere), not a rebuild, if it proves insufficient.

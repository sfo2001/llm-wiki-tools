# LLM owns `wiki/`; the CLI only writes to `wiki/.tmp/`

*Date: 2026-04-15*

`lwt ingest` never writes to `wiki/` itself — only to `wiki/.tmp/`. All wiki-page creation and editing is done by the LLM agent, because the value of the wiki is the synthesis, cross-referencing, and editorial judgement the agent provides; a CLI that writes pages directly would compete with the agent and produce low-quality content.

## Considered Options

Auto-generating a stub page on ingest was rejected — stubs become dead pages nobody updates.

## Consequences

If the LLM ever becomes unreliable at page maintenance, we'll need human or CLI-assisted fallbacks. Revisit if the "wiki stays fresh" assumption breaks.

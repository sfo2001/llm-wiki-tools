# MkDocs Material replaces the local HTTP backend as the recommended deploy target

*Date: 2026-04-20*

`lwt deploy --target mkdocs` (MkDocs Material) is now the recommended deploy target, replacing `--target local`. The bare local HTTP server had no full-text search and rendered raw markdown, whereas MkDocs Material gives search, theming, code highlighting, and anchor navigation with zero configuration beyond `pip install llm-wiki-tools[mkdocs]`; `MkdocsBackend` auto-generates `mkdocs.yml` on first run and never overwrites a user-customised one.

**Considered Options:** keeping `LocalBackend` as the default and offering mkdocs as an extra was rejected — a bare-bones local server shouldn't be the recommended path.

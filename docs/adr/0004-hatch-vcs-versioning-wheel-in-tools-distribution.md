# Distribute `llm-wiki-tools` as a wheel vendored into each wiki's `tools/`, versioned via `hatch-vcs`

*Date: 2026-04-26*

`llm-wiki-tools` is distributed as a Python wheel whose version is derived from annotated git tags via `hatch-vcs` (no static `version =` in `pyproject.toml`). Each scaffolded wiki repo carries the wheel at `tools/llm_wiki_tools-X.Y.Z-py3-none-any.whl`; `run.sh`/`run.ps1` create a per-wiki `venv/` on first run and pip-install it, and `lwt update --tools <new.whl>` drops in a new wheel and prunes old ones. This replaces an "editable install on the developer's machine" model that left wikis silently depending on a path nobody else had — recipients with no PyPI, GitHub, or gitea access need nothing beyond `git clone` and Python 3.11+.

**Considered Options:** PyPI publish (rejected — personal tool, no audience there); `pip install git+ssh://gitea/...` (rejected — recipients may lack network access to the gitea); a git bundle (rejected — recipients don't need source history, and a wheel is smaller and standard); vendoring the `lwt` source into each wiki (rejected — no version discipline, multiplies maintenance).

## Consequences

Wheels accumulate in the wiki repo's git history (~30 KB per release × N releases). Mitigation: `--prune` removes the working-tree wheel; git history can be filter-repo'd later if it ever bites. `hatch-vcs` requires git history at build time, so a shallow clone can't build — fine, since recipients install the wheel and never build. Tag discipline is human-enforced; `release.sh` rejects untagged builds, so the only way to ship a `.dev` is to bypass `release.sh` deliberately.

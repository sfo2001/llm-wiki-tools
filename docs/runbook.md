---
project: llm-wiki-tools
last_updated: 2026-04-26
---

# llm-wiki-tools — Runbook

`llm-wiki-tools` v0.1.0 is implemented. The `lwt` CLI is usable today from `/path/to/llm-wiki-tools`.

## Install

```bash
# Development install (editable, with test deps):
cd /path/to/llm-wiki-tools
pip install -e ".[dev]"

# With MkDocs Material (recommended deploy target):
pip install -e ".[dev,mkdocs]"
# or after a release: pip install "llm-wiki-tools[mkdocs]"

# Verify:
lwt --help
```

## Start a new wiki

```bash
lwt init ~/devel/my-wiki --name "My Research Wiki"
cd ~/devel/my-wiki
git init && git add . && git commit -m "chore: lwt init"
```

Scaffold creates: `raw/`, `wiki/index.md`, `wiki/queries/`, `wiki/log.md`, `templates/`, `AGENTS.md`, `CLAUDE.md`, `.gitignore`, `.lwt.env.example`, `README.md`, `run.sh`, `run.ps1`, `skills/`.

Human entry point: `./run.sh help` or `./run.ps1 help`.

## Ingest a source

```bash
# Local file (PDF, DOCX, PPTX, markdown, text):
lwt ingest raw/paper.pdf --wiki-dir wiki

# Web URL:
lwt ingest https://example.com/article --wiki-dir wiki

# Preview without writing (stdout):
lwt ingest raw/paper.pdf --wiki-dir wiki --output -
```

Output lands in `wiki/.tmp/<date>_<filename>.md` with traceability frontmatter. The LLM then reads this and updates `wiki/` pages.

## Search the wiki

```bash
# BM25 keyword search (after LLM has populated wiki/):
lwt search "BM25 ranking" --wiki-dir wiki

# More results:
lwt search "neural network" --wiki-dir wiki --top 10
```

## Lint

```bash
# Structural lint — broken links, orphans, missing pages:
lwt lint --structural --wiki-dir wiki

# All lint modes:
lwt lint --wiki-dir wiki
```

Findings format: `wiki/page.md:12: broken link to 'concepts/foo.md'`. Zero findings = clean.

## Deploy

```bash
# MkDocs Material (recommended — auto-generates mkdocs.yml on first run):
lwt deploy --target mkdocs --wiki-dir wiki

# Build static site instead of serving:
lwt deploy --target mkdocs --wiki-dir wiki --build

# Custom port:
lwt deploy --target mkdocs --wiki-dir wiki --port 9000

# Fallback — plain HTTP server (no mkdocs needed):
lwt deploy --target local --wiki-dir wiki

# Docker (serves wiki/ via container):
lwt deploy --target docker --wiki-dir wiki --mode volume

# Confluence (dry-run by default):
lwt deploy --target confluence --wiki-dir wiki --no-dry-run
```

Confluence requires `.lwt.env` with `CONFLUENCE_URL`, `CONFLUENCE_TOKEN`, `CONFLUENCE_SPACE`.

## Check it's alive

```bash
# Tests (from llm-wiki-tools):
cd /path/to/llm-wiki-tools
pytest --tb=short -q

# Current test count: 102 passed

# CLI smoke test:
lwt --version
lwt lint --structural --wiki-dir wiki
```

## Common tasks

### Releasing a new lwt version

```bash
cd /path/to/llm-wiki-tools

# 1. Make changes, commit
git add ... && git commit -m "..."

# 2. Tag the release (annotated tag → release notes go in the message)
git tag -a v0.2.0 -m "Phase 0: wheel distribution + self-bootstrapping wikis"
git push origin main --tags

# 3. Build the wheel — fails on dirty tree or untagged HEAD
./release.sh
# → dist/llm_wiki_tools-0.2.0-py3-none-any.whl + matching sdist

# 4. Distribute to each in-use wiki
lwt update <wiki-path> --tools dist/llm_wiki_tools-0.2.0-py3-none-any.whl --apply
# In the wiki repo: git diff, then commit the new wheel + asset diffs
```

The version is derived from `git describe` via `hatch-vcs`. Untagged commits produce `.devN` versions that `release.sh` refuses to ship.

### First-run / fresh deployment of a wiki

A wiki repo with `tools/llm_wiki_tools-X.Y.Z-py3-none-any.whl` committed is fully self-bootstrapping — Python 3.11+ is the only host requirement.

```bash
# Recipient on a fresh machine:
git clone <wiki-repo-url> my-wiki
cd my-wiki
./run.sh serve
# → creates venv/, installs from tools/*.whl, serves the wiki at :8000
```

`run.sh` records the installed wheel filename in `venv/.installed-wheel`. Subsequent runs skip the pip step. Replacing the wheel (e.g. via `lwt update --tools <new.whl>` from another machine, then `git pull`) triggers a reinstall on the next `./run.sh` invocation.

### Refresh bundled assets in an existing wiki

When `llm-wiki-tools` ships changes to `AGENTS.md`, `skills/`, or the `run.sh` / `run.ps1` wrappers, pull them into a deployed wiki repo with:

```bash
cd <wiki-data-repo>
lwt update                    # dry-run — print per-file status table
lwt update --apply            # write canonical updates (AGENTS.md, skills/, run.sh, run.ps1)
lwt update --apply --force    # also overwrite CLAUDE.md, templates/, README.md, .gitignore
git diff                      # review
git commit -am "chore: refresh lwt bundled assets"
```

Two file classes:

- **canonical** — LLM-owned, expected to stay in sync with the bundle. Updated silently on `--apply`: `AGENTS.md`, `skills/{ingest,query,lint,deploy}.md`, `run.sh`, `run.ps1`.
- **customisable** — user-owned, may diverge. Diff is printed; not touched unless `--force`: `CLAUDE.md`, `README.md`, `templates/*`, `.gitignore`, `.lwt.env.example`.

The wiki name (substituted into `README.md`) is recovered from `# <Name> Wiki` on line 1 of the deployed README. Always commit the wiki repo before `lwt update --apply` so the change is reviewable.

### Update the design

Design artifacts live in `docs/` (moved from `~/devel/llm-wiki`):
- `docs/karpathy-llm-wiki.md` — Karpathy's original pattern (read-only reference)
- `docs/superpowers/specs/2026-04-15-llm-wiki-design.md` — system design
- `docs/superpowers/plans/` — four implementation plans (all complete as of 2026-04-25)

### Backup / restore

Both repos are under git. Regular `git push` is the backup. For the data repo:

```bash
git add wiki/ raw/ && git commit -m "chore: wiki update $(date +%F)"
```

## Things that have broken before

### 2026-04-19 — LocalBackend deploy() ignored wiki_dir parameter

Using `self.wiki_dir` instead of the passed `wiki_dir` argument in `deploy()`. Fixed in Plan 2. Root cause: copy-paste from init constructor without threading the parameter through.

### 2026-04-24 — MkdocsBackend _ensure_mkdocs_yml() was dead code

`deploy()` inlined the yml-generation logic rather than calling `_ensure_mkdocs_yml()`. Fixed by refactoring the helper to accept an optional `repo_dir` parameter and return the yml path.

### 2026-04-26 — template: frontmatter key conflicts with MkDocs

MkDocs reserves the `template:` frontmatter key as a pointer to a Jinja2 HTML template. Wiki pages using `template: entity.md` caused MkDocs to try to load `entity.md` as an HTML template → `TemplateNotFound`. Fixed by renaming to `lwt_template:` in all 5 template files and all existing wiki pages.

### 2026-04-26 — mkdocs serve not live-reloading on NFS

inotify events don't fire on NFS-mounted filesystems. Fixed by passing `WATCHDOG_USE_POLLING=1` as an env var to the mkdocs subprocess in `MkdocsBackend.deploy()`.

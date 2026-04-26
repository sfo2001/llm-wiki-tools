# lwt init Human-Friendly Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `lwt init` produce a self-contained, human-friendly wiki directory that a first-time recipient (no prior knowledge of lwt) can use immediately.

**Architecture:** Four additions to the scaffold bundled data in `src/llm_wiki/data/`: copy the four `skills/` files so CLAUDE.md `@path` references resolve; add a human-facing `README.md.template` (name substituted at init time); add `run.sh` / `run.ps1` wrapper scripts that hide the `--wiki-dir wiki` boilerplate. Update the bundled `AGENTS.md` to handle "user already ran lwt ingest" and document `claude` as the entry point. `init.py` copies all new files; existing `scaffold_data_repo` signature unchanged.

**Tech Stack:** Python 3.11+, pathlib, os.chmod, pytest

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `src/llm_wiki/data/skills/ingest.md` | Create | Bundled ingest skill — copy of root `skills/ingest.md` |
| `src/llm_wiki/data/skills/query.md` | Create | Bundled query skill |
| `src/llm_wiki/data/skills/lint.md` | Create | Bundled lint skill |
| `src/llm_wiki/data/skills/deploy.md` | Create | Bundled deploy skill |
| `src/llm_wiki/data/README.md.template` | Create | Human HOWTO with `__NAME__` sentinel for name substitution |
| `src/llm_wiki/data/run.sh` | Create | Unix wrapper — hides `--wiki-dir wiki` flag |
| `src/llm_wiki/data/run.ps1` | Create | Windows PowerShell wrapper |
| `src/llm_wiki/data/AGENTS.md` | Modify | Add "if already ingested" path; mention `claude` command; fix deploy to list mkdocs |
| `src/llm_wiki/init.py` | Modify | Copy skills/, README.md (substituted), run.sh/ps1; chmod run.sh |
| `tests/test_cli.py` | Modify | Add 5 tests for new scaffold files |

---

## Task 1: Bundle skills/ into scaffold

Skills files live in the repo root `skills/` directory but are not copied to the wiki by `lwt init`. CLAUDE.md has `@path skills/ingest.md` etc. which silently fail because `skills/` doesn't exist in the scaffolded wiki. This task copies the four skill files into `src/llm_wiki/data/skills/` so `init.py` can bundle them.

**Files:**
- Create: `src/llm_wiki/data/skills/ingest.md`
- Create: `src/llm_wiki/data/skills/query.md`
- Create: `src/llm_wiki/data/skills/lint.md`
- Create: `src/llm_wiki/data/skills/deploy.md`
- Modify: `src/llm_wiki/init.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests — append to `tests/test_cli.py`**

```python
# --- init scaffold: skills/ ---

def test_lwt_init_creates_skills_dir(tmp_path):
    CliRunner().invoke(main, ["init", str(tmp_path / "wiki")])
    assert (tmp_path / "wiki" / "skills").is_dir()


def test_lwt_init_skills_has_four_files(tmp_path):
    CliRunner().invoke(main, ["init", str(tmp_path / "wiki")])
    skills = tmp_path / "wiki" / "skills"
    for name in ["ingest.md", "query.md", "lint.md", "deploy.md"]:
        assert (skills / name).exists(), f"Missing skill: {name}"


def test_lwt_init_skills_ingest_not_empty(tmp_path):
    CliRunner().invoke(main, ["init", str(tmp_path / "wiki")])
    content = (tmp_path / "wiki" / "skills" / "ingest.md").read_text()
    assert "lwt ingest" in content
```

- [ ] **Step 2: Run to confirm fail**

```bash
cd /path/to/llm-wiki-tools
.venv/bin/pytest tests/test_cli.py -v -k "skills"
```

Expected: 3 FAILED — `skills/` directory doesn't exist yet in scaffold.

- [ ] **Step 3: Create `src/llm_wiki/data/skills/` with the four skill files**

Copy the content of each file from `skills/` at the repo root into `src/llm_wiki/data/skills/`:

```bash
mkdir -p src/llm_wiki/data/skills
cp skills/ingest.md src/llm_wiki/data/skills/ingest.md
cp skills/query.md  src/llm_wiki/data/skills/query.md
cp skills/lint.md   src/llm_wiki/data/skills/lint.md
cp skills/deploy.md src/llm_wiki/data/skills/deploy.md
```

(The root `skills/` directory is the developer-facing reference; `src/llm_wiki/data/skills/` is the packaged copy. Keep both — they may diverge as the wiki schema evolves.)

- [ ] **Step 4: Update `src/llm_wiki/init.py` to copy skills/**

Add the skills copy block after the schema files section. Full updated `scaffold_data_repo`:

```python
import os
import shutil
from pathlib import Path

_DATA_DIR = Path(__file__).parent / "data"


def scaffold_data_repo(target_dir: Path, name: str = "my-wiki") -> None:
    """Create the llm-wiki data repo directory structure at target_dir."""
    target_dir.mkdir(parents=True, exist_ok=True)

    # Directory structure
    for d in ["raw", "wiki/queries", "output"]:
        (target_dir / d).mkdir(parents=True, exist_ok=True)
        (target_dir / d / ".gitkeep").touch()

    # Stub wiki files
    (target_dir / "wiki" / "index.md").write_text(
        f"# {name} Wiki\n\n"
        "*Index — updated by LLM on every write.*\n\n"
        "## Pages\n\n*(empty — add pages as you ingest sources)*\n",
        encoding="utf-8",
    )
    (target_dir / "wiki" / "log.md").write_text(
        "# Operation Log\n\n"
        "*Append-only. Each entry: `## [YYYY-MM-DD] op | title`*\n",
        encoding="utf-8",
    )

    # Templates (copied from bundled data)
    templates_src = _DATA_DIR / "templates"
    templates_dst = target_dir / "templates"
    templates_dst.mkdir(exist_ok=True)
    for tmpl in [
        "default.md", "entity.md", "concept.md",
        "source-summary.md", "query-answer.md",
    ]:
        (templates_dst / tmpl).write_bytes((templates_src / tmpl).read_bytes())

    # Skills (bundled — satisfies CLAUDE.md @path references)
    skills_dst = target_dir / "skills"
    skills_dst.mkdir(exist_ok=True)
    for skill in ["ingest.md", "query.md", "lint.md", "deploy.md"]:
        (skills_dst / skill).write_bytes(
            (_DATA_DIR / "skills" / skill).read_bytes()
        )

    # Schema files
    (target_dir / "AGENTS.md").write_bytes((_DATA_DIR / "AGENTS.md").read_bytes())
    (target_dir / "CLAUDE.md").write_bytes((_DATA_DIR / "CLAUDE.md").read_bytes())

    # Config files
    gitignore = (_DATA_DIR / ".gitignore.template").read_text(encoding="utf-8")
    (target_dir / ".gitignore").write_text(gitignore, encoding="utf-8")
    (target_dir / ".lwt.env.example").write_bytes(
        (_DATA_DIR / ".lwt.env.example").read_bytes()
    )
```

- [ ] **Step 5: Run to confirm pass**

```bash
.venv/bin/pytest tests/test_cli.py -v -k "skills"
```

Expected: 3 PASSED.

- [ ] **Step 6: Run full suite — confirm no regressions**

```bash
.venv/bin/pytest --tb=short -q
```

Expected: 96 passed.

- [ ] **Step 7: Commit**

```bash
git add src/llm_wiki/data/skills/ src/llm_wiki/init.py tests/test_cli.py
git commit -m "feat: bundle skills/ into lwt init scaffold (fixes CLAUDE.md @path refs)"
```

---

## Task 2: Add README.md (human-facing HOWTO)

The scaffold has no guidance for a human receiving the wiki from a colleague. This task adds a `README.md` that explains: what this is, how to install lwt, the four-step workflow, and what each directory contains.

**Files:**
- Create: `src/llm_wiki/data/README.md.template`
- Modify: `src/llm_wiki/init.py` (add README copy with name substitution)
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests — append to `tests/test_cli.py`**

```python
# --- init scaffold: README.md ---

def test_lwt_init_creates_readme(tmp_path):
    CliRunner().invoke(main, ["init", str(tmp_path / "wiki"), "--name", "My Research"])
    assert (tmp_path / "wiki" / "README.md").exists()


def test_lwt_init_readme_contains_name(tmp_path):
    CliRunner().invoke(main, ["init", str(tmp_path / "wiki"), "--name", "My Research"])
    content = (tmp_path / "wiki" / "README.md").read_text()
    assert "My Research" in content


def test_lwt_init_readme_contains_run_sh(tmp_path):
    CliRunner().invoke(main, ["init", str(tmp_path / "wiki")])
    content = (tmp_path / "wiki" / "README.md").read_text()
    assert "run.sh" in content
```

- [ ] **Step 2: Run to confirm fail**

```bash
.venv/bin/pytest tests/test_cli.py -v -k "readme"
```

Expected: 3 FAILED — README.md not created yet.

- [ ] **Step 3: Create `src/llm_wiki/data/README.md.template`**

Create the file with `__NAME__` as the sentinel (avoids clashes with Python f-string `{}`):

```markdown
# __NAME__ Wiki

A personal knowledge base maintained by an AI assistant (Claude).
Sources live in `raw/`. The AI writes and maintains all wiki pages in `wiki/`.

---

## Quick start

### 1. Install lwt (one time)

**Linux / Mac:**
```bash
pip install "llm-wiki-tools[mkdocs]"
```

**Windows:**
```powershell
pip install "llm-wiki-tools[mkdocs]"
```

Verify: `lwt --version`

---

### 2. Drop a source into `raw/`

Supported: PDF, Word (.docx), PowerPoint (.pptx), plain text, Markdown, web URLs.

```
raw/
  my-paper.pdf
  meeting-notes.docx
  https-link.url      ← just paste the URL as the argument
```

---

### 3. Convert it

**Linux / Mac:**
```bash
./run.sh ingest raw/my-paper.pdf
```

**Windows:**
```powershell
.\run.ps1 ingest raw\my-paper.pdf
```

This converts the source to a readable markdown file in `wiki/.tmp/`.
It does **not** write any wiki pages — that's the AI's job.

---

### 4. Let the AI build the wiki pages

Open Claude Code in **this directory**:

```bash
claude
```

Then tell it what you just ingested, for example:

> "I ingested raw/my-paper.pdf — please process it."

Claude will read the converted file, discuss the key ideas with you, and write
wiki pages in `wiki/`.

---

### 5. Browse the wiki

**Linux / Mac:**
```bash
./run.sh serve
```

**Windows:**
```powershell
.\run.ps1 serve
```

Opens at **http://localhost:8000** — full-text search included.

To build a static site instead of serving live:
```bash
./run.sh build     # → .build/site/index.html
```

---

## Directory layout

| Path | Owner | What it is |
|------|-------|-----------|
| `raw/` | You | Original source files. Never edited. |
| `wiki/` | AI | The wiki. Don't edit by hand. |
| `wiki/.tmp/` | lwt | Converted sources waiting to be processed. |
| `templates/` | Shared | Page templates the AI uses when writing. |
| `skills/` | lwt | Workflow instructions loaded by Claude automatically. |
| `AGENTS.md` | lwt | AI schema — what the AI is and how it works. |
| `CLAUDE.md` | lwt | Claude Code configuration — loaded on `claude` startup. |
| `.lwt.env.example` | You | Copy to `.lwt.env` and fill in credentials (Confluence etc.). |

---

## Common operations

```bash
# Search the wiki
./run.sh search "transformer architecture"

# Check for broken links and orphaned pages
./run.sh lint

# Ingest a web page
./run.sh ingest https://example.com/article
```

---

## Sharing this wiki

Zip or git-push the whole directory. The recipient needs to install lwt
(step 1 above) — everything else is self-contained.
```

- [ ] **Step 4: Update `src/llm_wiki/init.py` — add README copy**

Add after the `.lwt.env.example` copy:

```python
    # Human-facing HOWTO
    readme_template = (_DATA_DIR / "README.md.template").read_text(encoding="utf-8")
    (target_dir / "README.md").write_text(
        readme_template.replace("__NAME__", name), encoding="utf-8"
    )
```

- [ ] **Step 5: Run to confirm pass**

```bash
.venv/bin/pytest tests/test_cli.py -v -k "readme"
```

Expected: 3 PASSED.

- [ ] **Step 6: Run full suite**

```bash
.venv/bin/pytest --tb=short -q
```

Expected: 99 passed.

- [ ] **Step 7: Commit**

```bash
git add src/llm_wiki/data/README.md.template src/llm_wiki/init.py tests/test_cli.py
git commit -m "feat: add README.md to lwt init scaffold (human-facing HOWTO)"
```

---

## Task 3: Add run.sh and run.ps1 wrapper scripts

The `--wiki-dir wiki` flag is required for every `lwt` command but is invisible to a first-time user. This task adds two wrapper scripts that default to `wiki` and expose only the user-facing verb.

**Files:**
- Create: `src/llm_wiki/data/run.sh`
- Create: `src/llm_wiki/data/run.ps1`
- Modify: `src/llm_wiki/init.py` (copy both; chmod +x for run.sh on Unix)
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests — append to `tests/test_cli.py`**

```python
import os

# --- init scaffold: run scripts ---

def test_lwt_init_creates_run_sh(tmp_path):
    CliRunner().invoke(main, ["init", str(tmp_path / "wiki")])
    assert (tmp_path / "wiki" / "run.sh").exists()


def test_lwt_init_run_sh_is_executable(tmp_path):
    CliRunner().invoke(main, ["init", str(tmp_path / "wiki")])
    assert os.access(tmp_path / "wiki" / "run.sh", os.X_OK)


def test_lwt_init_creates_run_ps1(tmp_path):
    CliRunner().invoke(main, ["init", str(tmp_path / "wiki")])
    assert (tmp_path / "wiki" / "run.ps1").exists()
```

- [ ] **Step 2: Run to confirm fail**

```bash
.venv/bin/pytest tests/test_cli.py -v -k "run_sh or run_ps1"
```

Expected: 3 FAILED.

- [ ] **Step 3: Create `src/llm_wiki/data/run.sh`**

```bash
#!/usr/bin/env bash
# run.sh — lwt wrapper for this wiki. Usage: ./run.sh <command> [args]
set -e

CMD=${1:-help}
shift 2>/dev/null || true

case "$CMD" in
  ingest)
    lwt ingest "$@" --wiki-dir wiki
    ;;
  serve)
    lwt deploy --target mkdocs --wiki-dir wiki "$@"
    ;;
  build)
    lwt deploy --target mkdocs --build --wiki-dir wiki "$@"
    ;;
  lint)
    lwt lint --structural --wiki-dir wiki
    ;;
  search)
    lwt search "$@" --wiki-dir wiki
    ;;
  help|--help|-h|*)
    echo "Usage: ./run.sh <command> [args]"
    echo ""
    echo "Commands:"
    echo "  ingest <file-or-url>   Convert source → wiki/.tmp/ then open claude"
    echo "  serve                  Serve wiki at http://localhost:8000 (live reload)"
    echo "  build                  Build static site → .build/site/"
    echo "  lint                   Check for broken links and orphaned pages"
    echo "  search <query>         BM25 keyword search over wiki pages"
    echo ""
    echo "Examples:"
    echo "  ./run.sh ingest raw/paper.pdf"
    echo "  ./run.sh ingest https://example.com/article"
    echo "  ./run.sh serve"
    echo "  ./run.sh search \"attention mechanism\""
    ;;
esac
```

- [ ] **Step 4: Create `src/llm_wiki/data/run.ps1`**

```powershell
# run.ps1 — lwt wrapper for this wiki. Usage: .\run.ps1 <command> [args]
param(
    [string]$Command = "help",
    [Parameter(ValueFromRemainingArguments=$true)]$Rest
)

switch ($Command) {
    "ingest" { lwt ingest @Rest --wiki-dir wiki }
    "serve"  { lwt deploy --target mkdocs --wiki-dir wiki @Rest }
    "build"  { lwt deploy --target mkdocs --build --wiki-dir wiki @Rest }
    "lint"   { lwt lint --structural --wiki-dir wiki }
    "search" { lwt search @Rest --wiki-dir wiki }
    default  {
        Write-Host "Usage: .\run.ps1 <command> [args]"
        Write-Host ""
        Write-Host "Commands:"
        Write-Host "  ingest <file-or-url>   Convert source -> wiki\.tmp\ then open claude"
        Write-Host "  serve                  Serve wiki at http://localhost:8000"
        Write-Host "  build                  Build static site -> .build\site\"
        Write-Host "  lint                   Check for broken links and orphaned pages"
        Write-Host "  search <query>         BM25 keyword search over wiki pages"
        Write-Host ""
        Write-Host "Examples:"
        Write-Host "  .\run.ps1 ingest raw\paper.pdf"
        Write-Host "  .\run.ps1 serve"
        Write-Host "  .\run.ps1 search 'attention mechanism'"
    }
}
```

- [ ] **Step 5: Update `src/llm_wiki/init.py` — copy run scripts**

Add after the README copy:

```python
    # Wrapper scripts
    (target_dir / "run.sh").write_bytes((_DATA_DIR / "run.sh").read_bytes())
    os.chmod(target_dir / "run.sh", 0o755)
    (target_dir / "run.ps1").write_bytes((_DATA_DIR / "run.ps1").read_bytes())
```

The `import os` must appear at the top of the file alongside `from pathlib import Path`.

Full updated imports section of `init.py`:

```python
import os
from pathlib import Path

_DATA_DIR = Path(__file__).parent / "data"
```

- [ ] **Step 6: Run to confirm pass**

```bash
.venv/bin/pytest tests/test_cli.py -v -k "run_sh or run_ps1"
```

Expected: 3 PASSED.

- [ ] **Step 7: Run full suite**

```bash
.venv/bin/pytest --tb=short -q
```

Expected: 102 passed.

- [ ] **Step 8: Commit**

```bash
git add src/llm_wiki/data/run.sh src/llm_wiki/data/run.ps1 src/llm_wiki/init.py tests/test_cli.py
git commit -m "feat: add run.sh / run.ps1 to lwt init scaffold"
```

---

## Task 4: Update bundled AGENTS.md

Two gaps in the current bundled `AGENTS.md`:

1. The **Ingest workflow** assumes Claude runs `lwt ingest` itself. In practice the human runs it and tells Claude "I ingested X" — Claude then has no clear instruction on what to do. Add an explicit "if already ingested" entry point.
2. The **Deploy workflow** references `local|docker|confluence` but not `mkdocs`, which is now the recommended target.

**Files:**
- Modify: `src/llm_wiki/data/AGENTS.md`

No new tests needed for this task — AGENTS.md is prose, not code. The existing `test_lwt_init_creates_structure` verifies the file exists.

- [ ] **Step 1: Read current `src/llm_wiki/data/AGENTS.md`**

Verify the Ingest and Deploy sections:
- Ingest step 1: `Run: lwt ingest <file-or-url>`
- Deploy step 2: `Run: lwt deploy --target <local|docker|confluence>`

- [ ] **Step 2: Replace the Ingest and Deploy sections**

In `src/llm_wiki/data/AGENTS.md`, replace the `### Ingest` section:

**Old:**
```markdown
### Ingest

1. Run: `lwt ingest <file-or-url>`
2. Read the summary line (path, lines, sections, backend)
3. Small doc (< 200 lines): read full temp file
4. Large doc: read in chunks (offset/limit) or dispatch sub-agent per section
5. Discuss key takeaways with user before writing anything
6. Select template: source-summary.md for ingested sources
7. Write/update wiki pages — copy traceability frontmatter from temp file header
8. One source typically touches 5–15 wiki pages (summary + entity/concept updates)
9. Update wiki/index.md, append to wiki/log.md:
   `## [YYYY-MM-DD] ingest | <source title>`
```

**New:**
```markdown
### Ingest

The human typically runs `lwt ingest` themselves, then opens Claude and says
"I ingested raw/file.pdf" or "process the file I just ingested". Either path
leads to the same workflow:

1. If `lwt ingest` not yet run: `lwt ingest <file-or-url> --wiki-dir wiki`
2. Read the summary output (path, lines, sections, backend)
3. **Small doc (< 200 lines):** read full temp file in one pass
4. **Large doc (200–500 lines):** read in chunks using offset/limit
5. **Very large doc (> 500 lines):** dispatch sub-agents per section, synthesize
6. Discuss key takeaways with user before writing anything
7. Select template: source-summary.md for ingested sources
8. Write/update wiki pages — copy traceability frontmatter from temp file header
9. Typical scope: 1 source-summary + 3–10 entity/concept page updates
10. Update wiki/index.md, append to wiki/log.md:
    `## [YYYY-MM-DD] ingest | <source title>`
```

Replace the `### Deploy` section:

**Old:**
```markdown
### Deploy

1. Confirm target with user before running
2. Run: `lwt deploy --target <local|docker|confluence> [options]`
3. Confluence is stub — dry-run only unless user confirms --no-dry-run
```

**New:**
```markdown
### Deploy

1. Confirm target with user before running
2. Run the appropriate command:
   - `lwt deploy --target mkdocs --wiki-dir wiki` — MkDocs Material site (recommended, requires `pip install "llm-wiki-tools[mkdocs]"`)
   - `lwt deploy --target mkdocs --wiki-dir wiki --build` — build static site to `.build/site/`
   - `lwt deploy --target local --wiki-dir wiki` — plain HTTP fallback
   - `lwt deploy --target docker --wiki-dir wiki --mode volume`
3. Confluence is a stub — dry-run only unless user confirms `--no-dry-run`
```

- [ ] **Step 3: Run full suite to confirm nothing broken**

```bash
.venv/bin/pytest --tb=short -q
```

Expected: 102 passed (no change — no new tests for prose changes).

- [ ] **Step 4: Commit**

```bash
git add src/llm_wiki/data/AGENTS.md
git commit -m "docs: update bundled AGENTS.md — ingest handles 'already ingested'; deploy lists mkdocs"
```

---

## Self-Review

**1. Spec coverage:**

| Requirement | Task |
|-------------|------|
| skills/ bundled so @path refs resolve | Task 1 |
| README.md for human recipients | Task 2 |
| run.sh / run.ps1 wrapper scripts | Task 3 |
| AGENTS.md handles "already ingested" | Task 4 |
| AGENTS.md deploy lists mkdocs | Task 4 |
| run.sh is executable (+x) | Task 3, Step 5 |
| README contains wiki name | Task 2 |
| self-contained (no external knowledge needed) | Tasks 1–3 combined |

All requirements covered.

**2. Placeholder scan:** None found. All code blocks are complete.

**3. Type consistency:**
- `_DATA_DIR` used consistently across all tasks — defined once, referenced in copy operations.
- `scaffold_data_repo(target_dir, name)` signature unchanged throughout — Tasks 1–3 all use `target_dir / "..."`.
- `os.chmod` added in Task 3 requires `import os` at top of init.py — Task 3 Step 5 shows the full imports section.

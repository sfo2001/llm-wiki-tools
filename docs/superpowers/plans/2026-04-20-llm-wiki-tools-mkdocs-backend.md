# MkDocs Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `MkdocsBackend` deploy target that generates a `mkdocs.yml` beside `wiki/` and runs `mkdocs serve` or `mkdocs build`, replacing `LocalBackend` as the recommended human-facing viewer.

**Architecture:** `MkdocsBackend` sits in `src/llm_wiki/deploy/mkdocs_backend.py` alongside the existing backends. On `deploy()`, it lazily generates a `mkdocs.yml` at `wiki/../mkdocs.yml` (the data-repo root) if one doesn't already exist, then runs `mkdocs serve` (default) or `mkdocs build` via subprocess. `write_page` / `delete_page` write directly to `wiki/` — MkDocs treats `wiki/` as its `docs_dir`, so the files are live immediately. The CLI gains `--target mkdocs` and a `--build` flag.

**Tech Stack:** Python 3.11+, click, subprocess, `mkdocs-material>=9.5` (optional dep, must be installed by user), pytest, unittest.mock

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `src/llm_wiki/deploy/mkdocs_backend.py` | Create | `MkdocsBackend` class |
| `tests/deploy/test_mkdocs_backend.py` | Create | 9 tests for `MkdocsBackend` |
| `src/llm_wiki/cli.py` | Modify (lines 86–128) | Add `mkdocs` choice + `--build` flag |
| `tests/test_cli.py` | Modify (append) | 3 deploy tests for mkdocs target |
| `pyproject.toml` | Modify (lines 22–28) | Add `mkdocs` optional-dep group |
| `skills/deploy.md` | Modify | Document mkdocs target |

---

## Task 1: `MkdocsBackend` + optional dep

**Files:**
- Create: `src/llm_wiki/deploy/mkdocs_backend.py`
- Create: `tests/deploy/test_mkdocs_backend.py`
- Modify: `pyproject.toml`

### Background for the implementer

The existing backends (`LocalBackend`, `DockerBackend`, `ConfluenceBackend`) all live in `src/llm_wiki/deploy/` and inherit from `WikiBackend` in `src/llm_wiki/deploy/base.py`:

```python
class WikiBackend(ABC):
    @property
    @abstractmethod
    def target_name(self) -> str: ...
    @abstractmethod
    def write_page(self, rel_path: str, content: str) -> None: ...
    @abstractmethod
    def delete_page(self, rel_path: str) -> None: ...
    @abstractmethod
    def deploy(self, wiki_dir: Path) -> None: ...
```

A data repo created by `lwt init` has this layout:

```
<data-repo>/          ← wiki_dir.parent  (MkdocsBackend._repo_dir)
  wiki/               ← wiki_dir  (MkdocsBackend.wiki_dir)
    index.md
    concepts/foo.md
    ...
  raw/
  templates/
  AGENTS.md
```

`MkdocsBackend._ensure_mkdocs_yml()` writes `<data-repo>/mkdocs.yml` pointing `docs_dir: wiki`. MkDocs runs with `cwd=_repo_dir` so it resolves `wiki/` as a relative path correctly. Directories starting with `.` (`wiki/.tmp/`, `wiki/.lwt_cache/`) are excluded by MkDocs automatically.

- [ ] **Step 1: Write failing tests — create `tests/deploy/test_mkdocs_backend.py`**

```python
import pytest
from pathlib import Path
from unittest.mock import patch
from llm_wiki.deploy.mkdocs_backend import MkdocsBackend


def test_mkdocs_target_name(tmp_path):
    b = MkdocsBackend(tmp_path / "wiki")
    assert b.target_name == "mkdocs"


def test_mkdocs_write_page_creates_file(tmp_path):
    b = MkdocsBackend(tmp_path / "wiki")
    b.write_page("concepts/foo.md", "# Foo\n\nContent.")
    assert (tmp_path / "wiki" / "concepts" / "foo.md").exists()
    assert "# Foo" in (tmp_path / "wiki" / "concepts" / "foo.md").read_text()


def test_mkdocs_write_page_creates_parents(tmp_path):
    b = MkdocsBackend(tmp_path / "wiki")
    b.write_page("a/b/c/page.md", "# Page")
    assert (tmp_path / "wiki" / "a" / "b" / "c" / "page.md").exists()


def test_mkdocs_delete_page_removes_file(tmp_path):
    b = MkdocsBackend(tmp_path / "wiki")
    b.write_page("page.md", "# Page")
    b.delete_page("page.md")
    assert not (tmp_path / "wiki" / "page.md").exists()


def test_mkdocs_delete_page_noop_if_missing(tmp_path):
    b = MkdocsBackend(tmp_path / "wiki")
    b.delete_page("nonexistent.md")  # must not raise


def test_mkdocs_ensure_creates_yml_if_absent(tmp_path):
    b = MkdocsBackend(tmp_path / "wiki", name="My Research")
    b._ensure_mkdocs_yml()
    yml_path = tmp_path / "mkdocs.yml"
    assert yml_path.exists()
    content = yml_path.read_text()
    assert "My Research" in content
    assert "material" in content
    assert "docs_dir: wiki" in content


def test_mkdocs_ensure_skips_if_yml_exists(tmp_path):
    existing = tmp_path / "mkdocs.yml"
    existing.write_text("site_name: Custom\n")
    b = MkdocsBackend(tmp_path / "wiki")
    b._ensure_mkdocs_yml()
    assert "Custom" in existing.read_text()  # must not overwrite


def test_mkdocs_deploy_serve_calls_mkdocs_serve(tmp_path):
    b = MkdocsBackend(tmp_path / "wiki", port=9000, build=False)
    with patch("llm_wiki.deploy.mkdocs_backend.subprocess.run") as mock_run:
        b.deploy(tmp_path / "wiki")
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert "mkdocs" in cmd and "serve" in cmd
    assert "9000" in " ".join(str(a) for a in cmd)


def test_mkdocs_deploy_build_calls_mkdocs_build(tmp_path):
    b = MkdocsBackend(tmp_path / "wiki", build=True)
    with patch("llm_wiki.deploy.mkdocs_backend.subprocess.run") as mock_run:
        b.deploy(tmp_path / "wiki")
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert "mkdocs" in cmd and "build" in cmd
```

- [ ] **Step 2: Run — verify fail**

```bash
cd /path/to/llm-wiki-tools
.venv/bin/pytest tests/deploy/test_mkdocs_backend.py -v
```

Expected: `ImportError: cannot import name 'MkdocsBackend'`

- [ ] **Step 3: Implement `src/llm_wiki/deploy/mkdocs_backend.py`**

```python
import subprocess
from pathlib import Path

from llm_wiki.deploy.base import WikiBackend

_MKDOCS_YML_TEMPLATE = """\
site_name: "{name}"
docs_dir: wiki
site_dir: .build/site
theme:
  name: material
  features:
    - navigation.instant
    - navigation.top
    - search.highlight
    - search.suggest
markdown_extensions:
  - toc:
      permalink: true
  - pymdownx.highlight:
      anchor_linenums: true
  - pymdownx.superfences
plugins:
  - search
"""


class MkdocsBackend(WikiBackend):
    """Build/serve wiki/ as a MkDocs Material site.

    write_page() and delete_page() write directly to wiki_dir.
    deploy() generates mkdocs.yml beside wiki/ (if absent), then
    runs 'mkdocs serve' (default) or 'mkdocs build' (when build=True).
    """

    def __init__(
        self,
        wiki_dir: Path,
        port: int = 8000,
        name: str = "Wiki",
        build: bool = False,
    ) -> None:
        self.wiki_dir = wiki_dir
        self.port = port
        self.name = name
        self.build = build

    @property
    def target_name(self) -> str:
        return "mkdocs"

    def write_page(self, rel_path: str, content: str) -> None:
        path = self.wiki_dir / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def delete_page(self, rel_path: str) -> None:
        path = self.wiki_dir / rel_path
        if path.exists():
            path.unlink()

    @property
    def _repo_dir(self) -> Path:
        """Parent of wiki_dir — the data-repo root where mkdocs.yml lives."""
        return self.wiki_dir.parent

    @property
    def _mkdocs_yml(self) -> Path:
        return self._repo_dir / "mkdocs.yml"

    def _ensure_mkdocs_yml(self) -> None:
        """Write mkdocs.yml beside wiki/ if one does not already exist."""
        if self._mkdocs_yml.exists():
            return
        self._repo_dir.mkdir(parents=True, exist_ok=True)
        self._mkdocs_yml.write_text(
            _MKDOCS_YML_TEMPLATE.format(name=self.name), encoding="utf-8"
        )

    def deploy(self, wiki_dir: Path) -> None:
        self._ensure_mkdocs_yml()
        if self.build:
            cmd = [
                "mkdocs", "build",
                "--config-file", str(self._mkdocs_yml),
                "--clean",
            ]
        else:
            cmd = [
                "mkdocs", "serve",
                "--config-file", str(self._mkdocs_yml),
                "--dev-addr", f"0.0.0.0:{self.port}",
            ]
        print(f"{'Building' if self.build else 'Serving'}: {' '.join(cmd)}")
        subprocess.run(cmd, check=True, cwd=str(self._repo_dir))
```

- [ ] **Step 4: Run — verify pass**

```bash
.venv/bin/pytest tests/deploy/test_mkdocs_backend.py -v
```

Expected: 9 PASSED.

- [ ] **Step 5: Add `mkdocs` optional-dep group to `pyproject.toml`**

In `pyproject.toml`, update `[project.optional-dependencies]` to add a `mkdocs` group:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "fpdf2>=2.7",
    "responses>=0.25",
]
mkdocs = [
    "mkdocs-material>=9.5",
]
```

- [ ] **Step 6: Commit**

```bash
git add src/llm_wiki/deploy/mkdocs_backend.py tests/deploy/test_mkdocs_backend.py pyproject.toml
git commit -m "feat: add MkdocsBackend (serve/build wiki/ via mkdocs-material)"
```

---

## Task 2: CLI + skills update

**Files:**
- Modify: `src/llm_wiki/cli.py` (lines 84–128)
- Modify: `tests/test_cli.py` (append at end of file)
- Modify: `skills/deploy.md`

### Background for the implementer

Current `deploy` command at `cli.py:84`. The `--target` choice list is on line 87:
```python
type=click.Choice(["local", "docker", "confluence"]),
```

The routing block is lines 108–128. Add `mkdocs` alongside the others.

Two changes needed:
1. Add `"mkdocs"` to the `click.Choice` list.
2. Add `--build` flag (mkdocs-only, ignored for other targets).
3. Add the `elif target == "mkdocs":` branch in the routing block.
4. Auto-derive site name from the wiki-dir parent directory name when no explicit name is available: `wiki_path.parent.name.replace("-", " ").title()`.

- [ ] **Step 1: Write failing tests — append to `tests/test_cli.py`**

Add at the very bottom of the existing `tests/test_cli.py`:

```python
# --- mkdocs deploy tests ---

def test_lwt_deploy_mkdocs_in_help():
    result = CliRunner().invoke(main, ["deploy", "--help"])
    assert result.exit_code == 0
    assert "mkdocs" in result.output


def test_lwt_deploy_mkdocs_serve(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "index.md").write_text("# Index")
    with mock_patch("llm_wiki.deploy.mkdocs_backend.subprocess.run"):
        result = CliRunner().invoke(main, [
            "deploy", "--target", "mkdocs",
            "--wiki-dir", str(wiki_dir),
        ])
    assert result.exit_code == 0


def test_lwt_deploy_mkdocs_build(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "index.md").write_text("# Index")
    with mock_patch("llm_wiki.deploy.mkdocs_backend.subprocess.run") as mock_run:
        result = CliRunner().invoke(main, [
            "deploy", "--target", "mkdocs",
            "--wiki-dir", str(wiki_dir),
            "--build",
        ])
    assert result.exit_code == 0
    cmd = mock_run.call_args[0][0]
    assert "build" in cmd
```

Note: `mock_patch` is already imported at the top of `tests/test_cli.py` as `from unittest.mock import patch as mock_patch`.

- [ ] **Step 2: Run — verify fail**

```bash
.venv/bin/pytest tests/test_cli.py -v -k "mkdocs"
```

Expected: errors — `mkdocs` is not a valid choice for `--target` yet.

- [ ] **Step 3: Update `src/llm_wiki/cli.py`**

Replace the entire `deploy` command (lines 84–128) with:

```python
@main.command()
@click.option(
    "--target", required=True,
    type=click.Choice(["local", "docker", "confluence", "mkdocs"]),
    help="Deployment target.",
)
@click.option("--wiki-dir", default="wiki", show_default=True)
@click.option("--port", default=None, type=int,
              help="Port override (default: 8080 local, 8443 docker, 8000 mkdocs).")
@click.option(
    "--mode", default="volume",
    type=click.Choice(["volume", "image"]), show_default=True,
    help="Docker mode: volume (live updates) or image (baked snapshot).",
)
@click.option(
    "--dry-run/--no-dry-run", default=True, show_default=True,
    help="Confluence: print diff without pushing (default: dry-run).",
)
@click.option(
    "--build", is_flag=True, default=False,
    help="MkDocs: build static site instead of serving (default: serve).",
)
def deploy(
    target: str, wiki_dir: str, port: int | None, mode: str, dry_run: bool, build: bool
) -> None:
    """Deploy wiki/ to a target (local HTTP, Docker, Confluence, or MkDocs Material)."""
    import os
    wiki_path = Path(wiki_dir)
    if target == "local":
        from llm_wiki.deploy.local import LocalBackend
        backend = LocalBackend(wiki_path, port=port or 8080)
    elif target == "docker":
        from llm_wiki.deploy.docker import DockerBackend
        backend = DockerBackend(wiki_path, port=port or 8443, mode=mode)
    elif target == "mkdocs":
        from llm_wiki.deploy.mkdocs_backend import MkdocsBackend
        name = wiki_path.parent.name.replace("-", " ").title()
        backend = MkdocsBackend(wiki_path, port=port or 8000, name=name, build=build)
    else:  # confluence
        from llm_wiki.deploy.confluence import ConfluenceBackend
        url = os.environ.get("CONFLUENCE_URL", "")
        token = os.environ.get("CONFLUENCE_TOKEN", "")
        space = os.environ.get("CONFLUENCE_SPACE", "")
        if not dry_run and not all([url, token, space]):
            missing = [k for k, v in [
                ("CONFLUENCE_URL", url), ("CONFLUENCE_TOKEN", token), ("CONFLUENCE_SPACE", space)
            ] if not v]
            raise click.UsageError(
                f"Missing required env vars for live Confluence deploy: {', '.join(missing)}\n"
                "Set them in .lwt.env or export them, or use --dry-run."
            )
        backend = ConfluenceBackend(url=url, token=token, space=space, dry_run=dry_run)
    backend.deploy(wiki_path)
```

- [ ] **Step 4: Run — verify pass**

```bash
.venv/bin/pytest tests/test_cli.py -v -k "mkdocs"
```

Expected: 3 PASSED.

- [ ] **Step 5: Run full suite — verify no regressions**

```bash
.venv/bin/pytest --tb=short -q
```

Expected: 92 passed (80 existing + 9 mkdocs_backend + 3 cli mkdocs).

- [ ] **Step 6: Update `skills/deploy.md`**

Replace the entire content of `skills/deploy.md` with:

```markdown
# Deploy Workflow Skill

## When to use

When the user asks you to deploy or serve the wiki externally.

## Always confirm before deploying

Ask the user which target and confirm before running. For Confluence, always
confirm `--no-dry-run` explicitly — the default is dry-run.

## Target reference

### MkDocs Material (recommended for personal use)

```bash
# Serve (blocking — runs until Ctrl-C):
lwt deploy --target mkdocs --wiki-dir wiki [--port 8000]

# Build static site:
lwt deploy --target mkdocs --wiki-dir wiki --build
```

Auto-generates `mkdocs.yml` beside `wiki/` on first run (skips if already present).
The site name is derived from the data-repo directory name. To customise, edit `mkdocs.yml` directly.
Requires `mkdocs-material` installed: `pip install "llm-wiki-tools[mkdocs]"`.

### Local HTTP server (fallback, no install required)

```bash
lwt deploy --target local --wiki-dir wiki [--port 8080]
```

Detects mkdocs → grip → stdlib http.server (priority order). Blocking — runs until Ctrl-C.
Serves raw markdown — no search, no rendered navigation.

### Docker

```bash
# Volume mode (live updates — wiki/ on disk):
lwt deploy --target docker --wiki-dir wiki --mode volume [--port 8443]

# Image mode (baked snapshot — requires Dockerfile in wiki/):
lwt deploy --target docker --wiki-dir wiki --mode image [--port 8443]
```

### Confluence Data Centre

```bash
# Dry-run (safe — default):
lwt deploy --target confluence --wiki-dir wiki

# Live push (requires user confirmation):
lwt deploy --target confluence --wiki-dir wiki --no-dry-run
```

Requires in `.lwt.env`: `CONFLUENCE_URL`, `CONFLUENCE_TOKEN`, `CONFLUENCE_SPACE`.

**Confluence is a stub.** Full markdown-to-storage-format conversion not yet implemented.

## Traceability check before deploy

Run `lwt lint --structural --wiki-dir wiki` and fix all findings before deploying.
```

- [ ] **Step 7: Commit**

```bash
git add src/llm_wiki/cli.py tests/test_cli.py skills/deploy.md
git commit -m "feat: add --target mkdocs to lwt deploy (serve/build via mkdocs-material)"
```

---

## Self-Review Checklist

- [ ] `lwt deploy --target mkdocs --wiki-dir wiki` generates `mkdocs.yml` beside `wiki/` and calls `mkdocs serve`
- [ ] `lwt deploy --target mkdocs --wiki-dir wiki --build` calls `mkdocs build`
- [ ] Existing mkdocs.yml is never overwritten
- [ ] Site name auto-derived from `wiki_path.parent.name` (e.g. `my-research` → `My Research`)
- [ ] All 92 tests pass
- [ ] `mkdocs-material>=9.5` appears in `[project.optional-dependencies.mkdocs]`
- [ ] `skills/deploy.md` lists mkdocs as the recommended target

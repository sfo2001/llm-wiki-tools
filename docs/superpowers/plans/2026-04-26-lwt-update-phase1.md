# lwt update — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `lwt update` so users can pull bundled-asset improvements (`AGENTS.md`, `skills/*`, `run.sh`, `run.ps1`) into existing data repos without losing their customised files (`CLAUDE.md`, `README.md`, `templates/*`, `.gitignore`).

**Architecture:** New `src/llm_wiki/update.py` module. Hardcoded two-class file taxonomy: **canonical** (silent overwrite on `--apply`) and **customisable** (left alone unless `--force`, with diff printed). No state files, no manifest — Phase 1 is comparison-based only. New `lwt update [PATH] [--apply] [--force]` CLI command. Default mode is dry-run that prints a status table.

**Tech Stack:** Python 3.11+, pathlib, hashlib, difflib, click, pytest, click.testing.CliRunner.

**Out of scope (later phases):**
- `.lwt-manifest.yaml` for "user-modified vs bundle-drift" disambiguation → Phase 2
- Three-way merge for customisable files → Phase 3
- Content migrations (e.g. frontmatter key renames) → Phase 4
- `lwt doctor` / deploy awareness → Phase 5

---

## File classification (Phase 1)

| Class | Files | Behaviour on `lwt update --apply` |
|---|---|---|
| **canonical** | `AGENTS.md`, `skills/ingest.md`, `skills/query.md`, `skills/lint.md`, `skills/deploy.md`, `run.sh`, `run.ps1` | Overwrite silently if bundle differs |
| **customisable** | `CLAUDE.md`, `README.md`, `templates/default.md`, `templates/entity.md`, `templates/concept.md`, `templates/source-summary.md`, `templates/query-answer.md`, `.gitignore`, `.lwt.env.example` | Print diff; do not touch unless `--force` |
| **ignored** | `wiki/**`, `raw/**`, `output/**`, `.lwt.env`, `.lwt-manifest.yaml`, anything else | Never inspected |

`run.sh` mode bit re-applied (`0o755`) after overwrite, mirroring `lwt init`.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `src/llm_wiki/update.py` | Create | Bundle-comparison logic, canonical/customisable taxonomy, apply/force semantics |
| `src/llm_wiki/cli.py` | Modify | Wire up `lwt update` subcommand |
| `tests/test_update.py` | Create | Unit + integration tests |
| `docs/runbook.md` | Modify | Document `lwt update` workflow |
| `src/llm_wiki/data/AGENTS.md` | Modify | Mention `lwt update` for keeping the wiki current |

---

## Task 1: `update.py` core — file taxonomy and status comparison

Implement the pure logic with no side effects: given a `target_dir`, return a list of `FileStatus` dicts describing each bundled file.

**Files:**
- Create: `src/llm_wiki/update.py`
- Create: `tests/test_update.py`

- [ ] **Step 1: Write failing tests — `tests/test_update.py`**

```python
from pathlib import Path
import pytest
from click.testing import CliRunner
from llm_wiki.cli import main
from llm_wiki.update import (
    CANONICAL_FILES,
    CUSTOMISABLE_FILES,
    FileStatus,
    compute_status,
)


def _scaffold(tmp_path: Path) -> Path:
    target = tmp_path / "wiki-repo"
    CliRunner().invoke(main, ["init", str(target), "--name", "Test"])
    return target


def test_taxonomy_disjoint():
    assert set(CANONICAL_FILES).isdisjoint(set(CUSTOMISABLE_FILES))


def test_taxonomy_covers_every_bundled_file():
    from llm_wiki.update import _BUNDLED_FILES
    assert set(_BUNDLED_FILES) == set(CANONICAL_FILES) | set(CUSTOMISABLE_FILES)


def test_compute_status_fresh_scaffold_all_identical(tmp_path):
    target = _scaffold(tmp_path)
    statuses = compute_status(target)
    for s in statuses:
        assert s.state == "identical", f"{s.rel_path}: {s.state}"


def test_compute_status_detects_canonical_drift(tmp_path):
    target = _scaffold(tmp_path)
    (target / "AGENTS.md").write_text("user butchered this\n")
    statuses = {s.rel_path: s for s in compute_status(target)}
    assert statuses["AGENTS.md"].state == "differs"
    assert statuses["AGENTS.md"].class_ == "canonical"


def test_compute_status_detects_customisable_drift(tmp_path):
    target = _scaffold(tmp_path)
    (target / "CLAUDE.md").write_text("# my custom instructions\n")
    statuses = {s.rel_path: s for s in compute_status(target)}
    assert statuses["CLAUDE.md"].state == "differs"
    assert statuses["CLAUDE.md"].class_ == "customisable"


def test_compute_status_handles_missing_file(tmp_path):
    target = _scaffold(tmp_path)
    (target / "run.sh").unlink()
    statuses = {s.rel_path: s for s in compute_status(target)}
    assert statuses["run.sh"].state == "missing"
```

- [ ] **Step 2: Run to confirm fail**

```bash
.venv/bin/pytest tests/test_update.py -v
```

Expected: all FAIL — module doesn't exist yet.

- [ ] **Step 3: Implement `src/llm_wiki/update.py`**

```python
"""lwt update — refresh bundled assets in an existing wiki data repo.

Phase 1: hardcoded file taxonomy (canonical vs customisable), no manifest.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

_DATA_DIR = Path(__file__).parent / "data"

CANONICAL_FILES: tuple[str, ...] = (
    "AGENTS.md",
    "skills/ingest.md",
    "skills/query.md",
    "skills/lint.md",
    "skills/deploy.md",
    "run.sh",
    "run.ps1",
)

CUSTOMISABLE_FILES: tuple[str, ...] = (
    "CLAUDE.md",
    "README.md",
    "templates/default.md",
    "templates/entity.md",
    "templates/concept.md",
    "templates/source-summary.md",
    "templates/query-answer.md",
    ".gitignore",
    ".lwt.env.example",
)

_BUNDLED_FILES: tuple[str, ...] = CANONICAL_FILES + CUSTOMISABLE_FILES

# Files whose bundled name differs from the deployed name.
_BUNDLE_NAME_OVERRIDES: dict[str, str] = {
    ".gitignore": ".gitignore.template",
    "README.md": "README.md.template",
}


def _bundle_path(rel: str) -> Path:
    return _DATA_DIR / _BUNDLE_NAME_OVERRIDES.get(rel, rel)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class FileStatus:
    rel_path: str
    class_: Literal["canonical", "customisable"]
    state: Literal["identical", "differs", "missing"]
    bundle_bytes: bytes  # current bundled content (for apply step)
    deployed_bytes: bytes | None  # None if missing


def _classify(rel: str) -> Literal["canonical", "customisable"]:
    return "canonical" if rel in CANONICAL_FILES else "customisable"


def _read_bundle(rel: str, name: str = "my-wiki") -> bytes:
    """Read bundled file, applying README/__NAME__ substitution if applicable."""
    raw = _bundle_path(rel).read_bytes()
    if rel == "README.md":
        return raw.replace(b"__NAME__", name.encode())
    return raw


def compute_status(target_dir: Path, name: str = "my-wiki") -> list[FileStatus]:
    """Inspect every bundled file under target_dir; return per-file status."""
    statuses: list[FileStatus] = []
    for rel in _BUNDLED_FILES:
        bundle_bytes = _read_bundle(rel, name=name)
        dep_path = target_dir / rel
        if not dep_path.exists():
            statuses.append(FileStatus(
                rel_path=rel, class_=_classify(rel),
                state="missing", bundle_bytes=bundle_bytes,
                deployed_bytes=None,
            ))
            continue
        deployed_bytes = dep_path.read_bytes()
        state = "identical" if _sha(deployed_bytes) == _sha(bundle_bytes) else "differs"
        statuses.append(FileStatus(
            rel_path=rel, class_=_classify(rel),
            state=state, bundle_bytes=bundle_bytes,
            deployed_bytes=deployed_bytes,
        ))
    return statuses
```

- [ ] **Step 4: Re-run tests, expect green**

```bash
.venv/bin/pytest tests/test_update.py -v
```

All 6 tests should pass.

---

## Task 2: Apply logic — `apply_update()`

Given the statuses, write changes to disk respecting class + flags.

**Files:**
- Modify: `src/llm_wiki/update.py`
- Modify: `tests/test_update.py`

- [ ] **Step 1: Append failing tests to `tests/test_update.py`**

```python
from llm_wiki.update import apply_update


def test_apply_updates_canonical_silently(tmp_path):
    target = _scaffold(tmp_path)
    (target / "AGENTS.md").write_text("stale\n")
    written = apply_update(target, force=False)
    assert "AGENTS.md" in [w.rel_path for w in written]
    # Now matches bundle:
    assert (target / "AGENTS.md").read_bytes() == \
        (Path(__file__).parent.parent / "src/llm_wiki/data/AGENTS.md").read_bytes()


def test_apply_skips_customisable_without_force(tmp_path):
    target = _scaffold(tmp_path)
    (target / "CLAUDE.md").write_text("custom\n")
    written = apply_update(target, force=False)
    assert "CLAUDE.md" not in [w.rel_path for w in written]
    assert (target / "CLAUDE.md").read_text() == "custom\n"


def test_apply_overwrites_customisable_with_force(tmp_path):
    target = _scaffold(tmp_path)
    (target / "CLAUDE.md").write_text("custom\n")
    written = apply_update(target, force=True)
    assert "CLAUDE.md" in [w.rel_path for w in written]
    assert (target / "CLAUDE.md").read_bytes() != b"custom\n"


def test_apply_restores_missing_canonical_file(tmp_path):
    target = _scaffold(tmp_path)
    (target / "run.sh").unlink()
    apply_update(target, force=False)
    assert (target / "run.sh").exists()


def test_apply_chmods_run_sh(tmp_path):
    target = _scaffold(tmp_path)
    (target / "run.sh").write_text("stale\n")
    (target / "run.sh").chmod(0o644)
    apply_update(target, force=False)
    mode = (target / "run.sh").stat().st_mode & 0o777
    assert mode & 0o100, f"run.sh not executable: {oct(mode)}"


def test_apply_creates_parent_dirs_for_skills(tmp_path):
    target = _scaffold(tmp_path)
    import shutil
    shutil.rmtree(target / "skills")
    apply_update(target, force=False)
    assert (target / "skills" / "ingest.md").exists()


def test_apply_is_idempotent(tmp_path):
    target = _scaffold(tmp_path)
    (target / "AGENTS.md").write_text("stale\n")
    apply_update(target, force=False)
    second = apply_update(target, force=False)
    assert second == [], "second apply should be a no-op"
```

- [ ] **Step 2: Run to confirm fail**

- [ ] **Step 3: Implement `apply_update` in `update.py`**

```python
def apply_update(target_dir: Path, *, force: bool = False, name: str = "my-wiki") -> list[FileStatus]:
    """Apply bundled-file updates to target_dir. Returns the list of files actually written."""
    written: list[FileStatus] = []
    for s in compute_status(target_dir, name=name):
        if s.state == "identical":
            continue
        if s.class_ == "customisable" and not force:
            continue
        out = target_dir / s.rel_path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(s.bundle_bytes)
        if s.rel_path == "run.sh":
            os.chmod(out, 0o755)
        written.append(s)
    return written
```

- [ ] **Step 4: Tests should pass**

---

## Task 3: CLI command `lwt update`

**Files:**
- Modify: `src/llm_wiki/cli.py`
- Modify: `tests/test_update.py`

- [ ] **Step 1: Append failing CLI tests**

```python
def test_cli_update_dry_run_default(tmp_path):
    target = _scaffold(tmp_path)
    (target / "AGENTS.md").write_text("stale\n")
    result = CliRunner().invoke(main, ["update", str(target)])
    assert result.exit_code == 0
    assert "AGENTS.md" in result.output
    assert "differs" in result.output
    assert (target / "AGENTS.md").read_text() == "stale\n"  # untouched


def test_cli_update_apply_writes_canonical(tmp_path):
    target = _scaffold(tmp_path)
    (target / "AGENTS.md").write_text("stale\n")
    result = CliRunner().invoke(main, ["update", str(target), "--apply"])
    assert result.exit_code == 0
    assert (target / "AGENTS.md").read_text() != "stale\n"


def test_cli_update_apply_skips_customisable(tmp_path):
    target = _scaffold(tmp_path)
    (target / "CLAUDE.md").write_text("mine\n")
    CliRunner().invoke(main, ["update", str(target), "--apply"])
    assert (target / "CLAUDE.md").read_text() == "mine\n"


def test_cli_update_force_overwrites_customisable(tmp_path):
    target = _scaffold(tmp_path)
    (target / "CLAUDE.md").write_text("mine\n")
    CliRunner().invoke(main, ["update", str(target), "--apply", "--force"])
    assert (target / "CLAUDE.md").read_text() != "mine\n"


def test_cli_update_clean_repo_reports_no_changes(tmp_path):
    target = _scaffold(tmp_path)
    result = CliRunner().invoke(main, ["update", str(target), "--apply"])
    assert "No changes" in result.output or "0 file" in result.output
```

- [ ] **Step 2: Run to confirm fail (`update` command not registered)**

- [ ] **Step 3: Add command in `src/llm_wiki/cli.py`**

```python
@main.command(name="update")
@click.argument("path", default=".")
@click.option("--apply", "apply_changes", is_flag=True, default=False,
              help="Write changes (default: dry-run / status only).")
@click.option("--force", is_flag=True, default=False,
              help="Also overwrite customisable files (CLAUDE.md, templates/, …).")
def update_cmd(path: str, apply_changes: bool, force: bool) -> None:
    """Refresh bundled assets (AGENTS.md, skills/, run.sh) in an existing wiki repo."""
    from llm_wiki.update import apply_update, compute_status
    target = Path(path)
    statuses = compute_status(target)
    differs = [s for s in statuses if s.state != "identical"]
    if not differs:
        click.echo("All bundled files match. Nothing to do.")
        return
    # Print status table
    width = max(len(s.rel_path) for s in differs)
    click.echo(f"{'File':<{width}}  {'Class':<13}  {'State':<10}  Action")
    click.echo("-" * (width + 40))
    for s in differs:
        action = (
            "will update" if (s.class_ == "canonical" or force)
            else "skip (use --force)"
        )
        click.echo(f"{s.rel_path:<{width}}  {s.class_:<13}  {s.state:<10}  {action}")
    if not apply_changes:
        click.echo("\nDry run — pass --apply to write changes.")
        return
    written = apply_update(target, force=force)
    click.echo(f"\nUpdated {len(written)} file(s).")
```

- [ ] **Step 4: All tests green; manual smoke test**

```bash
.venv/bin/pytest tests/test_update.py -v
.venv/bin/lwt update --help
```

---

## Task 4: Documentation

**Files:**
- Modify: `docs/runbook.md`
- Modify: `src/llm_wiki/data/AGENTS.md`

- [ ] **Step 1: Add a "Refresh bundled assets" section to `docs/runbook.md`**

Document the workflow:

```bash
cd <wiki-data-repo>
lwt update                  # dry-run; show what would change
lwt update --apply          # update canonical files (AGENTS.md, skills/, run.sh, run.ps1)
lwt update --apply --force  # also overwrite CLAUDE.md, templates/, …
git diff                    # review changes
git commit -am "chore: refresh lwt bundled assets"
```

- [ ] **Step 2: Mention the new command in bundled `AGENTS.md`** under "Tool surface" so future scaffolds know about it.

```markdown
| lwt update                       | Refresh bundled assets (AGENTS.md, skills/, run.sh) |
```

---

## Task 5: Final verification

- [ ] **Step 1: Full test suite green**

```bash
.venv/bin/pytest -q
```

- [ ] **Step 2: Smoke test against this repo's own data**

```bash
# Build a throwaway scaffold:
.venv/bin/lwt init /tmp/lwt-update-smoke --name "Smoke"
# Make it stale:
echo "stale" >> /tmp/lwt-update-smoke/AGENTS.md
echo "custom" > /tmp/lwt-update-smoke/CLAUDE.md
# Dry run:
.venv/bin/lwt update /tmp/lwt-update-smoke
# Apply:
.venv/bin/lwt update /tmp/lwt-update-smoke --apply
# AGENTS.md should now match bundle; CLAUDE.md still says "custom":
diff /tmp/lwt-update-smoke/AGENTS.md src/llm_wiki/data/AGENTS.md
cat /tmp/lwt-update-smoke/CLAUDE.md
# Force overwrite:
.venv/bin/lwt update /tmp/lwt-update-smoke --apply --force
diff /tmp/lwt-update-smoke/CLAUDE.md src/llm_wiki/data/CLAUDE.md
```

- [ ] **Step 3: Update `docs/decisions.md`** with a dated entry recording the file taxonomy choice and Phase-1 scope.

- [ ] **Step 4: Commit per task** (one commit per Task 1-4, plus a docs commit). Tests must pass at every commit boundary.

---

## Risks and how this could age badly

- **Two-class taxonomy is a guess.** If users routinely customise `skills/*`, those need to move to "customisable". Phase 2's manifest fixes this properly; for now, the user feedback loop is "did your customisation get clobbered?"
- **`__NAME__` substitution drift.** README.md is treated as customisable but compared against the substituted-bundle. If a user changes the wiki name, the comparison will always say "differs". Acceptable for Phase 1; manifest in Phase 2 records the substituted SHA.
- **No backup before overwrite.** A bad bundle ships → user loses local changes (canonical files only). Mitigation: always commit before `lwt update --apply`. Phase 3 adds 3-way merge which removes the risk.

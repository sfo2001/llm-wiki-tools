# Phase 0: Wheel Distribution + Self-Bootstrapping Wiki Repos

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `llm-wiki-tools` distributable as a versioned wheel, and make every scaffolded wiki repo self-bootstrap its own venv from a wheel committed under `tools/`. Once shipped, a wiki repo can be cloned anywhere with Python 3.11+ and run with `./run.sh serve` — no developer environment, no PyPI, no network access to gitea.

**Why Phase 0 (precedes Phase 1):** Phase 1 (`lwt update`) refreshes bundled *assets* in a deployed wiki, but the wiki still depends on a system-wide editable install of the lwt package — invisible to anyone but the developer. Phase 0 fixes the "how does lwt itself get there?" question, after which Phase 1's asset refresh is the right next abstraction. Both phases together compose into a complete deployment story.

**Architecture:**
- **Versioning:** `hatch-vcs` derives the version from `git describe`. The wheel filename is the version of record. Tags are the only way to ship a clean release; intermediate builds get `.dev` suffixes that signal "do not distribute".
- **Build pipeline:** `release.sh` asserts a clean tagged tree, then runs `python -m build`. Output goes to `dist/`.
- **Wiki bootstrap:** Each wiki repo has a `tools/` directory holding a wheel (`llm_wiki_tools-X.Y.Z-py3-none-any.whl`). `run.sh` and `run.ps1` create `venv/` on first run, `pip install --upgrade tools/*.whl[mkdocs]`, then exec `venv/bin/lwt`. A marker file (`venv/.installed-wheel`) records which wheel is currently installed so subsequent runs skip the pip step.
- **Updates:** `lwt update --tools <wheel>` copies a new wheel into `<wiki>/tools/`, prunes older wheels, and triggers reinstall on next `run.sh` invocation. Composes with Phase 1's asset-refresh flags (`--apply`, `--force`).
- **Bootstrap-from-zero:** `lwt init --wheel <path>` immediately seeds the new scaffold's `tools/` with a wheel so the result is self-contained from the very first commit.

**Tech Stack:** Python 3.11+, hatchling, hatch-vcs, pip, bash, PowerShell, click, pytest.

**Out of scope:**
- Network-based update mechanisms (HTTP fetch, git clone-from-bundle) → keep the deliberate "drop a file in `tools/`" UX.
- Phase 1 asset refresh — orthogonal; assumed in place by the time `lwt update --tools` ships.
- Multi-version installs (e.g. `lwt @ 0.2.0` for one wiki, `lwt @ 0.3.0` for another) — already supported by per-wiki venv; no extra design needed.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `pyproject.toml` | Modify | Add `hatch-vcs` to build deps; switch `version` to dynamic; configure `[tool.hatch.version]` and version-file hook |
| `src/llm_wiki/__init__.py` | Modify | Read `__version__` from generated `_version.py`; keep `__git_hash__` mechanism |
| `src/llm_wiki/_version.py` | Generate | Auto-written by hatch-vcs at build time; gitignored |
| `.gitignore` | Modify | Add `src/llm_wiki/_version.py`, `dist/`, `build/` |
| `release.sh` | Create | Clean-tree + on-tag check; runs `python -m build` |
| `src/llm_wiki/data/run.sh` | Modify | Bootstrap venv from `tools/*.whl`; dispatch to subcommands |
| `src/llm_wiki/data/run.ps1` | Modify | Same logic for Windows PowerShell |
| `src/llm_wiki/data/.gitignore.template` | Modify | Add `venv/`, exclude `tools/*.whl` from gitignore (the opposite of usual) |
| `src/llm_wiki/init.py` | Modify | Create `tools/` dir; copy wheel if `--wheel` passed |
| `src/llm_wiki/cli.py` | Modify | Add `--wheel` to `lwt init`; add `--tools <path>` to `lwt update` |
| `src/llm_wiki/update.py` | Modify | Add `install_wheel(target_dir, wheel_path, prune=True)` |
| `tests/test_update.py` | Modify | Tests for `--tools` wheel install + prune |
| `tests/test_cli.py` | Modify | Tests for `lwt init --wheel` |
| `tests/test_release.py` | Create | Tests assert hatch-vcs reads version from git tag |
| `docs/runbook.md` | Modify | Document release workflow + wiki bootstrap |
| `docs/decisions.md` | Modify | Record hatch-vcs + wheel choice |
| `src/llm_wiki/data/AGENTS.md` | Modify | Mention `lwt update --tools` |
| `src/llm_wiki/data/README.md.template` | Modify | First-run instructions for recipients |

---

## Task 1: Wire up hatch-vcs

Goal: version comes from git tags, no manual bumps in `pyproject.toml`.

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/llm_wiki/__init__.py`
- Modify: `.gitignore`

- [ ] **Step 1: Edit `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[project]
name = "llm-wiki-tools"
# version = "0.1.0"   ← REMOVE this line
dynamic = ["version"]
requires-python = ">=3.11"
# … rest unchanged …

[tool.hatch.version]
source = "vcs"

[tool.hatch.build.hooks.vcs]
version-file = "src/llm_wiki/_version.py"

[tool.hatch.version.raw-options]
local_scheme = "no-local-version"
```

`local_scheme = "no-local-version"` strips the `+g<sha>` suffix so wheels are reinstallable by pip without `--force-reinstall`. `.dev` and `.post` modifiers remain.

- [ ] **Step 2: Edit `src/llm_wiki/__init__.py`**

Replace the hardcoded `__version__` with a runtime import that falls back gracefully when the generated file is absent (editable installs without a build).

```python
try:
    from llm_wiki._version import __version__
except ImportError:  # editable install before first build
    from importlib.metadata import PackageNotFoundError, version
    try:
        __version__ = version("llm-wiki-tools")
    except PackageNotFoundError:
        __version__ = "0.0.0+unknown"
```

`__git_hash__` stays as is (read from `git rev-parse HEAD` at runtime if you want the working-tree commit, or hardcode `"unknown"` for installed wheels).

- [ ] **Step 3: Add to `.gitignore`**

```
src/llm_wiki/_version.py
dist/
build/
*.egg-info/
```

- [ ] **Step 4: Tag the current state and confirm hatch-vcs reads it**

```bash
git tag -a v0.1.0 -m "Initial release: lwt CLI with ingest/search/lint/deploy/init/log-entry/update"
.venv/bin/pip install -U hatch-vcs hatchling build
.venv/bin/python -m build --wheel
ls dist/
# expect: llm_wiki_tools-0.1.0-py3-none-any.whl
.venv/bin/pip install --force-reinstall dist/llm_wiki_tools-0.1.0-py3-none-any.whl
.venv/bin/lwt --version
# expect: lwt, version 0.1.0
```

- [ ] **Step 5: Re-install in editable mode (developer workflow continues to work)**

```bash
.venv/bin/pip install -e ".[dev,mkdocs]"
.venv/bin/lwt --version
# expect: lwt, version 0.1.0   (since HEAD is on tag v0.1.0)
```

After making one new commit (without a new tag), the version should become `0.1.1.dev1` — confirms the `.dev` discipline works.

---

## Task 2: `release.sh` — disciplined wheel build

**Files:**
- Create: `release.sh`

- [ ] **Step 1: Write `release.sh`**

```bash
#!/usr/bin/env bash
# Build a release wheel + sdist. Refuses to run on a dirty or untagged tree.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

# 1. Clean working tree
if [[ -n "$(git status --porcelain)" ]]; then
    echo "✗ working tree dirty — commit or stash before releasing" >&2
    exit 1
fi

# 2. HEAD is on a tag
TAG=$(git describe --exact-match --tags HEAD 2>/dev/null || true)
if [[ -z "$TAG" ]]; then
    echo "✗ HEAD is not on a tag." >&2
    echo "  Tag first:  git tag -a vX.Y.Z -m 'release notes here'" >&2
    exit 1
fi

# 3. Tag matches semver-ish vX.Y.Z
if ! [[ "$TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "✗ tag $TAG does not match vX.Y.Z" >&2
    exit 1
fi

# 4. Build
rm -rf dist/ build/
.venv/bin/python -m build

# 5. Confirm wheel filename matches tag
EXPECTED="llm_wiki_tools-${TAG#v}-py3-none-any.whl"
if [[ ! -f "dist/$EXPECTED" ]]; then
    echo "✗ expected dist/$EXPECTED but got:" >&2
    ls dist/ >&2
    exit 1
fi

echo
echo "✓ Built $EXPECTED"
ls -la dist/
```

`chmod +x release.sh` after creation.

- [ ] **Step 2: Smoke test**

```bash
./release.sh
# expect: ✓ Built llm_wiki_tools-0.1.0-py3-none-any.whl
```

---

## Task 3: New `run.sh` — bootstrap from `tools/*.whl`

**Files:**
- Modify: `src/llm_wiki/data/run.sh`
- Modify: `src/llm_wiki/data/.gitignore.template`

- [ ] **Step 1: Replace `src/llm_wiki/data/run.sh` with bootstrap version**

```bash
#!/usr/bin/env bash
# llm-wiki-tools wrapper — bootstraps a per-wiki venv from tools/*.whl
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV="$SCRIPT_DIR/venv"
WHEEL_DIR="$SCRIPT_DIR/tools"
MARKER="$VENV/.installed-wheel"

# Locate newest wheel
WHEEL=$(ls -t "$WHEEL_DIR"/llm_wiki_tools-*.whl 2>/dev/null | head -1 || true)
if [[ -z "$WHEEL" ]]; then
    echo "✗ No wheel found in $WHEEL_DIR/" >&2
    echo "  Drop a llm_wiki_tools-*.whl in tools/ and re-run." >&2
    exit 1
fi
WHEEL_NAME=$(basename "$WHEEL")

# Bootstrap venv if missing
if [[ ! -d "$VENV" ]]; then
    echo "→ Creating venv at $VENV"
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install --quiet --upgrade pip
fi

# Install wheel if not yet installed or wheel changed
if [[ ! -f "$MARKER" ]] || [[ "$(cat "$MARKER")" != "$WHEEL_NAME" ]]; then
    echo "→ Installing $WHEEL_NAME"
    "$VENV/bin/pip" install --quiet --force-reinstall "${WHEEL}[mkdocs]"
    echo "$WHEEL_NAME" > "$MARKER"
fi

# Dispatch
LWT="$VENV/bin/lwt"
case "${1:-help}" in
    serve)     shift; exec "$LWT" deploy --target mkdocs --wiki-dir wiki "$@" ;;
    build)     shift; exec "$LWT" deploy --target mkdocs --wiki-dir wiki --build "$@" ;;
    ingest)    shift; exec "$LWT" ingest --wiki-dir wiki "$@" ;;
    search)    shift; exec "$LWT" search --wiki-dir wiki "$@" ;;
    lint)      shift; exec "$LWT" lint --wiki-dir wiki "$@" ;;
    log-entry) shift; exec "$LWT" log-entry --wiki-dir wiki "$@" ;;
    update)    shift; exec "$LWT" update "$SCRIPT_DIR" "$@" ;;
    help|--help|-h)
        cat <<EOF
Usage: ./run.sh <command> [args]

Commands:
  serve              Serve wiki/ via mkdocs (default port 8000)
  build              Build static site to .build/site/
  ingest <source>    Ingest a file or URL into wiki/.tmp/
  search <terms>     BM25 search over wiki/
  lint               Run lint checks (--all, --structural, --newlines, --append-only)
  log-entry          Append to wiki/log.md
  update             Refresh bundled assets and/or install new wheel
                     ./run.sh update --apply              # asset refresh
                     ./run.sh update --tools <new.whl>    # swap wheel
EOF
        ;;
    *) exec "$LWT" "$@" ;;
esac
```

- [ ] **Step 2: Add corresponding `run.ps1` bootstrap**

```powershell
# llm-wiki-tools wrapper — bootstraps a per-wiki venv from tools/*.whl
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$Venv = Join-Path $ScriptDir "venv"
$WheelDir = Join-Path $ScriptDir "tools"
$Marker = Join-Path $Venv ".installed-wheel"

# Locate newest wheel
$Wheel = Get-ChildItem -Path $WheelDir -Filter "llm_wiki_tools-*.whl" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $Wheel) {
    Write-Error "No wheel found in $WheelDir/. Drop a llm_wiki_tools-*.whl there and re-run."
    exit 1
}

# Bootstrap venv
if (-not (Test-Path $Venv)) {
    Write-Host "→ Creating venv at $Venv"
    python -m venv $Venv
    & "$Venv\Scripts\pip.exe" install --quiet --upgrade pip
}

# Install wheel if changed
$Installed = if (Test-Path $Marker) { Get-Content $Marker } else { "" }
if ($Installed -ne $Wheel.Name) {
    Write-Host "→ Installing $($Wheel.Name)"
    & "$Venv\Scripts\pip.exe" install --quiet --force-reinstall "$($Wheel.FullName)[mkdocs]"
    $Wheel.Name | Out-File -FilePath $Marker -Encoding ASCII
}

$Lwt = "$Venv\Scripts\lwt.exe"
$Cmd = if ($args.Count -gt 0) { $args[0] } else { "help" }
$Rest = if ($args.Count -gt 1) { $args[1..($args.Count - 1)] } else { @() }

switch ($Cmd) {
    "serve"     { & $Lwt deploy --target mkdocs --wiki-dir wiki @Rest }
    "build"     { & $Lwt deploy --target mkdocs --wiki-dir wiki --build @Rest }
    "ingest"    { & $Lwt ingest --wiki-dir wiki @Rest }
    "search"    { & $Lwt search --wiki-dir wiki @Rest }
    "lint"      { & $Lwt lint --wiki-dir wiki @Rest }
    "log-entry" { & $Lwt log-entry --wiki-dir wiki @Rest }
    "update"    { & $Lwt update $ScriptDir @Rest }
    {"help","--help","-h" -contains $_} {
        Write-Host @"
Usage: .\run.ps1 <command> [args]
… (mirror run.sh help text)
"@
    }
    Default { & $Lwt $args }
}
exit $LASTEXITCODE
```

- [ ] **Step 3: Update `src/llm_wiki/data/.gitignore.template`**

Add:
```
venv/
.build/
```

`tools/*.whl` is intentionally **not** gitignored — wheels are committed assets.

---

## Task 4: `lwt update --tools <wheel>` — swap in a new wheel

**Files:**
- Modify: `src/llm_wiki/update.py`
- Modify: `src/llm_wiki/cli.py`
- Modify: `tests/test_update.py`

- [ ] **Step 1: Append failing tests**

```python
def test_install_wheel_copies_to_tools(tmp_path):
    target = _scaffold(tmp_path)
    fake_wheel = tmp_path / "llm_wiki_tools-0.2.0-py3-none-any.whl"
    fake_wheel.write_bytes(b"PK\x03\x04fake")
    from llm_wiki.update import install_wheel
    written = install_wheel(target, fake_wheel)
    assert (target / "tools" / "llm_wiki_tools-0.2.0-py3-none-any.whl").exists()
    assert (target / "tools" / "llm_wiki_tools-0.2.0-py3-none-any.whl").read_bytes() == b"PK\x03\x04fake"


def test_install_wheel_prunes_older_wheels(tmp_path):
    target = _scaffold(tmp_path)
    (target / "tools").mkdir(exist_ok=True)
    (target / "tools" / "llm_wiki_tools-0.1.0-py3-none-any.whl").write_bytes(b"old")
    new_wheel = tmp_path / "llm_wiki_tools-0.2.0-py3-none-any.whl"
    new_wheel.write_bytes(b"new")
    from llm_wiki.update import install_wheel
    install_wheel(target, new_wheel, prune=True)
    wheels = sorted((target / "tools").glob("*.whl"))
    assert len(wheels) == 1
    assert wheels[0].name == "llm_wiki_tools-0.2.0-py3-none-any.whl"


def test_install_wheel_rejects_non_wheel(tmp_path):
    target = _scaffold(tmp_path)
    bogus = tmp_path / "totally-not-a-wheel.txt"
    bogus.write_text("nope")
    from llm_wiki.update import install_wheel
    with pytest.raises(ValueError, match="wheel"):
        install_wheel(target, bogus)


def test_cli_update_tools_copies_wheel(tmp_path):
    target = _scaffold(tmp_path)
    wheel = tmp_path / "llm_wiki_tools-0.3.0-py3-none-any.whl"
    wheel.write_bytes(b"PK\x03\x04")
    result = CliRunner().invoke(main, ["update", str(target), "--tools", str(wheel)])
    assert result.exit_code == 0
    assert (target / "tools" / "llm_wiki_tools-0.3.0-py3-none-any.whl").exists()


def test_cli_update_tools_combines_with_apply(tmp_path):
    target = _scaffold(tmp_path)
    (target / "AGENTS.md").write_text("stale\n")
    wheel = tmp_path / "llm_wiki_tools-0.3.0-py3-none-any.whl"
    wheel.write_bytes(b"PK")
    result = CliRunner().invoke(
        main, ["update", str(target), "--apply", "--tools", str(wheel)],
    )
    assert result.exit_code == 0
    # Both happened:
    assert (target / "tools" / "llm_wiki_tools-0.3.0-py3-none-any.whl").exists()
    assert (target / "AGENTS.md").read_text() != "stale\n"
```

- [ ] **Step 2: Implement `install_wheel` in `src/llm_wiki/update.py`**

```python
import re
import shutil

_WHEEL_RE = re.compile(r"^llm_wiki_tools-[\w.+-]+-py3-none-any\.whl$")


def install_wheel(target_dir: Path, wheel_path: Path, *, prune: bool = True) -> Path:
    """Copy a llm_wiki_tools-*.whl into target_dir/tools/ and (optionally) remove older wheels.

    Returns the deployed wheel path.
    Raises ValueError if wheel_path doesn't look like a llm-wiki-tools wheel.
    """
    if not _WHEEL_RE.match(wheel_path.name):
        raise ValueError(
            f"Not a llm-wiki-tools wheel: {wheel_path.name!r}. "
            f"Expected llm_wiki_tools-X.Y.Z-py3-none-any.whl."
        )
    if not wheel_path.is_file():
        raise FileNotFoundError(wheel_path)

    tools_dir = target_dir / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)

    if prune:
        for old in tools_dir.glob("llm_wiki_tools-*.whl"):
            if old.name != wheel_path.name:
                old.unlink()

    dest = tools_dir / wheel_path.name
    shutil.copyfile(wheel_path, dest)
    return dest
```

- [ ] **Step 3: Wire `--tools` into the CLI**

In `update_cmd`:

```python
@click.option("--tools", "tools_wheel", default=None, type=click.Path(exists=True),
              help="Path to a new llm_wiki_tools-*.whl; copies it into <PATH>/tools/ and prunes older wheels.")
def update_cmd(path: str, apply_changes: bool, force: bool, tools_wheel: str | None) -> None:
    ...
    if tools_wheel:
        from llm_wiki.update import install_wheel
        dest = install_wheel(target, Path(tools_wheel))
        click.echo(f"→ Installed wheel: {dest.relative_to(target)}")
        click.echo(f"  (run.sh / run.ps1 will reinstall on next invocation)")
    # …existing asset-refresh logic continues unchanged…
```

When neither `--apply` nor `--tools` is given and there are no asset diffs, the command prints "Nothing to do" as in Phase 1.

- [ ] **Step 4: All tests green**

---

## Task 5: `lwt init --wheel <path>` — self-contained scaffold from day one

**Files:**
- Modify: `src/llm_wiki/init.py`
- Modify: `src/llm_wiki/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add tests**

```python
def test_lwt_init_creates_tools_dir(tmp_path):
    CliRunner().invoke(main, ["init", str(tmp_path / "wiki")])
    assert (tmp_path / "wiki" / "tools").is_dir()


def test_lwt_init_with_wheel_copies_it(tmp_path):
    wheel = tmp_path / "llm_wiki_tools-0.1.0-py3-none-any.whl"
    wheel.write_bytes(b"PK")
    target = tmp_path / "wiki"
    CliRunner().invoke(main, ["init", str(target), "--wheel", str(wheel)])
    assert (target / "tools" / "llm_wiki_tools-0.1.0-py3-none-any.whl").exists()


def test_lwt_init_without_wheel_warns(tmp_path):
    target = tmp_path / "wiki"
    result = CliRunner().invoke(main, ["init", str(target)])
    assert "tools/" in result.output
    assert "wheel" in result.output.lower()
```

- [ ] **Step 2: Modify `scaffold_data_repo` and CLI**

`init.py`:
```python
def scaffold_data_repo(target_dir: Path, name: str = "my-wiki",
                       wheel: Path | None = None) -> None:
    # … existing logic …

    # tools/ directory (always created; empty unless --wheel passed)
    tools_dir = target_dir / "tools"
    tools_dir.mkdir(exist_ok=True)
    if wheel is not None:
        from llm_wiki.update import install_wheel
        install_wheel(target_dir, wheel, prune=True)
```

`cli.py`:
```python
@main.command(name="init")
@click.argument("path", default=".")
@click.option("--name", default="my-wiki", show_default=True)
@click.option("--wheel", default=None, type=click.Path(exists=True),
              help="Seed tools/ with a wheel so the wiki is self-bootstrapping immediately.")
def init_cmd(path: str, name: str, wheel: str | None) -> None:
    """Scaffold a new llm-wiki data repository."""
    from llm_wiki.init import scaffold_data_repo
    target = Path(path)
    scaffold_data_repo(target, name=name, wheel=Path(wheel) if wheel else None)
    click.echo(f"Initialized wiki at {target.resolve()}")
    if wheel is None:
        click.echo("\n⚠ No wheel installed. Drop a llm_wiki_tools-*.whl into tools/")
        click.echo("  before ./run.sh works. (Re-run lwt init with --wheel to do it now.)")
    # … existing summary echos …
```

---

## Task 6: Documentation

**Files:**
- Modify: `docs/runbook.md`
- Modify: `docs/decisions.md`
- Modify: `src/llm_wiki/data/AGENTS.md`
- Modify: `src/llm_wiki/data/README.md.template`

- [ ] **Step 1: Add a "Releasing a new lwt version" section to `docs/runbook.md`**

Document the loop:
1. Make changes, commit
2. `git tag -a vX.Y.Z -m "release notes"`
3. `git push --tags`
4. `./release.sh` → produces `dist/llm_wiki_tools-X.Y.Z-py3-none-any.whl`
5. For each in-use wiki: `lwt update <wiki-path> --tools dist/llm_wiki_tools-X.Y.Z-py3-none-any.whl --apply`
6. Commit the new wheel + asset diffs in each wiki repo

- [ ] **Step 2: Add a "First-run / fresh deployment" section to `docs/runbook.md`**

```bash
# Recipient on a fresh machine:
git clone <wiki-repo-url> my-wiki
cd my-wiki
./run.sh serve
# → creates venv/, installs from tools/*.whl, serves the wiki
```

- [ ] **Step 3: Append a decision entry to `docs/decisions.md`**

Title: `2026-04-26 — Phase 0: hatch-vcs versioning + wheel-in-tools/ distribution`. Body: rationale ("personal tool; no PyPI; recipients may not have any access to your gitea or github; wheel-in-repo gives a single self-contained tarball"), alternatives rejected (PyPI publish; git+ssh; bare git bundle), aging risks (wheels accumulate in git history → wiki repo grows; mitigated by `--prune`).

- [ ] **Step 4: Update bundled `AGENTS.md` tool surface**

```
| lwt update --tools <wheel>       | Swap in a new lwt version (drops wheel into tools/) |
```

- [ ] **Step 5: Update `README.md.template`**

The recipient-facing README needs:
- "Requirements: Python 3.11+. Nothing else."
- "First run: `./run.sh serve` (creates venv from `tools/*.whl` automatically)"
- "Updating lwt: drop a new wheel into `tools/` and re-run; the bootstrap detects it"

---

## Task 7: Migration of existing wikis (one-time, manual)

For the in-use `test-wiki`:

- [ ] **Step 1: Build the v0.1.0 wheel** (after Task 1 completes)

```bash
./release.sh
```

- [ ] **Step 2: Add `tools/` and the wheel to test-wiki**

```bash
cd /path/to/test-wiki
mkdir -p tools
cp /path/to/llm-wiki-tools/dist/llm_wiki_tools-0.1.0-py3-none-any.whl tools/
echo "venv/" >> .gitignore
echo ".build/" >> .gitignore
# refresh run.sh / run.ps1 from the new bundle:
lwt update . --apply --force   # --force required because run.sh is canonical but old version is incompatible
git add tools/ .gitignore run.sh run.ps1
git commit -m "chore: bootstrap from wheel; remove dependency on system lwt"
```

(The `--force` is necessary the first time only because the old `run.sh` is a hand-written file rather than a copy of the bundle. After this commit, it's just the canonical bundled run.sh.)

- [ ] **Step 3: Verify**

```bash
cd /path/to/test-wiki
rm -rf venv  # ensure clean state
./run.sh --version
# → should bootstrap venv, install lwt 0.1.0 from tools/, print version
./run.sh lint --all
```

---

## Task 8: Final verification

- [ ] **Step 1: Full test suite green** (`pytest -q`)

- [ ] **Step 2: End-to-end smoke test (fresh wiki)**

```bash
mkdir -p /tmp/lwt-phase0-smoke
.venv/bin/lwt init /tmp/lwt-phase0-smoke --name "Smoke" --wheel dist/llm_wiki_tools-0.1.0-py3-none-any.whl
ls /tmp/lwt-phase0-smoke/tools/   # should contain the wheel
cd /tmp/lwt-phase0-smoke
./run.sh --version                 # should bootstrap and print 0.1.0
rm -rf /tmp/lwt-phase0-smoke
```

- [ ] **Step 3: Tagged release flow**

```bash
# After all Phase 0 commits:
git tag -a v0.2.0 -m "Phase 0: wheel distribution + self-bootstrapping wikis"
git push origin main --tags
./release.sh                       # produces dist/llm_wiki_tools-0.2.0-py3-none-any.whl
# Distribute to test-wiki:
lwt update /path/to/test-wiki \
    --tools dist/llm_wiki_tools-0.2.0-py3-none-any.whl --apply
```

- [ ] **Step 4: Update plan checklist boxes** as each task completes; commit per task.

---

## Risks and how this could age badly

- **Wheels accumulate in wiki repo git history.** Each version adds ~30 KB to the wiki's history. After 50 releases that's ~1.5 MB of binary-ish blobs in `git log`. `--prune` removes the working-tree wheel but git history is forever. Mitigation: `git filter-repo` someday, or accept it.
- **`--force-reinstall` on every wheel change re-downloads transitive deps.** First run takes ~30s; subsequent runs with the same wheel skip via the marker file. For airgapped recipients this is a one-time cost per version.
- **`hatch-vcs` requires git history at build time.** A tarball-only checkout (e.g. shallow clone) can't build a wheel. Mitigation: `release.sh` runs in the full repo only; recipients install from a wheel and never need to build.
- **Tag discipline is human-enforced.** Forgetting to tag → next build is `0.1.0.dev1+...`, which `release.sh` rejects but a manual `python -m build` doesn't. Mitigation: only ever distribute wheels produced by `release.sh`; never `python -m build` directly.
- **Wheel marker drift.** If a user modifies `tools/*.whl` filenames manually or partially, the marker logic could install the wrong version. Mitigation: documented "drop one wheel, let `--prune` handle the rest" UX.

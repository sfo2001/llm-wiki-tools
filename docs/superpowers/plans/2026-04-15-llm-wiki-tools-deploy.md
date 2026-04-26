# llm-wiki-tools Deploy + Init + Schema Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add WikiBackend deploy targets (local/Docker/Confluence stub), `lwt deploy`, `lwt init`, AGENTS.md, skills/, and bundled templates to complete the llm-wiki-tools package.

**Architecture:** WikiBackend ABC in `deploy/base.py` with three concrete backends. A bundled `src/llm_wiki/data/` directory inside the package provides templates and schema files copied by `lwt init`. Two new CLI subcommands (`deploy`, `init`) added to `cli.py`. Text-only schema files (AGENTS.md, CLAUDE.md, skills/) live in the repo root and are also bundled as package data. Tasks are ordered so data files exist before the CLI commands that consume them.

**Tech Stack:** Python 3.11+, click, requests, subprocess, `Path(__file__).parent` for package data, pytest, responses (dev)

---

## File Map

| File | Responsibility |
|------|---------------|
| `src/llm_wiki/deploy/__init__.py` | Package stub |
| `src/llm_wiki/deploy/base.py` | `WikiBackend` ABC — write_page, delete_page, deploy |
| `src/llm_wiki/deploy/local.py` | `LocalBackend` — filesystem write + HTTP serve |
| `src/llm_wiki/deploy/docker.py` | `DockerBackend` — filesystem write + docker run/build |
| `src/llm_wiki/deploy/confluence.py` | `ConfluenceBackend` stub — REST API push, dry_run=True |
| `src/llm_wiki/data/AGENTS.md` | Bundled canonical agent schema |
| `src/llm_wiki/data/CLAUDE.md` | Bundled Claude Code config wrapper |
| `src/llm_wiki/data/.gitignore.template` | Data repo .gitignore |
| `src/llm_wiki/data/.lwt.env.example` | Example credentials file |
| `src/llm_wiki/data/templates/default.md` | Default wiki page template |
| `src/llm_wiki/data/templates/entity.md` | Entity page template |
| `src/llm_wiki/data/templates/concept.md` | Concept page template |
| `src/llm_wiki/data/templates/source-summary.md` | Source summary template |
| `src/llm_wiki/data/templates/query-answer.md` | Query answer template |
| `AGENTS.md` | Repo-root canonical schema (same content as data/AGENTS.md) |
| `CLAUDE.md` | Repo-root Claude Code config (same content as data/CLAUDE.md) |
| `skills/query.md` | Query workflow skill |
| `skills/ingest.md` | Ingest workflow skill |
| `skills/lint.md` | Lint workflow skill |
| `skills/deploy.md` | Deploy workflow skill |
| `src/llm_wiki/init.py` | `scaffold_data_repo()` — copies bundled data to new data repo |
| `src/llm_wiki/cli.py` | Add `deploy` + `init` subcommands |
| `tests/deploy/__init__.py` | Test package |
| `tests/deploy/test_local.py` | LocalBackend tests |
| `tests/deploy/test_docker.py` | DockerBackend tests |
| `tests/deploy/test_confluence.py` | ConfluenceBackend tests |
| `tests/test_cli.py` | Extend with deploy + init tests |

**Task order dependency note:** Tasks 1–4 build the backend library (no CLI). Task 5 adds `lwt deploy` only. Task 6 creates all data files, `init.py`, `lwt init`, and the final test suite.

---

## Task 1: WikiBackend ABC + deploy package scaffold

**Files:**
- Create: `src/llm_wiki/deploy/__init__.py` (empty)
- Create: `src/llm_wiki/deploy/base.py`
- Create: `tests/deploy/__init__.py` (empty)
- Create: `tests/deploy/test_base.py`

- [ ] **Step 1: Write failing test**

```python
# tests/deploy/test_base.py
import pytest
from llm_wiki.deploy.base import WikiBackend


def test_wikibackend_is_abstract():
    with pytest.raises(TypeError):
        WikiBackend()


def test_concrete_subclass_works():
    from pathlib import Path

    class ConcreteBackend(WikiBackend):
        @property
        def target_name(self) -> str:
            return "test"

        def write_page(self, rel_path: str, content: str) -> None:
            pass

        def delete_page(self, rel_path: str) -> None:
            pass

        def deploy(self, wiki_dir: Path) -> None:
            pass

    b = ConcreteBackend()
    assert b.target_name == "test"
```

- [ ] **Step 2: Run — verify fail**

```bash
.venv/bin/pytest tests/deploy/test_base.py -v
```

Expected: `ImportError` — `llm_wiki.deploy` not yet defined.

- [ ] **Step 3: Create empty stubs**

Create two empty files:
- `src/llm_wiki/deploy/__init__.py`
- `tests/deploy/__init__.py`

- [ ] **Step 4: Implement `src/llm_wiki/deploy/base.py`**

```python
from abc import ABC, abstractmethod
from pathlib import Path


class WikiBackend(ABC):
    """Write/deploy interface for wiki backends. No query method — the LLM is the query engine."""

    @property
    @abstractmethod
    def target_name(self) -> str:
        """Human-readable name for this backend (e.g. 'local', 'docker', 'confluence')."""

    @abstractmethod
    def write_page(self, rel_path: str, content: str) -> None:
        """Write a wiki page. rel_path is relative to wiki root (e.g. 'concepts/foo.md')."""

    @abstractmethod
    def delete_page(self, rel_path: str) -> None:
        """Delete a wiki page by relative path."""

    @abstractmethod
    def deploy(self, wiki_dir: Path) -> None:
        """Full sync of wiki_dir to the backend target."""
```

- [ ] **Step 5: Run — verify pass**

```bash
.venv/bin/pytest tests/deploy/test_base.py -v
```

Expected: 2 PASSED.

- [ ] **Step 6: Commit**

```bash
git add src/llm_wiki/deploy/ tests/deploy/
git commit -m "feat: add WikiBackend ABC and deploy package scaffold"
```

---

## Task 2: `deploy/local.py` — LocalBackend

**Files:**
- Create: `src/llm_wiki/deploy/local.py`
- Create: `tests/deploy/test_local.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/deploy/test_local.py
import pytest
from pathlib import Path
from unittest.mock import patch
from llm_wiki.deploy.local import LocalBackend


def test_local_target_name(tmp_path):
    b = LocalBackend(tmp_path / "wiki")
    assert b.target_name == "local"


def test_local_write_page_creates_file(tmp_path):
    b = LocalBackend(tmp_path / "wiki")
    b.write_page("concepts/foo.md", "# Foo\n\nContent.")
    assert (tmp_path / "wiki" / "concepts" / "foo.md").exists()
    assert "# Foo" in (tmp_path / "wiki" / "concepts" / "foo.md").read_text()


def test_local_write_page_creates_parents(tmp_path):
    b = LocalBackend(tmp_path / "wiki")
    b.write_page("a/b/c/page.md", "# Page")
    assert (tmp_path / "wiki" / "a" / "b" / "c" / "page.md").exists()


def test_local_delete_page_removes_file(tmp_path):
    b = LocalBackend(tmp_path / "wiki")
    b.write_page("page.md", "# Page")
    b.delete_page("page.md")
    assert not (tmp_path / "wiki" / "page.md").exists()


def test_local_delete_page_noop_if_missing(tmp_path):
    b = LocalBackend(tmp_path / "wiki")
    b.delete_page("nonexistent.md")  # must not raise


def test_local_server_command_fallback_to_http_server(tmp_path):
    b = LocalBackend(tmp_path / "wiki", port=8080)
    with patch("shutil.which", return_value=None):
        cmd = b._server_command()
    joined = " ".join(cmd)
    assert "http.server" in joined
    assert "8080" in joined
    assert str(tmp_path / "wiki") in joined


def test_local_server_command_prefers_mkdocs(tmp_path):
    b = LocalBackend(tmp_path / "wiki", port=9000)
    def which_side_effect(name):
        return "/usr/bin/mkdocs" if name == "mkdocs" else None
    with patch("shutil.which", side_effect=which_side_effect):
        cmd = b._server_command()
    assert cmd[0] == "mkdocs"
    assert "9000" in " ".join(cmd)


def test_local_deploy_calls_subprocess(tmp_path):
    b = LocalBackend(tmp_path / "wiki", port=8080)
    with patch("shutil.which", return_value=None):
        with patch("subprocess.run") as mock_run:
            b.deploy(tmp_path / "wiki")
    mock_run.assert_called_once()
```

- [ ] **Step 2: Run — verify fail**

```bash
.venv/bin/pytest tests/deploy/test_local.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `src/llm_wiki/deploy/local.py`**

```python
import shutil
import subprocess
from pathlib import Path

from llm_wiki.deploy.base import WikiBackend


class LocalBackend(WikiBackend):
    """Serve wiki/ via local HTTP. write_page() writes directly to filesystem."""

    def __init__(self, wiki_dir: Path, port: int = 8080) -> None:
        self.wiki_dir = wiki_dir
        self.port = port

    @property
    def target_name(self) -> str:
        return "local"

    def write_page(self, rel_path: str, content: str) -> None:
        path = self.wiki_dir / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def delete_page(self, rel_path: str) -> None:
        path = self.wiki_dir / rel_path
        if path.exists():
            path.unlink()

    def _server_command(self) -> list[str]:
        """Return the best available HTTP server command."""
        if shutil.which("mkdocs"):
            return [
                "mkdocs", "serve",
                "--dev-addr", f"0.0.0.0:{self.port}",
                "--docs-dir", str(self.wiki_dir),
            ]
        if shutil.which("grip"):
            return ["grip", str(self.wiki_dir), f"0.0.0.0:{self.port}"]
        return [
            "python3", "-m", "http.server", str(self.port),
            "--directory", str(self.wiki_dir),
        ]

    def deploy(self, wiki_dir: Path) -> None:
        cmd = self._server_command()
        print(f"Starting local server: {' '.join(cmd)}")
        subprocess.run(cmd)
```

- [ ] **Step 4: Run — verify pass**

```bash
.venv/bin/pytest tests/deploy/test_local.py -v
```

Expected: 8 PASSED.

- [ ] **Step 5: Commit**

```bash
git add src/llm_wiki/deploy/local.py tests/deploy/test_local.py
git commit -m "feat: add LocalBackend (filesystem write + HTTP serve)"
```

---

## Task 3: `deploy/docker.py` — DockerBackend

**Files:**
- Create: `src/llm_wiki/deploy/docker.py`
- Create: `tests/deploy/test_docker.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/deploy/test_docker.py
import pytest
from pathlib import Path
from unittest.mock import patch
from llm_wiki.deploy.docker import DockerBackend


def test_docker_target_name(tmp_path):
    b = DockerBackend(tmp_path / "wiki")
    assert b.target_name == "docker"


def test_docker_write_page(tmp_path):
    b = DockerBackend(tmp_path / "wiki")
    b.write_page("page.md", "# Page")
    assert (tmp_path / "wiki" / "page.md").exists()
    assert "# Page" in (tmp_path / "wiki" / "page.md").read_text()


def test_docker_delete_page(tmp_path):
    b = DockerBackend(tmp_path / "wiki")
    b.write_page("page.md", "# Page")
    b.delete_page("page.md")
    assert not (tmp_path / "wiki" / "page.md").exists()


def test_docker_volume_command_contains_docker_run(tmp_path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    b = DockerBackend(wiki, port=8443, mode="volume")
    cmd = b._volume_command(wiki)
    assert "docker" in cmd
    assert "run" in cmd
    assert "nginx:alpine" in cmd
    assert "8443:80" in " ".join(cmd)
    assert str(wiki.resolve()) in " ".join(cmd)


def test_docker_image_command_contains_docker_build(tmp_path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    b = DockerBackend(wiki, port=8443, mode="image", tag="llm-wiki:latest")
    cmd = b._image_command(wiki)
    assert "docker" in cmd
    assert "build" in cmd
    assert "llm-wiki:latest" in cmd


def test_docker_deploy_volume_calls_docker_run(tmp_path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    b = DockerBackend(wiki, mode="volume")
    with patch("subprocess.run") as mock_run:
        b.deploy(wiki)
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert "docker" in cmd and "run" in cmd


def test_docker_deploy_image_calls_docker_build(tmp_path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    b = DockerBackend(wiki, mode="image")
    with patch("subprocess.run") as mock_run:
        b.deploy(wiki)
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert "docker" in cmd and "build" in cmd
```

- [ ] **Step 2: Run — verify fail**

```bash
.venv/bin/pytest tests/deploy/test_docker.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `src/llm_wiki/deploy/docker.py`**

```python
import subprocess
from pathlib import Path
from typing import Literal

from llm_wiki.deploy.base import WikiBackend


class DockerBackend(WikiBackend):
    """Deploy wiki/ in Docker. Two modes: volume (live updates) or image (baked snapshot)."""

    def __init__(
        self,
        wiki_dir: Path,
        port: int = 8443,
        mode: Literal["volume", "image"] = "volume",
        image: str = "nginx:alpine",
        tag: str = "llm-wiki:latest",
        compose_file: Path | None = None,
    ) -> None:
        self.wiki_dir = wiki_dir
        self.port = port
        self.mode = mode
        self.image = image
        self.tag = tag
        self.compose_file = compose_file

    @property
    def target_name(self) -> str:
        return "docker"

    def write_page(self, rel_path: str, content: str) -> None:
        path = self.wiki_dir / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def delete_page(self, rel_path: str) -> None:
        path = self.wiki_dir / rel_path
        if path.exists():
            path.unlink()

    def _volume_command(self, wiki_dir: Path) -> list[str]:
        return [
            "docker", "run", "-d",
            "-v", f"{wiki_dir.resolve()}:/usr/share/nginx/html:ro",
            "-p", f"{self.port}:80",
            self.image,
        ]

    def _image_command(self, wiki_dir: Path) -> list[str]:
        return [
            "docker", "build",
            "-t", self.tag,
            "--build-arg", f"WIKI_SRC={wiki_dir.resolve()}",
            str(wiki_dir.resolve()),
        ]

    def deploy(self, wiki_dir: Path) -> None:
        cmd = (
            self._volume_command(wiki_dir)
            if self.mode == "volume"
            else self._image_command(wiki_dir)
        )
        print(f"Running: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
```

- [ ] **Step 4: Run — verify pass**

```bash
.venv/bin/pytest tests/deploy/test_docker.py -v
```

Expected: 7 PASSED.

- [ ] **Step 5: Commit**

```bash
git add src/llm_wiki/deploy/docker.py tests/deploy/test_docker.py
git commit -m "feat: add DockerBackend (volume + image modes)"
```

---

## Task 4: `deploy/confluence.py` — ConfluenceBackend stub

**Files:**
- Create: `src/llm_wiki/deploy/confluence.py`
- Create: `tests/deploy/test_confluence.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/deploy/test_confluence.py
import pytest
import responses as resp_mock
from pathlib import Path
from llm_wiki.deploy.confluence import ConfluenceBackend


def test_confluence_target_name():
    b = ConfluenceBackend(url="https://wiki.example.com", token="tok", space="TEST")
    assert b.target_name == "confluence"


def test_confluence_write_page_dry_run_prints_message(capsys):
    b = ConfluenceBackend(
        url="https://wiki.example.com", token="tok", space="TEST", dry_run=True
    )
    b.write_page("concepts/foo.md", "# Foo\n\nContent.")
    captured = capsys.readouterr()
    assert "[DRY-RUN]" in captured.out
    assert "Concepts Foo" in captured.out


def test_confluence_deploy_dry_run_lists_pages(tmp_path, capsys):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "index.md").write_text("# Index")
    (wiki / "page-a.md").write_text("# Page A")
    b = ConfluenceBackend(
        url="https://wiki.example.com", token="tok", space="TEST", dry_run=True
    )
    b.deploy(wiki)
    captured = capsys.readouterr()
    assert "[DRY-RUN]" in captured.out
    assert "2 pages" in captured.out


@resp_mock.activate
def test_confluence_write_page_creates_new_page():
    # Page does not exist — empty search results
    resp_mock.add(
        resp_mock.GET,
        "https://wiki.example.com/rest/api/content",
        json={"results": []}, status=200,
    )
    # Create succeeds
    resp_mock.add(
        resp_mock.POST,
        "https://wiki.example.com/rest/api/content",
        json={"id": "99999", "title": "Concepts Foo"}, status=200,
    )
    b = ConfluenceBackend(
        url="https://wiki.example.com", token="tok", space="TEST", dry_run=False
    )
    b.write_page("concepts/foo.md", "# Foo\n\nContent.")
    # No exception = success


@resp_mock.activate
def test_confluence_write_page_raises_on_http_error():
    resp_mock.add(
        resp_mock.GET,
        "https://wiki.example.com/rest/api/content",
        json={"results": []}, status=200,
    )
    resp_mock.add(
        resp_mock.POST,
        "https://wiki.example.com/rest/api/content",
        status=401,
    )
    b = ConfluenceBackend(
        url="https://wiki.example.com", token="bad", space="TEST", dry_run=False
    )
    with pytest.raises(Exception):
        b.write_page("page.md", "# Page")
```

- [ ] **Step 2: Run — verify fail**

```bash
.venv/bin/pytest tests/deploy/test_confluence.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `src/llm_wiki/deploy/confluence.py`**

```python
from pathlib import Path

import requests

from llm_wiki.deploy.base import WikiBackend


class ConfluenceBackend(WikiBackend):
    """Confluence DC backend stub. dry_run=True by default — prints what would happen."""

    def __init__(
        self,
        url: str,
        token: str,
        space: str,
        parent_title: str = "",
        dry_run: bool = True,
    ) -> None:
        self.url = url.rstrip("/")
        self.token = token
        self.space = space
        self.parent_title = parent_title
        self.dry_run = dry_run

    @property
    def target_name(self) -> str:
        return "confluence"

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}

    def _title_from_path(self, rel_path: str) -> str:
        return Path(rel_path).stem.replace("-", " ").title()

    def _page_id(self, title: str) -> str | None:
        resp = requests.get(
            f"{self.url}/rest/api/content",
            headers=self._headers(),
            params={"title": title, "spaceKey": self.space, "expand": "version"},
            timeout=30,
        )
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            if results:
                return results[0]["id"]
        return None

    def write_page(self, rel_path: str, content: str) -> None:
        """Push page to Confluence. Prints dry-run message if self.dry_run=True."""
        title = self._title_from_path(rel_path)
        if self.dry_run:
            print(f"[DRY-RUN] Would push: {title}")
            return
        # Stub: wrap in Confluence preformatted macro
        storage = (
            "<ac:structured-macro ac:name='noformat'>"
            f"<ac:plain-text-body><![CDATA[{content}]]></ac:plain-text-body>"
            "</ac:structured-macro>"
        )
        page_id = self._page_id(title)
        if page_id is None:
            payload = {
                "type": "page",
                "title": title,
                "space": {"key": self.space},
                "body": {"storage": {"value": storage, "representation": "storage"}},
            }
            resp = requests.post(
                f"{self.url}/rest/api/content",
                json=payload,
                headers={**self._headers(), "Content-Type": "application/json"},
                timeout=30,
            )
            resp.raise_for_status()
        else:
            ver_resp = requests.get(
                f"{self.url}/rest/api/content/{page_id}",
                headers=self._headers(),
                params={"expand": "version"},
                timeout=30,
            )
            ver_resp.raise_for_status()
            version = ver_resp.json()["version"]["number"] + 1
            payload = {
                "type": "page",
                "title": title,
                "version": {"number": version},
                "body": {"storage": {"value": storage, "representation": "storage"}},
            }
            resp = requests.put(
                f"{self.url}/rest/api/content/{page_id}",
                json=payload,
                headers={**self._headers(), "Content-Type": "application/json"},
                timeout=30,
            )
            resp.raise_for_status()

    def delete_page(self, rel_path: str) -> None:
        title = self._title_from_path(rel_path)
        if self.dry_run:
            print(f"[DRY-RUN] Would delete: {title}")

    def deploy(self, wiki_dir: Path) -> None:
        """Sync all wiki pages to Confluence. dry_run=True prints a diff only."""
        pages = sorted(
            p for p in wiki_dir.rglob("*.md")
            if not any(part.startswith(".") for part in p.parts)
        )
        if self.dry_run:
            print(
                f"[DRY-RUN] Would sync {len(pages)} pages to Confluence space '{self.space}':"
            )
            for p in pages:
                print(f"  {p.relative_to(wiki_dir)}")
            print("Pass --no-dry-run to lwt deploy --target confluence to push.")
            return
        for page_path in pages:
            self.write_page(
                str(page_path.relative_to(wiki_dir)),
                page_path.read_text(encoding="utf-8"),
            )
```

- [ ] **Step 4: Run — verify pass**

```bash
.venv/bin/pytest tests/deploy/test_confluence.py -v
```

Expected: 5 PASSED.

- [ ] **Step 5: Commit**

```bash
git add src/llm_wiki/deploy/confluence.py tests/deploy/test_confluence.py
git commit -m "feat: add ConfluenceBackend stub (REST API push, dry_run=True)"
```

---

## Task 5: `lwt deploy` CLI subcommand

**Files:**
- Modify: `src/llm_wiki/cli.py` (append `deploy` command)
- Modify: `tests/test_cli.py` (append deploy tests)

- [ ] **Step 1: Write failing tests — append to `tests/test_cli.py`**

Add at the bottom of the existing `tests/test_cli.py`:

```python
# --- deploy tests ---
from unittest.mock import patch as mock_patch


def test_lwt_deploy_help():
    result = CliRunner().invoke(main, ["deploy", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "local" in result.output
    assert "docker" in result.output
    assert "confluence" in result.output


def test_lwt_deploy_local_starts_server(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "index.md").write_text("# Index")
    with mock_patch("subprocess.run"):
        result = CliRunner().invoke(main, [
            "deploy", "--target", "local",
            "--wiki-dir", str(wiki_dir),
        ])
    assert result.exit_code == 0


def test_lwt_deploy_confluence_dry_run(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "index.md").write_text("# Index")
    (wiki_dir / "page-a.md").write_text("# Page A")
    result = CliRunner().invoke(
        main,
        ["deploy", "--target", "confluence", "--wiki-dir", str(wiki_dir), "--dry-run"],
        env={"CONFLUENCE_URL": "https://wiki.example.com",
             "CONFLUENCE_TOKEN": "tok",
             "CONFLUENCE_SPACE": "TEST"},
    )
    assert result.exit_code == 0
    assert "DRY-RUN" in result.output
```

- [ ] **Step 2: Run — verify fail**

```bash
.venv/bin/pytest tests/test_cli.py -v -k "deploy"
```

Expected: errors — `deploy` command not defined yet.

- [ ] **Step 3: Append `deploy` command to `src/llm_wiki/cli.py`**

Append this block at the end of `src/llm_wiki/cli.py` (after the `lint` command):

```python
@main.command()
@click.option(
    "--target", required=True,
    type=click.Choice(["local", "docker", "confluence"]),
    help="Deployment target.",
)
@click.option("--wiki-dir", default="wiki", show_default=True)
@click.option("--port", default=None, type=int,
              help="Port override (default: 8080 for local, 8443 for docker).")
@click.option(
    "--mode", default="volume",
    type=click.Choice(["volume", "image"]), show_default=True,
    help="Docker mode: volume (live updates) or image (baked snapshot).",
)
@click.option(
    "--dry-run/--no-dry-run", default=True, show_default=True,
    help="Confluence: print diff without pushing (default: dry-run).",
)
def deploy(
    target: str, wiki_dir: str, port: int | None, mode: str, dry_run: bool
) -> None:
    """Deploy wiki/ to a target (local HTTP, Docker, or Confluence)."""
    import os
    wiki_path = Path(wiki_dir)
    if target == "local":
        from llm_wiki.deploy.local import LocalBackend
        backend = LocalBackend(wiki_path, port=port or 8080)
    elif target == "docker":
        from llm_wiki.deploy.docker import DockerBackend
        backend = DockerBackend(wiki_path, port=port or 8443, mode=mode)
    else:  # confluence
        from llm_wiki.deploy.confluence import ConfluenceBackend
        backend = ConfluenceBackend(
            url=os.environ.get("CONFLUENCE_URL", ""),
            token=os.environ.get("CONFLUENCE_TOKEN", ""),
            space=os.environ.get("CONFLUENCE_SPACE", ""),
            dry_run=dry_run,
        )
    backend.deploy(wiki_path)
```

- [ ] **Step 4: Run — verify pass**

```bash
.venv/bin/pytest tests/test_cli.py -v -k "deploy"
```

Expected: 3 PASSED.

- [ ] **Step 5: Commit**

```bash
git add src/llm_wiki/cli.py tests/test_cli.py
git commit -m "feat: add lwt deploy CLI subcommand (local/docker/confluence)"
```

---

## Task 6: Bundled data, AGENTS.md, skills/, `lwt init`

**Files:**
- Create: `src/llm_wiki/data/AGENTS.md`
- Create: `src/llm_wiki/data/CLAUDE.md`
- Create: `src/llm_wiki/data/.gitignore.template`
- Create: `src/llm_wiki/data/.lwt.env.example`
- Create: `src/llm_wiki/data/templates/default.md`
- Create: `src/llm_wiki/data/templates/entity.md`
- Create: `src/llm_wiki/data/templates/concept.md`
- Create: `src/llm_wiki/data/templates/source-summary.md`
- Create: `src/llm_wiki/data/templates/query-answer.md`
- Create: `AGENTS.md` (repo root)
- Create: `CLAUDE.md` (repo root)
- Create: `skills/query.md`
- Create: `skills/ingest.md`
- Create: `skills/lint.md`
- Create: `skills/deploy.md`
- Create: `src/llm_wiki/init.py`
- Modify: `src/llm_wiki/cli.py` (append `init` command)
- Modify: `tests/test_cli.py` (append init tests)

No TDD for text files. Create all data/skill files first, then implement init.py, then add init CLI and tests.

- [ ] **Step 1: Create `src/llm_wiki/data/AGENTS.md`**

```markdown
# LLM Wiki — Agent Schema

## What this is

A persistent, compounding knowledge base maintained entirely by the LLM.
You write and maintain all wiki pages. The human curates sources, asks
questions, and directs the analysis. You do the summarizing,
cross-referencing, filing, and bookkeeping.

## Directory conventions

| Directory    | Owner  | Rule                                            |
|--------------|--------|-------------------------------------------------|
| raw/         | human  | Immutable. Never modify, never delete.          |
| wiki/        | you    | You own this entirely. Create, update, maintain.|
| wiki/.tmp/   | lwt    | Temp ingest files. Read, never commit.          |
| templates/   | shared | Use the closest matching template for new pages.|
| output/      | lwt    | Generated. Do not hand-edit.                    |

## Tool surface

| Command                          | Purpose                                        |
|----------------------------------|------------------------------------------------|
| lwt ingest <file-or-url>         | Convert source → wiki/.tmp/<name>.md           |
| lwt ingest <file> --output -     | Convert small source → stdout (opt-in only)    |
| lwt search "<terms>"             | BM25 keyword search over wiki/ → ranked paths  |
| lwt lint --structural            | Structural check → wiki/lint-report.md         |
| lwt deploy --target <t>          | Push wiki/ to output target                    |
| lwt init <path>                  | Scaffold a new data repo                       |

## Workflows

### Query (you are the query engine — no CLI tool)

1. Read wiki/index.md to identify candidate pages
2. If wiki is large or index is ambiguous: run `lwt search "<key terms>"`
3. Read top candidates with Read/Grep tools
4. Synthesize answer with [[wiki-page]] citations
5. Ask user: "Worth filing this as a wiki page?"
6. If yes: write wiki/queries/<slug>.md using query-answer.md template
7. Update wiki/index.md, append to wiki/log.md

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

### Lint

1. Run: `lwt lint --structural`
2. Read wiki/lint-report.md — work through findings top to bottom
3. Fix structural issues first (broken links, orphans, missing pages)
4. Semantic lint: for flagged pages, read page + check source frontmatter lineage
5. Flag contradictions, stale claims, unresolvable gaps to user
6. Append to wiki/log.md: `## [YYYY-MM-DD] lint | <finding count> findings`

### Deploy

1. Confirm target with user before running
2. Run: `lwt deploy --target <local|docker|confluence> [options]`
3. Confluence is stub — dry-run only unless user confirms --no-dry-run

## Wiki page conventions

- Every page uses a template from templates/
- Every page has YAML frontmatter with traceability fields
- Every page footer: lwt version, git hash, date, template name
- Cross-links: [[page-name]] syntax
- wiki/index.md: updated on every write, one line per page with summary
- wiki/log.md: append-only, entries prefixed `## [YYYY-MM-DD] <op> | <title>`

## Schema evolution

This file is a living contract. Propose additions when you discover conventions
that work well. Human approves. Changes are git commits, not chat messages.
```

- [ ] **Step 2: Create `src/llm_wiki/data/CLAUDE.md`**

```markdown
# LLM Wiki — Claude Code Configuration

@path skills/query.md
@path skills/ingest.md
@path skills/lint.md
@path skills/deploy.md

---

<!-- Full AGENTS.md content follows. To customise, edit this file directly. -->

# LLM Wiki — Agent Schema

## What this is

A persistent, compounding knowledge base maintained entirely by the LLM.
You write and maintain all wiki pages. The human curates sources, asks
questions, and directs the analysis. You do the summarizing,
cross-referencing, filing, and bookkeeping.

## Directory conventions

| Directory    | Owner  | Rule                                            |
|--------------|--------|-------------------------------------------------|
| raw/         | human  | Immutable. Never modify, never delete.          |
| wiki/        | you    | You own this entirely. Create, update, maintain.|
| wiki/.tmp/   | lwt    | Temp ingest files. Read, never commit.          |
| templates/   | shared | Use the closest matching template for new pages.|
| output/      | lwt    | Generated. Do not hand-edit.                    |

## Tool surface

| Command                          | Purpose                                        |
|----------------------------------|------------------------------------------------|
| lwt ingest <file-or-url>         | Convert source → wiki/.tmp/<name>.md           |
| lwt ingest <file> --output -     | Convert small source → stdout (opt-in only)    |
| lwt search "<terms>"             | BM25 keyword search over wiki/ → ranked paths  |
| lwt lint --structural            | Structural check → wiki/lint-report.md         |
| lwt deploy --target <t>          | Push wiki/ to output target                    |
| lwt init <path>                  | Scaffold a new data repo                       |

## Workflows

### Query (you are the query engine — no CLI tool)

1. Read wiki/index.md to identify candidate pages
2. If wiki is large or index is ambiguous: run `lwt search "<key terms>"`
3. Read top candidates with Read/Grep tools
4. Synthesize answer with [[wiki-page]] citations
5. Ask user: "Worth filing this as a wiki page?"
6. If yes: write wiki/queries/<slug>.md using query-answer.md template
7. Update wiki/index.md, append to wiki/log.md

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

### Lint

1. Run: `lwt lint --structural`
2. Read wiki/lint-report.md — work through findings top to bottom
3. Fix structural issues first (broken links, orphans, missing pages)
4. Semantic lint: for flagged pages, read page + check source frontmatter lineage
5. Flag contradictions, stale claims, unresolvable gaps to user
6. Append to wiki/log.md: `## [YYYY-MM-DD] lint | <finding count> findings`

### Deploy

1. Confirm target with user before running
2. Run: `lwt deploy --target <local|docker|confluence> [options]`
3. Confluence is stub — dry-run only unless user confirms --no-dry-run

## Wiki page conventions

- Every page uses a template from templates/
- Every page has YAML frontmatter with traceability fields
- Every page footer: lwt version, git hash, date, template name
- Cross-links: [[page-name]] syntax
- wiki/index.md: updated on every write, one line per page with summary
- wiki/log.md: append-only, entries prefixed `## [YYYY-MM-DD] <op> | <title>`

## Schema evolution

This file is a living contract. Propose additions when you discover conventions
that work well. Human approves. Changes are git commits, not chat messages.
```

- [ ] **Step 3: Create `src/llm_wiki/data/.gitignore.template`**

```
# llm-wiki data repo — generated by lwt init
wiki/.tmp/
wiki/.lwt_cache/
output/
.lwt.env
__pycache__/
*.pyc
.DS_Store
```

- [ ] **Step 4: Create `src/llm_wiki/data/.lwt.env.example`**

```bash
# Copy this file to .lwt.env and fill in your credentials.
# .lwt.env is gitignored — never commit real tokens.

CONFLUENCE_URL=https://confluence.example.com
CONFLUENCE_TOKEN=your-personal-access-token-here
CONFLUENCE_SPACE=MYSPACE
CONFLUENCE_PARENT=Wiki Home

DOCKER_PORT=8443
LOCAL_PORT=8080
```

- [ ] **Step 5: Create `src/llm_wiki/data/templates/default.md`**

```markdown
---
title: ""
template: default.md
sources: []
lwt-version: ""
lwt-git-hash: ""
created-at: ""
---

# Page Title

*One-line summary of what this page covers.*

## Overview

## Details

## Related

---
*Generated by llm-wiki-tools · template: default.md*
```

- [ ] **Step 6: Create `src/llm_wiki/data/templates/entity.md`**

```markdown
---
title: ""
template: entity.md
entity-type: ""     # person | system | product | organisation | other
sources: []
lwt-version: ""
lwt-git-hash: ""
created-at: ""
---

# Entity Name

**Type:** *(person | system | product | organisation | other)*
**Also known as:** *(aliases if any)*

## Description

## Key Facts

## Relationships

- [[related-entity]] — *describe relationship*

## Source References

---
*Generated by llm-wiki-tools · template: entity.md*
```

- [ ] **Step 7: Create `src/llm_wiki/data/templates/concept.md`**

```markdown
---
title: ""
template: concept.md
sources: []
lwt-version: ""
lwt-git-hash: ""
created-at: ""
---

# Concept Name

*One-line definition.*

## Explanation

## Examples

## Connections

- [[related-concept]] — *how they relate*

## Open Questions

## Source References

---
*Generated by llm-wiki-tools · template: concept.md*
```

- [ ] **Step 8: Create `src/llm_wiki/data/templates/source-summary.md`**

```markdown
---
title: ""
template: source-summary.md
source: ""
source-sha: ""
ingest-command: ""
ingest-backend: ""
lwt-version: ""
lwt-git-hash: ""
ingested-at: ""
---

# Source Title

**Source:** `raw/filename.ext`
**Ingested:** YYYY-MM-DD
**Backend:** *(pdftotext | pandoc | ...)*

## Summary

*2–4 sentence overview of what this source contains.*

## Key Points

- Point 1
- Point 2

## Entities Mentioned

- [[entity-name]] — *brief note*

## Concepts Covered

- [[concept-name]] — *brief note*

## Contradictions / Updates

*Note any claims that contradict or update existing wiki pages.*

---
*Generated by llm-wiki-tools · template: source-summary.md*
```

- [ ] **Step 9: Create `src/llm_wiki/data/templates/query-answer.md`**

```markdown
---
title: ""
template: query-answer.md
query: ""
sources-consulted: []
lwt-version: ""
lwt-git-hash: ""
filed-at: ""
---

# Query: Question Text

*Filed answer — originally asked YYYY-MM-DD.*

## Answer

## Sources Consulted

- [[wiki-page]] — *what it contributed*

## Caveats

*What this answer might be missing or where it could be wrong.*

---
*Generated by llm-wiki-tools · template: query-answer.md*
```

- [ ] **Step 10: Create `skills/query.md`** in the repo root (`/path/to/llm-wiki-tools/skills/query.md`)

```markdown
# Query Workflow Skill

## When to use

When a user asks a question against the wiki.

## Decision tree by wiki size

- **< 50 pages:** Read wiki/index.md, identify candidates, use Read tool directly.
- **50–200 pages:** Run `lwt search "<key terms>"` first, then Read top results.
- **> 200 pages:** Run `lwt search "<key terms>"` + `Grep` for exact matches.

## Steps

1. Read `wiki/index.md` — scan for relevant pages by title and summary
2. If index is large or ambiguous: `lwt search "<key terms>" --wiki-dir wiki`
3. Read top candidate pages with Read/Grep tools
4. Synthesize answer with `[[wiki-page]]` citations
5. Ask user: "Worth filing this as a wiki page?"

## When to file answers back

File if the answer:
- Synthesizes across 3+ wiki pages
- Makes a comparison or analysis the user will want again
- Reveals a connection not explicit in any single page
- Answers a question that will recur

**Do NOT file:** one-sentence lookups, navigation answers, ephemeral status questions.

## Filing a query answer

1. Write `wiki/queries/<slug>.md` using `templates/query-answer.md`
2. Set `query:` frontmatter to the original question
3. Update `wiki/index.md` — add one-line entry under Queries
4. Append to `wiki/log.md`: `## [YYYY-MM-DD] query | <question summary>`
```

- [ ] **Step 11: Create `skills/ingest.md`**

```markdown
# Ingest Workflow Skill

## When to use

When a user adds a source to raw/ and asks you to process it.

## Native capability hints

| Format | Strategy |
|--------|----------|
| PDF | Try `lwt ingest` first. For complex layouts, use native vision (Read tool on PDF path). |
| Web URL | Try `lwt ingest <url>` first. For JS-heavy pages trafilatura misses, fetch natively. |
| DOCX / PPTX | Always use `lwt ingest` — binary formats, no native support. |
| MD / TXT | `lwt ingest` or Read directly — both work. |
| Confluence page | `lwt ingest <rest-api-url>` — requires CONFLUENCE_TOKEN in .lwt.env. |

## Steps

1. Run: `lwt ingest <file-or-url> --wiki-dir wiki`
2. Read the summary output (path, lines, sections, backend)
3. **Small doc (< 200 lines):** read full temp file in one pass
4. **Large doc (200–500 lines):** read in chunks using offset/limit
5. **Very large doc (> 500 lines):** dispatch sub-agents per section, then synthesize
6. Discuss key takeaways with user before writing anything
7. Select template: `source-summary.md` for ingested sources
8. Write/update wiki pages — copy traceability frontmatter from temp file header
9. Typical scope: 1 source-summary page + 3–10 entity/concept updates
10. Update `wiki/index.md`, append to `wiki/log.md`:
    `## [YYYY-MM-DD] ingest | <source title>`

## Traceability frontmatter

Copy these fields from the temp file header to every wiki page you write:

```yaml
source: raw/filename.ext
source-sha: "a3f9c12b"
ingest-command: "lwt ingest raw/filename.ext"
ingest-backend: "pdf.pdftotext"
lwt-version: "0.1.0"
lwt-git-hash: "abc1234"
ingested-at: "2026-04-15T09:00:00Z"
```

For pages updated by multiple ingests, use a `sources:` list.
```

- [ ] **Step 12: Create `skills/lint.md`**

```markdown
# Lint Workflow Skill

## When to use

When the user asks you to health-check or clean up the wiki.

## Phase 1: Structural lint (automated)

Run: `lwt lint --structural --wiki-dir wiki`

This writes `wiki/lint-report.md` with `file:line: [type] message` findings.

Fix order:
1. **broken_link** — page links to non-existent page → create page or fix link
2. **missing_page** — index.md references non-existent page → same fix
3. **orphan** — page has no inbound links → add link from related page, or delete

Re-run `lwt lint --structural` to verify zero findings.

## Phase 2: Semantic lint (LLM judgment)

Only run on pages flagged by structural lint or pages you have reason to doubt.

For each flagged page:
1. Read the wiki page
2. Read source pages listed in its `source:` / `sources:` frontmatter
3. Compare claims against source content
4. Flag contradictions, stale claims, or missing coverage to user

**Do not make semantic changes without reporting to the user first.**

## Completing lint

Append to `wiki/log.md`:
`## [YYYY-MM-DD] lint | <N> structural findings fixed, <M> semantic issues flagged`
```

- [ ] **Step 13: Create `skills/deploy.md`**

```markdown
# Deploy Workflow Skill

## When to use

When the user asks you to deploy or serve the wiki externally.

## Always confirm before deploying

Ask the user which target and confirm before running. For Confluence, always
confirm `--no-dry-run` explicitly — the default is dry-run.

## Target reference

### Local HTTP server

```bash
lwt deploy --target local --wiki-dir wiki [--port 8080]
```

Detects mkdocs → grip → stdlib http.server (priority order). Blocking — runs until Ctrl-C.

### Docker

```bash
# Volume mode (live updates — wiki/ on disk):
lwt deploy --target docker --wiki-dir wiki --mode volume [--port 8443]

# Image mode (baked snapshot):
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

- [ ] **Step 14: Copy AGENTS.md and CLAUDE.md to repo root**

```bash
cp src/llm_wiki/data/AGENTS.md AGENTS.md
cp src/llm_wiki/data/CLAUDE.md CLAUDE.md
```

- [ ] **Step 15: Implement `src/llm_wiki/init.py`**

```python
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

- [ ] **Step 16: Append `init` command to `src/llm_wiki/cli.py`**

Append this block at the end of `src/llm_wiki/cli.py`:

```python
@main.command(name="init")
@click.argument("path", default=".")
@click.option("--name", default="my-wiki", show_default=True,
              help="Human-readable name for this wiki.")
def init_cmd(path: str, name: str) -> None:
    """Scaffold a new llm-wiki data repository."""
    from llm_wiki.init import scaffold_data_repo
    target = Path(path)
    scaffold_data_repo(target, name=name)
    click.echo(f"Initialized wiki at {target.resolve()}")
    click.echo(f"  raw/              — drop source files here")
    click.echo(f"  wiki/             — LLM-maintained markdown pages")
    click.echo(f"  templates/        — page templates")
    click.echo(f"  AGENTS.md         — agent schema (edit to customize)")
    click.echo(f"  CLAUDE.md         — Claude Code configuration")
    click.echo(f"  .lwt.env.example  — copy to .lwt.env and fill in credentials")
```

- [ ] **Step 17: Append init tests to `tests/test_cli.py`**

```python
# --- init tests ---

def test_lwt_init_help():
    result = CliRunner().invoke(main, ["init", "--help"])
    assert result.exit_code == 0
    assert "--name" in result.output


def test_lwt_init_creates_structure(tmp_path):
    result = CliRunner().invoke(main, [
        "init", str(tmp_path / "mywiki"), "--name", "Test Wiki",
    ])
    assert result.exit_code == 0, result.output
    wiki_path = tmp_path / "mywiki"
    assert (wiki_path / "raw").is_dir()
    assert (wiki_path / "wiki").is_dir()
    assert (wiki_path / "templates").is_dir()
    assert (wiki_path / "output").is_dir()
    assert (wiki_path / "AGENTS.md").exists()
    assert (wiki_path / "CLAUDE.md").exists()
    assert (wiki_path / ".gitignore").exists()
    assert (wiki_path / ".lwt.env.example").exists()


def test_lwt_init_creates_all_templates(tmp_path):
    CliRunner().invoke(main, ["init", str(tmp_path / "wiki")])
    templates = tmp_path / "wiki" / "templates"
    for name in ["default.md", "entity.md", "concept.md",
                 "source-summary.md", "query-answer.md"]:
        assert (templates / name).exists(), f"Missing template: {name}"


def test_lwt_init_index_contains_name(tmp_path):
    CliRunner().invoke(main, [
        "init", str(tmp_path / "wiki"), "--name", "My Project",
    ])
    index = (tmp_path / "wiki" / "wiki" / "index.md").read_text()
    assert "My Project" in index


def test_lwt_init_gitignore_excludes_tmp(tmp_path):
    CliRunner().invoke(main, ["init", str(tmp_path / "wiki")])
    gitignore = (tmp_path / "wiki" / ".gitignore").read_text()
    assert "wiki/.tmp/" in gitignore
```

- [ ] **Step 18: Run init tests**

```bash
.venv/bin/pytest tests/test_cli.py -v -k "init"
```

Expected: 5 PASSED.

- [ ] **Step 19: Run full test suite**

```bash
.venv/bin/pytest --tb=short -q
```

Expected: all tests pass.

- [ ] **Step 20: Smoke test `lwt init`**

```bash
.venv/bin/lwt init /tmp/smoke-init --name "Smoke Test Wiki"
ls /tmp/smoke-init/
ls /tmp/smoke-init/templates/
cat /tmp/smoke-init/AGENTS.md | head -5
```

Expected: directory structure created, templates present, AGENTS.md readable.

- [ ] **Step 21: Commit everything**

```bash
git add src/llm_wiki/data/ src/llm_wiki/init.py src/llm_wiki/cli.py \
    skills/ AGENTS.md CLAUDE.md tests/test_cli.py
git commit -m "feat: add bundled data, templates, AGENTS.md, skills/, and lwt init"
```

---

## Self-Review Checklist

- [ ] All tests pass: `.venv/bin/pytest -q`
- [ ] `lwt --help` shows: ingest, search, lint, deploy, init
- [ ] `lwt deploy --help` shows: --target local/docker/confluence, --port, --mode, --dry-run
- [ ] `lwt init --help` shows: --name option
- [ ] `lwt init /tmp/test` creates: raw/, wiki/, templates/ (5 files), AGENTS.md, CLAUDE.md, .gitignore, .lwt.env.example
- [ ] `WikiBackend` cannot be instantiated directly (raises TypeError)
- [ ] `LocalBackend._server_command()` prefers mkdocs → grip → http.server
- [ ] `DockerBackend` defaults to mode="volume", image="nginx:alpine"
- [ ] `ConfluenceBackend` defaults to dry_run=True
- [ ] `init.py` uses `_DATA_DIR = Path(__file__).parent / "data"` — no importlib.resources
- [ ] AGENTS.md and CLAUDE.md in repo root match bundled copies in src/llm_wiki/data/
- [ ] Skills reference correct CLI commands: `lwt lint --structural` (not `lwt lint structural`)
- [ ] No TBD, TODO, or placeholder text in any implementation file
- [ ] `ConfluenceBackend.deploy()` dry-run output says "2 pages" (not "2 page") — check plural

---

## What's Next

Plan 2 completes the llm-wiki-tools package. The full `lwt` CLI is operational:

```
lwt ingest <source>           — convert to wiki/.tmp/
lwt search "<terms>"          — BM25 keyword search
lwt lint --structural         — find broken links, orphans, missing pages
lwt deploy --target local     — serve wiki/ locally
lwt deploy --target docker    — run in Docker container
lwt deploy --target confluence — dry-run push to Confluence
lwt init <path>               — scaffold a new data repo
```

Next step: create the first data repo with `lwt init llm-wiki-myproject`, drop sources into `raw/`, and start ingesting.

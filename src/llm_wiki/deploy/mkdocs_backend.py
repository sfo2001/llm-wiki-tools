import subprocess
import sys
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

    def _ensure_mkdocs_yml(self, repo_dir: Path | None = None) -> Path:
        """Write mkdocs.yml beside wiki/ if absent. Returns its path."""
        if repo_dir is None:
            repo_dir = self._repo_dir
        mkdocs_yml = repo_dir / "mkdocs.yml"
        if not mkdocs_yml.exists():
            repo_dir.mkdir(parents=True, exist_ok=True)
            mkdocs_yml.write_text(
                _MKDOCS_YML_TEMPLATE.format(name=self.name), encoding="utf-8"
            )
        return mkdocs_yml

    @staticmethod
    def _mkdocs_bin() -> str:
        """Return mkdocs co-located with current Python (venv-aware), or 'mkdocs'."""
        candidate = Path(sys.executable).parent / "mkdocs"
        return str(candidate) if candidate.exists() else "mkdocs"

    def deploy(self, wiki_dir: Path) -> None:
        repo_dir = wiki_dir.parent
        mkdocs_yml = self._ensure_mkdocs_yml(repo_dir)
        mkdocs = self._mkdocs_bin()
        if self.build:
            cmd = [
                mkdocs, "build",
                "--config-file", str(mkdocs_yml),
                "--clean",
            ]
        else:
            cmd = [
                mkdocs, "serve",
                "--config-file", str(mkdocs_yml),
                "--dev-addr", f"0.0.0.0:{self.port}",
            ]
        print(f"{'Building' if self.build else 'Serving'}: {' '.join(cmd)}")
        import os
        env = {**os.environ, "WATCHDOG_USE_POLLING": "1"}
        subprocess.run(cmd, check=True, cwd=str(repo_dir), env=env)

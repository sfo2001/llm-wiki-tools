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


class FilesystemBackend(WikiBackend):
    """WikiBackend whose write/delete operate on a local wiki directory.

    Subclasses must set self.wiki_dir in __init__ and implement target_name + deploy.
    """

    wiki_dir: Path

    def write_page(self, rel_path: str, content: str) -> None:
        path = self.wiki_dir / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def delete_page(self, rel_path: str) -> None:
        path = self.wiki_dir / rel_path
        if path.exists():
            path.unlink()

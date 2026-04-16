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

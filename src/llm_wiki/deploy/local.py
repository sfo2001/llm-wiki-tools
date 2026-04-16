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

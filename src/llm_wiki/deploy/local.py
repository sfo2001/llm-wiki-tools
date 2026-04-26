import shutil
import subprocess
from pathlib import Path

from llm_wiki.deploy.base import FilesystemBackend


class LocalBackend(FilesystemBackend):
    """Serve wiki/ via local HTTP. write_page() writes directly to filesystem."""

    def __init__(self, wiki_dir: Path, port: int = 8080, bind: str = "127.0.0.1") -> None:
        self.wiki_dir = wiki_dir
        self.port = port
        self.bind = bind

    @property
    def target_name(self) -> str:
        return "local"

    def _server_command(self, wiki_dir: Path | None = None) -> list[str]:
        """Return the best available HTTP server command."""
        target_dir = wiki_dir if wiki_dir is not None else self.wiki_dir
        if shutil.which("mkdocs"):
            return [
                "mkdocs", "serve",
                "--dev-addr", f"{self.bind}:{self.port}",
                "--docs-dir", str(target_dir),
            ]
        if shutil.which("grip"):
            return ["grip", str(target_dir), f"{self.bind}:{self.port}"]
        return [
            "python3", "-m", "http.server", str(self.port),
            "--bind", self.bind,
            "--directory", str(target_dir),
        ]

    def deploy(self, wiki_dir: Path) -> None:
        cmd = self._server_command(wiki_dir)
        print(f"Starting local server: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)

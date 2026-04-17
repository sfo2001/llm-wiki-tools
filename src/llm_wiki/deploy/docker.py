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
    ) -> None:
        self.wiki_dir = wiki_dir
        self.port = port
        self.mode = mode
        self.image = image
        self.tag = tag

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
        # NOTE: Image mode requires a Dockerfile at wiki_dir/Dockerfile.
        # Generate one or place it there before running lwt deploy --mode image.
        if not (wiki_dir / "Dockerfile").exists():
            raise FileNotFoundError(
                f"Docker image mode requires a Dockerfile at {wiki_dir / 'Dockerfile'}.\n"
                "Place a Dockerfile in your wiki directory, or use --mode volume instead."
            )
        return [
            "docker", "build",
            "-t", self.tag,
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

import re
import shutil
import subprocess
from pathlib import Path

SUPPORTED = {".md", ".txt", ".rst", ".org", ".text"}
FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)


def _strip_frontmatter(text: str) -> str:
    return FRONTMATTER_RE.sub("", text, count=1).lstrip()


def _try_pandoc_rst_org(path: Path) -> str | None:
    if not shutil.which("pandoc"):
        return None
    fmt = "org" if path.suffix == ".org" else "rst"
    result = subprocess.run(
        ["pandoc", "--from", fmt, "--to", "markdown", str(path)],
        capture_output=True, text=True,
    )
    md = result.stdout.strip()
    return md if result.returncode == 0 and md else None


def convert_raw(path: Path) -> tuple[str, str]:
    """Convert text-based source to (backend_name, markdown_body)."""
    if path.suffix.lower() not in SUPPORTED:
        raise ValueError(f"Unsupported raw format: {path.suffix}")

    if path.suffix.lower() in {".rst", ".org"}:
        md = _try_pandoc_rst_org(path)
        if md:
            return f"raw.pandoc-{path.suffix.lstrip('.')}", md

    text = path.read_text(encoding="utf-8", errors="replace")
    text = _strip_frontmatter(text)
    return "raw.passthrough", text

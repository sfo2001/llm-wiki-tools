import shutil
import subprocess
from pathlib import Path


def _try_pandoc(path: Path) -> str | None:
    if not shutil.which("pandoc"):
        return None
    result = subprocess.run(
        ["pandoc", "--from", "docx", "--to", "markdown", str(path)],
        capture_output=True, text=True,
    )
    md = result.stdout.strip()
    return md if result.returncode == 0 and md else None


def _try_python_docx(path: Path) -> str | None:
    try:
        from docx import Document
        doc = Document(str(path))
        lines = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            style = para.style.name.lower()
            if "heading 1" in style:
                lines.append(f"# {text}")
            elif "heading 2" in style:
                lines.append(f"## {text}")
            elif "heading 3" in style:
                lines.append(f"### {text}")
            else:
                lines.append(text)
        return "\n\n".join(lines) if lines else None
    except Exception:
        return None


def convert_docx(path: Path) -> tuple[str, str]:
    """Convert DOCX to (backend_name, markdown_body)."""
    md = _try_pandoc(path)
    if md:
        return "docx.pandoc", md
    md = _try_python_docx(path)
    if md:
        return "docx.python-docx", md
    raise RuntimeError(f"All DOCX backends failed for {path}")

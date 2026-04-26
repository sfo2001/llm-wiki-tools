import logging
import re
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def _text_to_md(text: str) -> str:
    """Wrap plain text as minimal markdown."""
    lines = text.strip().splitlines()
    if not lines:
        return ""
    first = lines[0].strip()
    if first and len(first) < 120 and not first.endswith("."):
        return f"# {first}\n" + "\n".join(lines[1:])
    return "\n".join(lines)


def _try_pdftotext(path: Path) -> str | None:
    if not shutil.which("pdftotext"):
        return None
    result = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        capture_output=True, text=True,
    )
    text = result.stdout.strip()
    return text if result.returncode == 0 and text else None


def _try_pdfminer(path: Path) -> str | None:
    try:
        from pdfminer.high_level import extract_text
        text = extract_text(str(path)).strip()
        return text if text else None
    except Exception as e:
        logger.debug("pdfminer failed for %s: %s", path, e)
        return None


def _try_pypdf(path: Path) -> str | None:
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        pages = [p.extract_text() or "" for p in reader.pages]
        text = "\n\n".join(p for p in pages if p.strip())
        return text if text else None
    except Exception as e:
        logger.debug("pypdf failed for %s: %s", path, e)
        return None


def convert_pdf(path: Path) -> tuple[str, str]:
    """Convert PDF to (backend_name, markdown_body). Tries three backends."""
    text = _try_pdftotext(path)
    if text:
        return "pdf.pdftotext", _text_to_md(text)
    text = _try_pdfminer(path)
    if text:
        return "pdf.pdfminer", _text_to_md(text)
    text = _try_pypdf(path)
    if text:
        return "pdf.pypdf", _text_to_md(text)
    raise RuntimeError(f"All PDF backends failed for {path}")

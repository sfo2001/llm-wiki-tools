# llm-wiki-tools Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `llm-wiki-tools` — a Python package (`lwt`) that converts binary sources to markdown, indexes wiki pages with BM25, and runs structural lint checks, so an LLM coding assistant can maintain a persistent knowledge wiki.

**Architecture:** Flat format handlers (no ABC) convert sources to markdown and write to `wiki/.tmp/`. A BM25 index over `wiki/` supports keyword search (cache stored as JSON — no pickle). A structural linter scans for broken links, orphans, and missing pages. A `click`-based CLI wires everything into `lwt ingest`, `lwt search`, and `lwt lint`.

**Tech Stack:** Python 3.11+, click, rank-bm25, trafilatura, pypdf, pdfminer.six, python-docx, python-pptx, pyyaml, pytest, hatchling

**Note:** This is Plan 1 of 2. Plan 2 covers WikiBackend deploy targets + AGENTS.md + skills + `lwt init`.

---

## File Map

| File | Responsibility |
|------|---------------|
| `pyproject.toml` | Package metadata, dependencies, `lwt` entry point |
| `src/llm_wiki/__init__.py` | `__version__`, `__git_hash__` |
| `src/llm_wiki/common.py` | `IngestMeta`, `write_tmp()`, `inject_footer()`, `compute_sha()` |
| `src/llm_wiki/log.py` | `append_log()` — append-only wiki/log.md writer |
| `src/llm_wiki/ingest/pdf.py` | `convert_pdf(path) -> (backend, md)` |
| `src/llm_wiki/ingest/docx.py` | `convert_docx(path) -> (backend, md)` |
| `src/llm_wiki/ingest/pptx.py` | `convert_pptx(path) -> (backend, md)` |
| `src/llm_wiki/ingest/web.py` | `convert_web(url) -> (backend, md)` |
| `src/llm_wiki/ingest/raw.py` | `convert_raw(path) -> (backend, md)` |
| `src/llm_wiki/ingest/confluence.py` | `convert_confluence(url, token) -> (backend, md)` |
| `src/llm_wiki/ingest/__init__.py` | `ingest_source(src, wiki_dir, output, command) -> IngestResult` |
| `src/llm_wiki/search/bm25.py` | `BM25Index` class — build, search, JSON cache |
| `src/llm_wiki/search/__init__.py` | `search(wiki_dir, query, n) -> list[SearchResult]` |
| `src/llm_wiki/lint/structural.py` | `Finding`, check functions |
| `src/llm_wiki/lint/report.py` | `format_report(findings) -> str` |
| `src/llm_wiki/lint/__init__.py` | `lint_structural(wiki_dir) -> list[Finding]` |
| `src/llm_wiki/cli.py` | `click` CLI — `ingest`, `search`, `lint` subcommands |
| `tests/conftest.py` | Shared fixtures: tmp wiki dir, sample files |
| `tests/test_common.py` | Tests for common.py |
| `tests/test_log.py` | Tests for log.py |
| `tests/ingest/test_pdf.py` | Tests for pdf.py |
| `tests/ingest/test_docx.py` | Tests for docx.py |
| `tests/ingest/test_pptx.py` | Tests for pptx.py |
| `tests/ingest/test_web.py` | Tests for web.py |
| `tests/ingest/test_raw.py` | Tests for raw.py |
| `tests/ingest/test_dispatch.py` | Tests for ingest/__init__.py |
| `tests/search/test_bm25.py` | Tests for BM25 index + search |
| `tests/lint/test_structural.py` | Tests for structural lint checks |
| `tests/test_cli.py` | CLI integration tests via click.testing |

---

## Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `src/llm_wiki/__init__.py`
- Create: `src/llm_wiki/ingest/__init__.py` (empty stub)
- Create: `src/llm_wiki/search/__init__.py` (empty stub)
- Create: `src/llm_wiki/lint/__init__.py` (empty stub)
- Create: `tests/__init__.py`
- Create: `tests/ingest/__init__.py`
- Create: `tests/search/__init__.py`
- Create: `tests/lint/__init__.py`
- Create: `.gitignore`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "llm-wiki-tools"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "click>=8.1",
    "pyyaml>=6.0",
    "rank-bm25>=0.2.2",
    "trafilatura>=1.9",
    "html2text>=2024.2",
    "requests>=2.31",
    "pypdf>=4.0",
    "pdfminer.six>=20231228",
    "python-docx>=1.1",
    "python-pptx>=0.6",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "fpdf2>=2.7",
    "responses>=0.25",
]

[project.scripts]
lwt = "llm_wiki.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/llm_wiki"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create `src/llm_wiki/__init__.py`**

```python
import subprocess
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("llm-wiki-tools")
except PackageNotFoundError:
    __version__ = "dev"


def _get_git_hash() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=__file__,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


__git_hash__ = _get_git_hash()
```

- [ ] **Step 3: Create empty `__init__.py` files**

Create empty files at:
- `src/llm_wiki/ingest/__init__.py`
- `src/llm_wiki/search/__init__.py`
- `src/llm_wiki/lint/__init__.py`
- `tests/__init__.py`
- `tests/ingest/__init__.py`
- `tests/search/__init__.py`
- `tests/lint/__init__.py`

- [ ] **Step 4: Create `.gitignore`**

```
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
dist/
.venv/
wiki/.tmp/
wiki/.lwt_cache/
.lwt.env
```

- [ ] **Step 5: Install in dev mode**

```bash
pip install -e ".[dev]"
```

Expected: `lwt --help` prints usage without errors.

- [ ] **Step 6: Commit**

```bash
git init
git add pyproject.toml src/ tests/ .gitignore
git commit -m "feat: scaffold llm-wiki-tools package"
```

---

## Task 2: `common.py` — shared utilities

**Files:**
- Create: `src/llm_wiki/common.py`
- Create: `tests/test_common.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_common.py
import pytest
from pathlib import Path
from llm_wiki.common import compute_sha, inject_footer, write_tmp


def test_compute_sha_is_8_chars(tmp_path):
    f = tmp_path / "file.txt"
    f.write_bytes(b"hello")
    sha = compute_sha(f)
    assert len(sha) == 8
    assert sha.isalnum()


def test_compute_sha_deterministic(tmp_path):
    f = tmp_path / "file.txt"
    f.write_bytes(b"hello")
    assert compute_sha(f) == compute_sha(f)


def test_inject_footer_appended():
    content = "# Title\n\nBody text."
    result = inject_footer(content, version="1.0.0", git_hash="abc1234",
                           template="entity.md", date="2026-04-15")
    assert result.startswith("# Title")
    assert "llm-wiki-tools v1.0.0" in result
    assert "abc1234" in result
    assert "entity.md" in result
    assert "2026-04-15" in result


def test_write_tmp_creates_file(tmp_path):
    wiki_dir = tmp_path / "wiki"
    source = tmp_path / "report.pdf"
    source.write_bytes(b"%PDF-fake")

    out_path, summary = write_tmp(
        wiki_dir=wiki_dir,
        source_path=source,
        backend_name="pdf.pdftotext",
        markdown_body="# Report\n\nContent here.",
        ingest_command="lwt ingest report.pdf",
    )

    assert out_path.exists()
    assert "---" in out_path.read_text()
    assert "pdf.pdftotext" in out_path.read_text()
    assert "# Report" in out_path.read_text()


def test_write_tmp_summary_keys(tmp_path):
    wiki_dir = tmp_path / "wiki"
    source = tmp_path / "doc.pdf"
    source.write_bytes(b"%PDF")

    _, summary = write_tmp(
        wiki_dir=wiki_dir,
        source_path=source,
        backend_name="pdf.pypdf",
        markdown_body="# Title\n\n## Section\n\nText.",
        ingest_command="lwt ingest doc.pdf",
    )

    assert "path" in summary
    assert "lines" in summary
    assert "sections" in summary
    assert "backend" in summary
    assert "source_sha" in summary
    assert summary["sections"] == 1  # one ## heading
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_common.py -v
```

Expected: `ImportError` — `common` not defined yet.

- [ ] **Step 3: Implement `src/llm_wiki/common.py`**

```python
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

from llm_wiki import __version__, __git_hash__


def compute_sha(path: Path) -> str:
    """Return first 8 hex chars of SHA-256 of file contents."""
    h = hashlib.sha256(path.read_bytes())
    return h.hexdigest()[:8]


def inject_footer(
    content: str,
    version: str,
    git_hash: str,
    template: str,
    date: str,
) -> str:
    """Append traceability footer to markdown content."""
    footer = (
        f"\n\n---\n"
        f"*Generated by llm-wiki-tools v{version} "
        f"(commit {git_hash}) · {date} · template: {template}*\n"
    )
    return content.rstrip() + footer


def write_tmp(
    wiki_dir: Path,
    source_path: Path,
    backend_name: str,
    markdown_body: str,
    ingest_command: str,
) -> tuple[Path, dict]:
    """Write converted markdown to wiki/.tmp/ with frontmatter.

    Returns (tmp_path, summary_dict).
    """
    tmp_dir = wiki_dir / ".tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    safe_name = re.sub(r"[^\w.\-]", "_", source_path.name)
    out_path = tmp_dir / f"{date_str}_{safe_name}.md"

    source_sha = compute_sha(source_path)
    ingested_at = datetime.now(timezone.utc).isoformat()

    meta = {
        "source": str(source_path),
        "source-sha": source_sha,
        "source-type": source_path.suffix.lstrip(".").lower(),
        "ingest-command": ingest_command,
        "ingest-backend": backend_name,
        "lwt-version": __version__,
        "lwt-git-hash": __git_hash__,
        "ingested-at": ingested_at,
    }

    frontmatter = yaml.dump(meta, default_flow_style=False, allow_unicode=True)
    full_content = f"---\n{frontmatter}---\n\n{markdown_body}"
    out_path.write_text(full_content, encoding="utf-8")

    lines = len(markdown_body.splitlines())
    sections = len(re.findall(r"^#{1,3} ", markdown_body, re.MULTILINE))

    return out_path, {
        "path": out_path,
        "lines": lines,
        "sections": sections,
        "backend": backend_name,
        "source_sha": source_sha,
    }
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_common.py -v
```

Expected: 5 PASSED.

- [ ] **Step 5: Commit**

```bash
git add src/llm_wiki/common.py tests/test_common.py
git commit -m "feat: add common utilities (write_tmp, inject_footer, compute_sha)"
```

---

## Task 3: `log.py` — append-only log writer

**Files:**
- Create: `src/llm_wiki/log.py`
- Create: `tests/test_log.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_log.py
from pathlib import Path
from llm_wiki.log import append_log


def test_append_log_creates_file(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    append_log(wiki_dir, operation="ingest", title="My Report")
    assert (wiki_dir / "log.md").exists()


def test_append_log_format(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    append_log(wiki_dir, operation="ingest", title="My Report")
    content = (wiki_dir / "log.md").read_text()
    assert "## [20" in content
    assert "ingest" in content
    assert "My Report" in content


def test_append_log_is_append_only(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    append_log(wiki_dir, operation="ingest", title="First")
    append_log(wiki_dir, operation="lint", title="Second")
    content = (wiki_dir / "log.md").read_text()
    assert "First" in content
    assert "Second" in content
    assert content.index("First") < content.index("Second")
```

- [ ] **Step 2: Run — verify fail**

```bash
pytest tests/test_log.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `src/llm_wiki/log.py`**

```python
from datetime import datetime, timezone
from pathlib import Path


def append_log(wiki_dir: Path, operation: str, title: str) -> None:
    """Append one entry to wiki/log.md in chronological order."""
    log_path = wiki_dir / "log.md"
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entry = f"\n## [{date_str}] {operation} | {title}\n"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(entry)
```

- [ ] **Step 4: Run — verify pass**

```bash
pytest tests/test_log.py -v
```

Expected: 3 PASSED.

- [ ] **Step 5: Commit**

```bash
git add src/llm_wiki/log.py tests/test_log.py
git commit -m "feat: add append-only log writer"
```

---

## Task 4: `ingest/pdf.py` — PDF to markdown

**Files:**
- Create: `src/llm_wiki/ingest/pdf.py`
- Create: `tests/ingest/test_pdf.py`
- Create: `tests/conftest.py` (shared fixtures)

- [ ] **Step 1: Create `tests/conftest.py`**

```python
# tests/conftest.py
import pytest
from pathlib import Path


@pytest.fixture
def sample_pdf(tmp_path) -> Path:
    """Minimal valid PDF with text content."""
    try:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.cell(200, 10, txt="Sample Report Title", ln=True)
        pdf.cell(200, 10, txt="This is sample body text for testing.", ln=True)
        path = tmp_path / "sample.pdf"
        pdf.output(str(path))
        return path
    except ImportError:
        pytest.skip("fpdf2 not installed")


@pytest.fixture
def sample_docx(tmp_path) -> Path:
    try:
        from docx import Document
        doc = Document()
        doc.add_heading("Sample Document Title", 0)
        doc.add_paragraph("This is body text.")
        path = tmp_path / "sample.docx"
        doc.save(str(path))
        return path
    except ImportError:
        pytest.skip("python-docx not installed")


@pytest.fixture
def sample_pptx(tmp_path) -> Path:
    try:
        from pptx import Presentation
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = "Slide One Title"
        slide.placeholders[1].text = "Bullet point one"
        path = tmp_path / "sample.pptx"
        prs.save(str(path))
        return path
    except ImportError:
        pytest.skip("python-pptx not installed")


@pytest.fixture
def wiki_dir(tmp_path) -> Path:
    """Minimal wiki with index and two linked pages (no broken links)."""
    d = tmp_path / "wiki"
    d.mkdir()
    (d / "index.md").write_text(
        "# Index\n\n- [[page-a]] — Page A summary\n- [[page-b]] — Page B summary\n"
    )
    (d / "page-a.md").write_text("# Page A\n\nLinks to [[page-b]].\n")
    (d / "page-b.md").write_text("# Page B\n\nNo outbound links.\n")
    return d
```

- [ ] **Step 2: Write failing tests**

```python
# tests/ingest/test_pdf.py
import pytest
from pathlib import Path
from unittest.mock import patch
from llm_wiki.ingest.pdf import convert_pdf


def test_convert_pdf_returns_tuple(sample_pdf):
    backend, md = convert_pdf(sample_pdf)
    assert isinstance(backend, str)
    assert isinstance(md, str)
    assert backend.startswith("pdf.")


def test_convert_pdf_markdown_not_empty(sample_pdf):
    _, md = convert_pdf(sample_pdf)
    assert len(md.strip()) > 0


def test_convert_pdf_falls_back_to_pypdf(sample_pdf):
    with patch("shutil.which", return_value=None):
        with patch("llm_wiki.ingest.pdf._try_pdfminer", return_value=None):
            backend, md = convert_pdf(sample_pdf)
    assert backend == "pdf.pypdf"
    assert len(md.strip()) > 0


def test_convert_pdf_raises_on_all_failures(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf at all")
    with patch("shutil.which", return_value=None):
        with patch("llm_wiki.ingest.pdf._try_pdfminer", return_value=None):
            with patch("llm_wiki.ingest.pdf._try_pypdf", return_value=None):
                with pytest.raises(RuntimeError, match="All PDF backends failed"):
                    convert_pdf(bad)
```

- [ ] **Step 3: Run — verify fail**

```bash
pytest tests/ingest/test_pdf.py -v
```

Expected: `ImportError` — module not defined.

- [ ] **Step 4: Implement `src/llm_wiki/ingest/pdf.py`**

```python
import re
import shutil
import subprocess
from pathlib import Path


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
    except Exception:
        return None


def _try_pypdf(path: Path) -> str | None:
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        pages = [p.extract_text() or "" for p in reader.pages]
        text = "\n\n".join(p for p in pages if p.strip())
        return text if text else None
    except Exception:
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
```

- [ ] **Step 5: Run — verify pass**

```bash
pytest tests/ingest/test_pdf.py -v
```

Expected: 4 PASSED.

- [ ] **Step 6: Commit**

```bash
git add src/llm_wiki/ingest/pdf.py tests/ingest/test_pdf.py tests/conftest.py
git commit -m "feat: add PDF ingest handler with pdftotext/pdfminer/pypdf fallbacks"
```

---

## Task 5: `ingest/docx.py` — DOCX to markdown

**Files:**
- Create: `src/llm_wiki/ingest/docx.py`
- Create: `tests/ingest/test_docx.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/ingest/test_docx.py
from unittest.mock import patch
from llm_wiki.ingest.docx import convert_docx


def test_convert_docx_returns_tuple(sample_docx):
    backend, md = convert_docx(sample_docx)
    assert isinstance(backend, str)
    assert backend.startswith("docx.")
    assert isinstance(md, str)


def test_convert_docx_contains_text(sample_docx):
    _, md = convert_docx(sample_docx)
    assert len(md.strip()) > 0


def test_convert_docx_falls_back_to_python_docx(sample_docx):
    with patch("shutil.which", return_value=None):
        backend, md = convert_docx(sample_docx)
    assert backend == "docx.python-docx"
    assert len(md.strip()) > 0
```

- [ ] **Step 2: Run — verify fail**

```bash
pytest tests/ingest/test_docx.py -v
```

- [ ] **Step 3: Implement `src/llm_wiki/ingest/docx.py`**

```python
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
```

- [ ] **Step 4: Run — verify pass**

```bash
pytest tests/ingest/test_docx.py -v
```

Expected: 3 PASSED.

- [ ] **Step 5: Commit**

```bash
git add src/llm_wiki/ingest/docx.py tests/ingest/test_docx.py
git commit -m "feat: add DOCX ingest handler with pandoc/python-docx fallback"
```

---

## Task 6: `ingest/pptx.py` — PPTX to markdown

**Files:**
- Create: `src/llm_wiki/ingest/pptx.py`
- Create: `tests/ingest/test_pptx.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/ingest/test_pptx.py
from unittest.mock import patch
from llm_wiki.ingest.pptx import convert_pptx


def test_convert_pptx_returns_tuple(sample_pptx):
    backend, md = convert_pptx(sample_pptx)
    assert isinstance(backend, str)
    assert backend.startswith("pptx.")
    assert isinstance(md, str)


def test_convert_pptx_contains_text(sample_pptx):
    _, md = convert_pptx(sample_pptx)
    assert len(md.strip()) > 0


def test_convert_pptx_falls_back_to_python_pptx(sample_pptx):
    with patch("shutil.which", return_value=None):
        backend, md = convert_pptx(sample_pptx)
    assert backend == "pptx.python-pptx"
    assert "Slide One Title" in md
```

- [ ] **Step 2: Run — verify fail**

```bash
pytest tests/ingest/test_pptx.py -v
```

- [ ] **Step 3: Implement `src/llm_wiki/ingest/pptx.py`**

```python
import shutil
import subprocess
from pathlib import Path


def _try_pandoc(path: Path) -> str | None:
    if not shutil.which("pandoc"):
        return None
    result = subprocess.run(
        ["pandoc", "--from", "pptx", "--to", "markdown", str(path)],
        capture_output=True, text=True,
    )
    md = result.stdout.strip()
    return md if result.returncode == 0 and md else None


def _try_python_pptx(path: Path) -> str | None:
    try:
        from pptx import Presentation
        prs = Presentation(str(path))
        slides = []
        for i, slide in enumerate(prs.slides, start=1):
            title = ""
            bullets: list[str] = []
            for shape in slide.shapes:
                if not shape.has_text_frame:
                    continue
                text = shape.text_frame.text.strip()
                if not text:
                    continue
                if shape == slide.shapes.title:
                    title = text
                else:
                    bullets.append(text)
            heading = f"## Slide {i}: {title}" if title else f"## Slide {i}"
            body = "\n".join(f"- {b}" for b in bullets if b)
            slides.append(f"{heading}\n\n{body}" if body else heading)
        return "\n\n".join(slides) if slides else None
    except Exception:
        return None


def convert_pptx(path: Path) -> tuple[str, str]:
    """Convert PPTX to (backend_name, markdown_body)."""
    md = _try_pandoc(path)
    if md:
        return "pptx.pandoc", md
    md = _try_python_pptx(path)
    if md:
        return "pptx.python-pptx", md
    raise RuntimeError(f"All PPTX backends failed for {path}")
```

- [ ] **Step 4: Run — verify pass**

```bash
pytest tests/ingest/test_pptx.py -v
```

Expected: 3 PASSED.

- [ ] **Step 5: Commit**

```bash
git add src/llm_wiki/ingest/pptx.py tests/ingest/test_pptx.py
git commit -m "feat: add PPTX ingest handler with pandoc/python-pptx fallback"
```

---

## Task 7: `ingest/raw.py` — markdown/text passthrough

**Files:**
- Create: `src/llm_wiki/ingest/raw.py`
- Create: `tests/ingest/test_raw.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/ingest/test_raw.py
import pytest
from pathlib import Path
from llm_wiki.ingest.raw import convert_raw


def test_convert_md_passthrough(tmp_path):
    f = tmp_path / "notes.md"
    f.write_text("# Notes\n\nSome content.", encoding="utf-8")
    backend, md = convert_raw(f)
    assert backend == "raw.passthrough"
    assert "# Notes" in md
    assert "Some content." in md


def test_convert_txt(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("Plain text content.\nSecond line.", encoding="utf-8")
    backend, md = convert_raw(f)
    assert backend == "raw.passthrough"
    assert "Plain text content." in md


def test_convert_raw_strips_existing_frontmatter(tmp_path):
    f = tmp_path / "page.md"
    f.write_text("---\ntitle: Old\n---\n\n# Body\n\nContent.", encoding="utf-8")
    _, md = convert_raw(f)
    assert "title: Old" not in md
    assert "# Body" in md


def test_convert_raw_unsupported_extension_raises(tmp_path):
    f = tmp_path / "data.xlsx"
    f.write_bytes(b"binary")
    with pytest.raises(ValueError, match="Unsupported raw format"):
        convert_raw(f)
```

- [ ] **Step 2: Run — verify fail**

```bash
pytest tests/ingest/test_raw.py -v
```

- [ ] **Step 3: Implement `src/llm_wiki/ingest/raw.py`**

```python
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
```

- [ ] **Step 4: Run — verify pass**

```bash
pytest tests/ingest/test_raw.py -v
```

Expected: 4 PASSED.

- [ ] **Step 5: Commit**

```bash
git add src/llm_wiki/ingest/raw.py tests/ingest/test_raw.py
git commit -m "feat: add raw/text passthrough ingest handler"
```

---

## Task 8: `ingest/web.py` — URL to markdown

**Files:**
- Create: `src/llm_wiki/ingest/web.py`
- Create: `tests/ingest/test_web.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/ingest/test_web.py
import pytest
import responses as resp_mock
from unittest.mock import patch
from llm_wiki.ingest.web import convert_web

SAMPLE_HTML = """<html><body>
<h1>Article Title</h1>
<p>This is the article body with enough text to pass extraction.</p>
</body></html>"""


@resp_mock.activate
def test_convert_web_with_requests_fallback():
    resp_mock.add(resp_mock.GET, "http://example.com/article",
                  body=SAMPLE_HTML, status=200, content_type="text/html")
    with patch("llm_wiki.ingest.web._try_trafilatura", return_value=None):
        backend, md = convert_web("http://example.com/article")
    assert backend == "web.requests-html2text"
    assert len(md.strip()) > 0


def test_convert_web_uses_trafilatura_when_available():
    with patch("llm_wiki.ingest.web._try_trafilatura",
               return_value="# Title\n\nBody text from trafilatura."):
        backend, md = convert_web("http://example.com/article")
    assert backend == "web.trafilatura"
    assert "trafilatura" in md


@resp_mock.activate
def test_convert_web_raises_on_http_error():
    resp_mock.add(resp_mock.GET, "http://example.com/missing", status=404)
    with patch("llm_wiki.ingest.web._try_trafilatura", return_value=None):
        with pytest.raises(RuntimeError, match="HTTP 404"):
            convert_web("http://example.com/missing")
```

- [ ] **Step 2: Run — verify fail**

```bash
pytest tests/ingest/test_web.py -v
```

- [ ] **Step 3: Implement `src/llm_wiki/ingest/web.py`**

```python
import requests


def _try_trafilatura(url: str) -> str | None:
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None
        result = trafilatura.extract(downloaded, output_format="markdown",
                                     include_links=False)
        return result.strip() if result and result.strip() else None
    except Exception:
        return None


def _try_requests(url: str) -> str:
    """Fetch URL and convert HTML to markdown via html2text."""
    import html2text
    response = requests.get(url, timeout=30,
                            headers={"User-Agent": "lwt/1.0 (llm-wiki-tools)"})
    if response.status_code != 200:
        raise RuntimeError(f"HTTP {response.status_code} fetching {url}")
    h = html2text.HTML2Text()
    h.ignore_links = True
    h.ignore_images = True
    return h.handle(response.text).strip()


def convert_web(url: str) -> tuple[str, str]:
    """Convert URL to (backend_name, markdown_body)."""
    md = _try_trafilatura(url)
    if md:
        return "web.trafilatura", md
    md = _try_requests(url)
    return "web.requests-html2text", md
```

- [ ] **Step 4: Run — verify pass**

```bash
pytest tests/ingest/test_web.py -v
```

Expected: 3 PASSED.

- [ ] **Step 5: Commit**

```bash
git add src/llm_wiki/ingest/web.py tests/ingest/test_web.py
git commit -m "feat: add web URL ingest handler with trafilatura/requests fallback"
```

---

## Task 9: `ingest/confluence.py` — Confluence page to markdown

**Files:**
- Create: `src/llm_wiki/ingest/confluence.py`
- Create: `tests/ingest/test_confluence.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/ingest/test_confluence.py
import pytest
import responses as resp_mock
from llm_wiki.ingest.confluence import convert_confluence

CONFLUENCE_RESPONSE = {
    "title": "My Confluence Page",
    "body": {"storage": {"value": "<h1>Page Title</h1><p>Body content here.</p>"}}
}


@resp_mock.activate
def test_convert_confluence_page_by_id():
    resp_mock.add(
        resp_mock.GET,
        "https://wiki.example.com/rest/api/content/12345",
        json=CONFLUENCE_RESPONSE, status=200,
    )
    backend, md = convert_confluence(
        url="https://wiki.example.com/rest/api/content/12345",
        token="mytoken",
    )
    assert backend == "confluence.rest-api"
    assert len(md.strip()) > 0


@resp_mock.activate
def test_convert_confluence_raises_on_auth_failure():
    resp_mock.add(
        resp_mock.GET,
        "https://wiki.example.com/rest/api/content/12345",
        status=401,
    )
    with pytest.raises(RuntimeError, match="Confluence API error 401"):
        convert_confluence(
            url="https://wiki.example.com/rest/api/content/12345",
            token="badtoken",
        )
```

- [ ] **Step 2: Run — verify fail**

```bash
pytest tests/ingest/test_confluence.py -v
```

- [ ] **Step 3: Implement `src/llm_wiki/ingest/confluence.py`**

```python
import html2text
import requests


def convert_confluence(url: str, token: str) -> tuple[str, str]:
    """Fetch a Confluence DC page via REST API and convert to markdown.

    url: REST API URL, e.g. https://wiki.example.com/rest/api/content/12345
    token: Confluence personal access token
    """
    api_url = url if "?expand=" in url else f"{url}?expand=body.storage"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    response = requests.get(api_url, headers=headers, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(
            f"Confluence API error {response.status_code} for {url}"
        )

    data = response.json()
    storage_html = data.get("body", {}).get("storage", {}).get("value", "")
    title = data.get("title", "")

    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True
    body_md = h.handle(storage_html).strip()

    md = f"# {title}\n\n{body_md}" if title else body_md
    return "confluence.rest-api", md
```

- [ ] **Step 4: Run — verify pass**

```bash
pytest tests/ingest/test_confluence.py -v
```

Expected: 2 PASSED.

- [ ] **Step 5: Commit**

```bash
git add src/llm_wiki/ingest/confluence.py tests/ingest/test_confluence.py
git commit -m "feat: add Confluence DC REST API ingest handler"
```

---

## Task 10: `ingest/__init__.py` — dispatch + `IngestResult`

**Files:**
- Modify: `src/llm_wiki/ingest/__init__.py`
- Create: `tests/ingest/test_dispatch.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/ingest/test_dispatch.py
import pytest
from pathlib import Path
from llm_wiki.ingest import ingest_source, IngestResult


def test_ingest_pdf_writes_tmp(tmp_path, sample_pdf):
    wiki_dir = tmp_path / "wiki"
    result = ingest_source(
        source=sample_pdf,
        wiki_dir=wiki_dir,
        ingest_command=f"lwt ingest {sample_pdf}",
    )
    assert isinstance(result, IngestResult)
    assert result.path.exists()
    assert result.lines > 0
    assert result.backend.startswith("pdf.")


def test_ingest_raw_md(tmp_path):
    wiki_dir = tmp_path / "wiki"
    source = tmp_path / "notes.md"
    source.write_text("# Notes\n\nContent.", encoding="utf-8")
    result = ingest_source(
        source=source,
        wiki_dir=wiki_dir,
        ingest_command="lwt ingest notes.md",
    )
    assert result.path.exists()
    assert result.backend == "raw.passthrough"


def test_ingest_stdout_mode(tmp_path, sample_pdf, capsys):
    wiki_dir = tmp_path / "wiki"
    result = ingest_source(
        source=sample_pdf,
        wiki_dir=wiki_dir,
        ingest_command=f"lwt ingest {sample_pdf}",
        output="-",
    )
    captured = capsys.readouterr()
    assert "---" in captured.out
    assert result.path is None   # no file written in stdout mode


def test_ingest_unknown_extension_raises(tmp_path):
    wiki_dir = tmp_path / "wiki"
    source = tmp_path / "data.xyz"
    source.write_bytes(b"binary")
    with pytest.raises(ValueError, match="Unsupported source format"):
        ingest_source(source=source, wiki_dir=wiki_dir,
                      ingest_command="lwt ingest data.xyz")
```

- [ ] **Step 2: Run — verify fail**

```bash
pytest tests/ingest/test_dispatch.py -v
```

- [ ] **Step 3: Implement `src/llm_wiki/ingest/__init__.py`**

```python
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from llm_wiki import __git_hash__, __version__
from llm_wiki.common import compute_sha, write_tmp
from llm_wiki.ingest import confluence, docx, pdf, pptx, raw, web

EXTENSION_MAP = {
    ".pdf": pdf.convert_pdf,
    ".docx": docx.convert_docx,
    ".pptx": pptx.convert_pptx,
    ".md": raw.convert_raw,
    ".txt": raw.convert_raw,
    ".text": raw.convert_raw,
    ".rst": raw.convert_raw,
    ".org": raw.convert_raw,
}


@dataclass
class IngestResult:
    path: Path | None   # None when output="-" (stdout mode)
    lines: int
    sections: int
    backend: str
    source_sha: str


def ingest_source(
    source: str | Path,
    wiki_dir: Path,
    ingest_command: str,
    output: str | None = None,
) -> IngestResult:
    """Dispatch source to correct handler; write to wiki/.tmp/ or stdout."""
    source_str = str(source)
    is_url = source_str.startswith("http://") or source_str.startswith("https://")

    if is_url:
        if "/rest/api/content/" in source_str:
            import os
            token = os.environ.get("CONFLUENCE_TOKEN", "")
            backend_name, md_body = confluence.convert_confluence(source_str, token)
        else:
            backend_name, md_body = web.convert_web(source_str)
        # synthetic path for URL sources (write URL bytes so compute_sha works)
        safe = re.sub(r"[^\w]", "_", source_str)[:60]
        tmp_dir = wiki_dir / ".tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        source_path = tmp_dir / f"{safe}.url"
        source_path.write_bytes(source_str.encode())
    else:
        source_path = Path(source)
        ext = source_path.suffix.lower()
        handler = EXTENSION_MAP.get(ext)
        if handler is None:
            raise ValueError(
                f"Unsupported source format: {ext!r}. "
                f"Supported: {sorted(EXTENSION_MAP)}"
            )
        backend_name, md_body = handler(source_path)

    if output == "-":
        source_sha = compute_sha(source_path)
        meta = {
            "source": str(source_path),
            "source-sha": source_sha,
            "ingest-command": ingest_command,
            "ingest-backend": backend_name,
            "lwt-version": __version__,
            "lwt-git-hash": __git_hash__,
            "ingested-at": datetime.now(timezone.utc).isoformat(),
        }
        fm = yaml.dump(meta, default_flow_style=False, allow_unicode=True)
        sys.stdout.write(f"---\n{fm}---\n\n{md_body}\n")
        lines = len(md_body.splitlines())
        sections = len(re.findall(r"^#{1,3} ", md_body, re.MULTILINE))
        return IngestResult(path=None, lines=lines, sections=sections,
                            backend=backend_name, source_sha=source_sha)

    out_path, summary = write_tmp(
        wiki_dir=wiki_dir,
        source_path=source_path,
        backend_name=backend_name,
        markdown_body=md_body,
        ingest_command=ingest_command,
    )
    return IngestResult(
        path=out_path,
        lines=summary["lines"],
        sections=summary["sections"],
        backend=summary["backend"],
        source_sha=summary["source_sha"],
    )
```

- [ ] **Step 4: Run all ingest tests**

```bash
pytest tests/ingest/ -v
```

Expected: all PASSED.

- [ ] **Step 5: Commit**

```bash
git add src/llm_wiki/ingest/__init__.py tests/ingest/test_dispatch.py
git commit -m "feat: add ingest dispatch + IngestResult (all format handlers wired)"
```

---

## Task 11: `search/bm25.py` — BM25 index with JSON cache

**Files:**
- Create: `src/llm_wiki/search/bm25.py`
- Modify: `src/llm_wiki/search/__init__.py`
- Create: `tests/search/test_bm25.py`

Note: cache uses JSON (not pickle) — stores tokenized corpus, rebuilds `BM25Okapi` on load.

- [ ] **Step 1: Write failing tests**

```python
# tests/search/test_bm25.py
import pytest
from pathlib import Path
from llm_wiki.search import search, SearchResult
from llm_wiki.search.bm25 import BM25Index


def test_bm25_build_and_search(wiki_dir):
    idx = BM25Index(wiki_dir)
    idx.build()
    results = idx.search("page links", n=5)
    assert len(results) > 0
    assert all(isinstance(r, SearchResult) for r in results)


def test_search_returns_ranked_results(wiki_dir):
    results = search(wiki_dir, "links page", n=10)
    assert len(results) >= 1
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_search_result_fields(wiki_dir):
    results = search(wiki_dir, "page", n=5)
    r = results[0]
    assert isinstance(r.path, Path)
    assert isinstance(r.score, float)
    assert isinstance(r.snippet, str)


def test_search_cache_created(wiki_dir):
    search(wiki_dir, "page", n=5)
    cache = wiki_dir / ".lwt_cache" / "bm25_cache.json"
    assert cache.exists()


def test_search_cache_is_valid_json(wiki_dir):
    import json
    search(wiki_dir, "page", n=5)
    cache = wiki_dir / ".lwt_cache" / "bm25_cache.json"
    data = json.loads(cache.read_text())
    assert "pages" in data
    assert "corpus" in data


def test_search_empty_query_returns_empty(wiki_dir):
    assert search(wiki_dir, "", n=5) == []
```

- [ ] **Step 2: Run — verify fail**

```bash
pytest tests/search/test_bm25.py -v
```

- [ ] **Step 3: Implement `src/llm_wiki/search/bm25.py`**

```python
import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SearchResult:
    path: Path
    score: float
    snippet: str


def _tokenize(text: str) -> list[str]:
    """Lowercase, strip markdown syntax, split on whitespace."""
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\[\[.*?\]\]", "", text)
    text = re.sub(r"\*+|`+|_+|---+", " ", text)
    return text.lower().split()


def _extract_snippet(text: str, query_tokens: list[str], length: int = 120) -> str:
    lower = text.lower()
    for token in query_tokens:
        idx = lower.find(token)
        if idx != -1:
            start = max(0, idx - 40)
            end = min(len(text), idx + length)
            return "..." + text[start:end].replace("\n", " ").strip() + "..."
    return text[:length].replace("\n", " ").strip() + "..."


class BM25Index:
    def __init__(self, wiki_dir: Path) -> None:
        self.wiki_dir = wiki_dir
        self._cache_path = wiki_dir / ".lwt_cache" / "bm25_cache.json"
        self._pages: list[Path] = []
        self._texts: list[str] = []
        self._index = None

    def _md_files(self) -> list[Path]:
        return sorted(
            p for p in self.wiki_dir.rglob("*.md")
            if not any(part.startswith(".") for part in p.parts)
        )

    def _needs_rebuild(self) -> bool:
        if not self._cache_path.exists():
            return True
        cache_mtime = self._cache_path.stat().st_mtime
        return any(
            p.stat().st_mtime > cache_mtime for p in self._md_files()
        )

    def build(self) -> None:
        from rank_bm25 import BM25Okapi

        self._pages = self._md_files()
        self._texts = [
            p.read_text(encoding="utf-8", errors="replace") for p in self._pages
        ]
        tokenized = [_tokenize(t) for t in self._texts]
        self._index = BM25Okapi(tokenized)

        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_data = {
            "pages": [str(p) for p in self._pages],
            "corpus": tokenized,
        }
        self._cache_path.write_text(
            json.dumps(cache_data, ensure_ascii=False), encoding="utf-8"
        )

    def _load_cache(self) -> None:
        from rank_bm25 import BM25Okapi

        data = json.loads(self._cache_path.read_text(encoding="utf-8"))
        self._pages = [Path(p) for p in data["pages"]]
        self._texts = [
            p.read_text(encoding="utf-8", errors="replace")
            for p in self._pages
            if p.exists()
        ]
        self._index = BM25Okapi(data["corpus"])

    def _ensure_ready(self) -> None:
        if self._needs_rebuild():
            self.build()
        elif self._index is None:
            self._load_cache()

    def search(self, query: str, n: int = 10) -> list[SearchResult]:
        if not query.strip():
            return []
        self._ensure_ready()
        tokens = _tokenize(query)
        if not tokens:
            return []
        scores = self._index.get_scores(tokens)
        ranked = sorted(
            zip(scores, self._pages, self._texts),
            key=lambda x: x[0],
            reverse=True,
        )
        results = []
        for score, path, text in ranked[:n]:
            if score <= 0:
                break
            results.append(SearchResult(
                path=path,
                score=float(score),
                snippet=_extract_snippet(text, tokens),
            ))
        return results
```

- [ ] **Step 4: Implement `src/llm_wiki/search/__init__.py`**

```python
from pathlib import Path
from llm_wiki.search.bm25 import BM25Index, SearchResult


def search(wiki_dir: Path, query: str, n: int = 10) -> list[SearchResult]:
    """Search wiki pages using BM25. Returns ranked list of SearchResult."""
    return BM25Index(wiki_dir).search(query, n=n)


__all__ = ["search", "SearchResult"]
```

- [ ] **Step 5: Run — verify pass**

```bash
pytest tests/search/test_bm25.py -v
```

Expected: 6 PASSED.

- [ ] **Step 6: Commit**

```bash
git add src/llm_wiki/search/ tests/search/test_bm25.py
git commit -m "feat: add BM25 search with JSON cache (mtime invalidation)"
```

---

## Task 12: Structural linter

**Files:**
- Create: `src/llm_wiki/lint/structural.py`
- Create: `src/llm_wiki/lint/report.py`
- Modify: `src/llm_wiki/lint/__init__.py`
- Create: `tests/lint/test_structural.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/lint/test_structural.py
import pytest
from pathlib import Path
from llm_wiki.lint import lint_structural
from llm_wiki.lint.structural import Finding
from llm_wiki.lint.report import format_report


@pytest.fixture
def broken_wiki(tmp_path):
    d = tmp_path / "wiki"
    d.mkdir()
    (d / "index.md").write_text(
        "# Index\n\n- [[page-a]] — exists\n- [[missing-page]] — gone\n"
    )
    (d / "page-a.md").write_text(
        "# Page A\n\nSee [[broken-link]] and [[missing-page]].\n"
    )
    (d / "orphan.md").write_text("# Orphan\n\nNo one links here.\n")
    return d


def test_detects_broken_link(broken_wiki):
    findings = lint_structural(broken_wiki)
    broken = [f for f in findings if f.issue_type == "broken_link"]
    assert any("broken-link" in f.message for f in broken)


def test_detects_orphan_page(broken_wiki):
    findings = lint_structural(broken_wiki)
    orphans = [f for f in findings if f.issue_type == "orphan"]
    assert any("orphan" in str(f.path) for f in orphans)


def test_detects_missing_page_in_index(broken_wiki):
    findings = lint_structural(broken_wiki)
    missing = [f for f in findings if f.issue_type == "missing_page"]
    assert any("missing-page" in f.message for f in missing)


def test_clean_wiki_has_no_findings(wiki_dir):
    assert lint_structural(wiki_dir) == []


def test_format_report_has_file_colon_line(broken_wiki):
    findings = lint_structural(broken_wiki)
    report = format_report(findings)
    assert ":" in report


def test_format_report_empty_on_clean(wiki_dir):
    report = format_report(lint_structural(wiki_dir))
    assert "No issues found" in report
```

- [ ] **Step 2: Run — verify fail**

```bash
pytest tests/lint/test_structural.py -v
```

- [ ] **Step 3: Implement `src/llm_wiki/lint/structural.py`**

```python
import re
from dataclasses import dataclass
from pathlib import Path

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


@dataclass
class Finding:
    path: Path
    line: int
    issue_type: str   # "broken_link" | "orphan" | "missing_page"
    message: str


def _slug(name: str) -> str:
    return name.strip().lower().replace(" ", "-")


def _page_map(wiki_dir: Path) -> dict[str, Path]:
    return {
        p.stem.lower(): p
        for p in wiki_dir.rglob("*.md")
        if not any(part.startswith(".") for part in p.parts)
    }


def _iter_pages(wiki_dir: Path):
    for path in wiki_dir.rglob("*.md"):
        if not any(part.startswith(".") for part in path.parts):
            yield path, path.read_text(encoding="utf-8", errors="replace")


def check_broken_links(wiki_dir: Path) -> list[Finding]:
    pages = _page_map(wiki_dir)
    findings = []
    for path, content in _iter_pages(wiki_dir):
        for lineno, line in enumerate(content.splitlines(), start=1):
            for m in WIKILINK_RE.finditer(line):
                if _slug(m.group(1)) not in pages:
                    findings.append(Finding(
                        path=path, line=lineno,
                        issue_type="broken_link",
                        message=f"broken link: [[{m.group(1)}]] — page not found",
                    ))
    return findings


def check_orphans(wiki_dir: Path) -> list[Finding]:
    pages = _page_map(wiki_dir)
    referenced: set[str] = set()
    for _, content in _iter_pages(wiki_dir):
        for m in WIKILINK_RE.finditer(content):
            referenced.add(_slug(m.group(1)))
    skip = {"index", "log", "lint-report"}
    return [
        Finding(path=path, line=0, issue_type="orphan",
                message=f"orphan page: no inbound links to [[{slug}]]")
        for slug, path in pages.items()
        if slug not in referenced and slug not in skip
    ]


def check_missing_pages(wiki_dir: Path) -> list[Finding]:
    index = wiki_dir / "index.md"
    if not index.exists():
        return []
    pages = _page_map(wiki_dir)
    findings = []
    for lineno, line in enumerate(
        index.read_text(encoding="utf-8").splitlines(), start=1
    ):
        for m in WIKILINK_RE.finditer(line):
            if _slug(m.group(1)) not in pages:
                findings.append(Finding(
                    path=index, line=lineno,
                    issue_type="missing_page",
                    message=f"index references missing page: [[{m.group(1)}]]",
                ))
    return findings
```

- [ ] **Step 4: Implement `src/llm_wiki/lint/report.py`**

```python
from llm_wiki.lint.structural import Finding


def format_report(findings: list[Finding]) -> str:
    if not findings:
        return "No issues found.\n"
    lines = [
        f"{f.path}:{f.line}: [{f.issue_type}] {f.message}"
        for f in sorted(findings, key=lambda x: (str(x.path), x.line))
    ]
    return "\n".join(lines) + "\n"
```

- [ ] **Step 5: Implement `src/llm_wiki/lint/__init__.py`**

```python
from pathlib import Path
from llm_wiki.lint.structural import (
    Finding,
    check_broken_links,
    check_missing_pages,
    check_orphans,
)


def lint_structural(wiki_dir: Path) -> list[Finding]:
    return (
        check_broken_links(wiki_dir)
        + check_orphans(wiki_dir)
        + check_missing_pages(wiki_dir)
    )


__all__ = ["lint_structural", "Finding"]
```

- [ ] **Step 6: Run — verify pass**

```bash
pytest tests/lint/test_structural.py -v
```

Expected: 6 PASSED.

- [ ] **Step 7: Commit**

```bash
git add src/llm_wiki/lint/ tests/lint/test_structural.py
git commit -m "feat: add structural linter (broken links, orphans, missing pages)"
```

---

## Task 13: `cli.py` — `click` CLI entry point

**Files:**
- Create: `src/llm_wiki/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli.py
from click.testing import CliRunner
from llm_wiki.cli import main


def test_lwt_help():
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "ingest" in result.output
    assert "search" in result.output
    assert "lint" in result.output


def test_lwt_ingest_help():
    result = CliRunner().invoke(main, ["ingest", "--help"])
    assert result.exit_code == 0
    assert "--output" in result.output


def test_lwt_ingest_raw_file(tmp_path):
    source = tmp_path / "notes.md"
    source.write_text("# Notes\n\nContent here.", encoding="utf-8")
    wiki_dir = tmp_path / "wiki"
    result = CliRunner().invoke(main, [
        "ingest", str(source), "--wiki-dir", str(wiki_dir),
    ])
    assert result.exit_code == 0, result.output
    assert "Ingested:" in result.output
    assert "Lines:" in result.output


def test_lwt_ingest_stdout_mode(tmp_path):
    source = tmp_path / "notes.md"
    source.write_text("# Notes\n\nContent.", encoding="utf-8")
    wiki_dir = tmp_path / "wiki"
    result = CliRunner().invoke(main, [
        "ingest", str(source), "--wiki-dir", str(wiki_dir), "--output", "-",
    ])
    assert result.exit_code == 0
    assert "---" in result.output


def test_lwt_search(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "page.md").write_text(
        "# Topic\n\nContent about widgets.", encoding="utf-8"
    )
    result = CliRunner().invoke(main, ["search", "widgets",
                                       "--wiki-dir", str(wiki_dir)])
    assert result.exit_code == 0
    assert "page.md" in result.output


def test_lwt_lint_clean_wiki(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "index.md").write_text("# Index\n\n- [[page-a]] — Page A\n")
    (wiki_dir / "page-a.md").write_text("# Page A\n\nContent.\n")
    result = CliRunner().invoke(main, ["lint", "--structural",
                                       "--wiki-dir", str(wiki_dir)])
    assert result.exit_code == 0
    assert "No issues found" in result.output


def test_lwt_lint_writes_report_and_exits_nonzero(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "index.md").write_text("# Index\n\n- [[missing]] — Gone\n")
    result = CliRunner().invoke(main, ["lint", "--structural",
                                       "--wiki-dir", str(wiki_dir)])
    assert result.exit_code != 0
    assert (wiki_dir / "lint-report.md").exists()
    assert "missing" in (wiki_dir / "lint-report.md").read_text()
```

- [ ] **Step 2: Run — verify fail**

```bash
pytest tests/test_cli.py -v
```

- [ ] **Step 3: Implement `src/llm_wiki/cli.py`**

```python
import sys
from pathlib import Path

import click

from llm_wiki import __version__
from llm_wiki.ingest import IngestResult, ingest_source
from llm_wiki.lint import lint_structural
from llm_wiki.lint.report import format_report
from llm_wiki.search import search


@click.group()
@click.version_option(__version__, prog_name="lwt")
def main() -> None:
    """llm-wiki-tools — LLM wiki maintenance toolchain."""


@main.command()
@click.argument("source")
@click.option("--wiki-dir", default="wiki", show_default=True)
@click.option("--output", default=None,
              help="Output path for temp file, or '-' for stdout.")
def ingest(source: str, wiki_dir: str, output: str | None) -> None:
    """Convert a source file or URL to markdown in wiki/.tmp/."""
    wiki_path = Path(wiki_dir)
    command = f"lwt ingest {source}" + (f" --output {output}" if output else "")
    result: IngestResult = ingest_source(
        source=source,
        wiki_dir=wiki_path,
        ingest_command=command,
        output=output,
    )
    if output == "-":
        return
    click.echo(f"Ingested:   {result.path}")
    click.echo(f"Lines:      {result.lines}")
    click.echo(f"Sections:   {result.sections}")
    click.echo(f"Backend:    {result.backend}")
    click.echo(f"Source-SHA: {result.source_sha}")


@main.command(name="search")
@click.argument("query")
@click.option("--wiki-dir", default="wiki", show_default=True)
@click.option("-n", default=10, show_default=True)
@click.option("--reindex", is_flag=True)
def search_cmd(query: str, wiki_dir: str, n: int, reindex: bool) -> None:
    """BM25 keyword search over wiki pages."""
    wiki_path = Path(wiki_dir)
    if reindex:
        from llm_wiki.search.bm25 import BM25Index
        BM25Index(wiki_path).build()
        click.echo("Index rebuilt.")
    results = search(wiki_path, query, n=n)
    if not results:
        click.echo("No results.")
        return
    for r in results:
        try:
            rel = r.path.relative_to(wiki_path)
        except ValueError:
            rel = r.path
        click.echo(f"{rel}\tscore={r.score:.1f}\t{r.snippet}")


@main.command()
@click.option("--structural", is_flag=True, required=True)
@click.option("--wiki-dir", default="wiki", show_default=True)
@click.option("--output", default=None)
def lint(structural: bool, wiki_dir: str, output: str | None) -> None:
    """Run structural lint checks over the wiki."""
    wiki_path = Path(wiki_dir)
    findings = lint_structural(wiki_path)
    report = format_report(findings)
    report_path = Path(output) if output else wiki_path / "lint-report.md"
    report_path.write_text(report, encoding="utf-8")
    click.echo(report.rstrip())
    if findings:
        click.echo(f"\nReport written to {report_path}")
        sys.exit(1)
```

- [ ] **Step 4: Run — verify pass**

```bash
pytest tests/test_cli.py -v
```

Expected: 7 PASSED.

- [ ] **Step 5: Run full suite**

```bash
pytest --tb=short -q
```

Expected: all tests pass.

- [ ] **Step 6: End-to-end smoke test**

```bash
echo "# Test\n\nSome content about widgets." > /tmp/test.md
lwt ingest /tmp/test.md --wiki-dir /tmp/smoke-wiki
lwt search "widgets" --wiki-dir /tmp/smoke-wiki
lwt lint --structural --wiki-dir /tmp/smoke-wiki
```

Expected: ingest prints summary, search finds page, lint prints "No issues found."

- [ ] **Step 7: Commit**

```bash
git add src/llm_wiki/cli.py tests/test_cli.py
git commit -m "feat: add lwt CLI (ingest, search, lint) — Plan 1 complete"
```

---

## Self-Review Checklist

- [ ] All tests pass: `pytest -q`
- [ ] `lwt --help` shows ingest, search, lint
- [ ] `IngestResult` fields: `path`, `lines`, `sections`, `backend`, `source_sha` — consistent everywhere
- [ ] `Finding` fields: `path`, `line`, `issue_type`, `message` — consistent everywhere
- [ ] `SearchResult` fields: `path`, `score`, `snippet` — consistent everywhere
- [ ] BM25 cache file is `bm25_cache.json` (JSON, not binary) — verified in test
- [ ] No `TBD`, `TODO`, or placeholder text in any implementation file
- [ ] `write_tmp()` is the only place that writes to `wiki/.tmp/` — ingest handlers never write files

---

## What's Next — Plan 2

Plan 2 covers:
1. `WikiBackend` ABC + `LocalBackend` + `DockerBackend` + `ConfluenceBackend` (stub)
2. `lwt deploy` CLI subcommand
3. `AGENTS.md` + `CLAUDE.md` (canonical schema)
4. `skills/query.md`, `skills/ingest.md`, `skills/lint.md`, `skills/deploy.md`
5. `lwt init` — scaffold a new data repo
6. Data repo `templates/` (default, entity, concept, source-summary, query-answer)

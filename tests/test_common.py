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

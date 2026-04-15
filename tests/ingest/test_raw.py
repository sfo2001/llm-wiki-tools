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

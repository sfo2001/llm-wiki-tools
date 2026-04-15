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

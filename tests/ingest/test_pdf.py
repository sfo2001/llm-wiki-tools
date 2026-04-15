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

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

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

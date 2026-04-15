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

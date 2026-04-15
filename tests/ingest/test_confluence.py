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

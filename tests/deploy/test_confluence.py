import pytest
import responses as resp_mock
from pathlib import Path
from llm_wiki.deploy.confluence import ConfluenceBackend


def test_confluence_target_name():
    b = ConfluenceBackend(url="https://wiki.example.com", token="tok", space="TEST")
    assert b.target_name == "confluence"


def test_escape_cdata_passthrough():
    assert ConfluenceBackend._escape_cdata("hello") == "hello"


def test_escape_cdata_splits_terminator():
    out = ConfluenceBackend._escape_cdata("foo ]]> bar")
    assert "]]>" not in out.replace("]]]]><![CDATA[>", "")
    assert out == "foo ]]]]><![CDATA[> bar"


def test_escape_cdata_handles_multiple_occurrences():
    out = ConfluenceBackend._escape_cdata("a ]]> b ]]> c")
    assert out.count("]]]]><![CDATA[>") == 2


@resp_mock.activate
def test_confluence_write_page_escapes_cdata_in_payload():
    resp_mock.add(
        resp_mock.GET,
        "https://wiki.example.com/rest/api/content",
        json={"results": []}, status=200,
    )
    captured_payload = {}

    def capture(request):
        import json as _json
        captured_payload.update(_json.loads(request.body))
        return (200, {}, '{"id":"1","title":"x"}')

    resp_mock.add_callback(
        resp_mock.POST,
        "https://wiki.example.com/rest/api/content",
        callback=capture,
    )
    b = ConfluenceBackend(
        url="https://wiki.example.com", token="tok", space="TEST", dry_run=False
    )
    b.write_page("concepts/foo.md", "danger ]]> still safe")
    storage = captured_payload["body"]["storage"]["value"]
    # Every <![CDATA[ must be matched by exactly one ]]>. Without escaping,
    # the user's stray ]]> would yield 1 open and 2 closes (broken XML).
    cdata_opens = storage.count("<![CDATA[")
    cdata_closes = storage.count("]]>")
    assert cdata_opens == cdata_closes
    assert cdata_opens == 2  # original wrapper + the split caused by escape


def test_confluence_write_page_dry_run_prints_message(capsys):
    b = ConfluenceBackend(
        url="https://wiki.example.com", token="tok", space="TEST", dry_run=True
    )
    b.write_page("concepts/foo.md", "# Foo\n\nContent.")
    captured = capsys.readouterr()
    assert "[DRY-RUN]" in captured.out
    assert "Concepts Foo" in captured.out


def test_confluence_deploy_dry_run_lists_pages(tmp_path, capsys):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "index.md").write_text("# Index")
    (wiki / "page-a.md").write_text("# Page A")
    b = ConfluenceBackend(
        url="https://wiki.example.com", token="tok", space="TEST", dry_run=True
    )
    b.deploy(wiki)
    captured = capsys.readouterr()
    assert "[DRY-RUN]" in captured.out
    assert "2 pages" in captured.out


@resp_mock.activate
def test_confluence_write_page_creates_new_page():
    # Page does not exist — empty search results
    resp_mock.add(
        resp_mock.GET,
        "https://wiki.example.com/rest/api/content",
        json={"results": []}, status=200,
    )
    # Create succeeds
    resp_mock.add(
        resp_mock.POST,
        "https://wiki.example.com/rest/api/content",
        json={"id": "99999", "title": "Concepts Foo"}, status=200,
    )
    b = ConfluenceBackend(
        url="https://wiki.example.com", token="tok", space="TEST", dry_run=False
    )
    b.write_page("concepts/foo.md", "# Foo\n\nContent.")
    # No exception = success


@resp_mock.activate
def test_confluence_write_page_raises_on_http_error():
    resp_mock.add(
        resp_mock.GET,
        "https://wiki.example.com/rest/api/content",
        json={"results": []}, status=200,
    )
    resp_mock.add(
        resp_mock.POST,
        "https://wiki.example.com/rest/api/content",
        status=401,
    )
    b = ConfluenceBackend(
        url="https://wiki.example.com", token="bad", space="TEST", dry_run=False
    )
    with pytest.raises(Exception):
        b.write_page("page.md", "# Page")

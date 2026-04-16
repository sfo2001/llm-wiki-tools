import pytest
import responses as resp_mock
from pathlib import Path
from llm_wiki.deploy.confluence import ConfluenceBackend


def test_confluence_target_name():
    b = ConfluenceBackend(url="https://wiki.example.com", token="tok", space="TEST")
    assert b.target_name == "confluence"


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

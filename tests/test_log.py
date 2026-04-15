from pathlib import Path
from llm_wiki.log import append_log


def test_append_log_creates_file(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    append_log(wiki_dir, operation="ingest", title="My Report")
    assert (wiki_dir / "log.md").exists()


def test_append_log_format(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    append_log(wiki_dir, operation="ingest", title="My Report")
    content = (wiki_dir / "log.md").read_text()
    assert "## [20" in content
    assert "ingest" in content
    assert "My Report" in content


def test_append_log_is_append_only(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    append_log(wiki_dir, operation="ingest", title="First")
    append_log(wiki_dir, operation="lint", title="Second")
    content = (wiki_dir / "log.md").read_text()
    assert "First" in content
    assert "Second" in content
    assert content.index("First") < content.index("Second")

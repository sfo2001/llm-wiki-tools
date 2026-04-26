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


def test_append_log_with_body(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    append_log(
        wiki_dir, operation="ingest", title="My Source",
        body="- Source: foo.pdf\n- Backend: pdf",
    )
    content = (wiki_dir / "log.md").read_text()
    assert "## [" in content
    assert "ingest | My Source" in content
    assert "- Source: foo.pdf" in content
    assert "- Backend: pdf" in content
    assert content.endswith("\n")


def test_append_log_does_not_modify_prior_entries(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    append_log(wiki_dir, operation="ingest", title="First", body="- a\n- b")
    before = (wiki_dir / "log.md").read_text()
    append_log(wiki_dir, operation="ingest", title="Second", body="- c")
    after = (wiki_dir / "log.md").read_text()
    assert after.startswith(before)


def test_append_log_normalizes_trailing_newline(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    log = wiki_dir / "log.md"
    log.write_text("# Log\n\n## [2026-01-01] ingest | First")  # no trailing newline
    append_log(wiki_dir, operation="ingest", title="Second")
    assert "## [2026-01-01] ingest | First" in log.read_text()
    assert log.read_text().endswith("\n")

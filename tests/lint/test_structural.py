import pytest
from pathlib import Path
from llm_wiki.lint import lint_structural
from llm_wiki.lint.structural import Finding
from llm_wiki.lint.report import format_report


@pytest.fixture
def broken_wiki(tmp_path):
    d = tmp_path / "wiki"
    d.mkdir()
    (d / "index.md").write_text(
        "# Index\n\n- [[page-a]] — exists\n- [[missing-page]] — gone\n",
        encoding="utf-8",
    )
    (d / "page-a.md").write_text(
        "# Page A\n\nSee [[broken-link]] and [[missing-page]].\n"
    )
    (d / "orphan.md").write_text("# Orphan\n\nNo one links here.\n")
    return d


def test_detects_broken_link(broken_wiki):
    findings = lint_structural(broken_wiki)
    broken = [f for f in findings if f.issue_type == "broken_link"]
    assert any("broken-link" in f.message for f in broken)


def test_detects_orphan_page(broken_wiki):
    findings = lint_structural(broken_wiki)
    orphans = [f for f in findings if f.issue_type == "orphan"]
    assert any("orphan" in str(f.path) for f in orphans)


def test_detects_missing_page_in_index(broken_wiki):
    findings = lint_structural(broken_wiki)
    missing = [f for f in findings if f.issue_type == "missing_page"]
    assert any("missing-page" in f.message for f in missing)


def test_clean_wiki_has_no_findings(wiki_dir):
    assert lint_structural(wiki_dir) == []


def test_format_report_has_file_colon_line(broken_wiki):
    findings = lint_structural(broken_wiki)
    report = format_report(findings)
    assert ":" in report


def test_format_report_empty_on_clean(wiki_dir):
    report = format_report(lint_structural(wiki_dir))
    assert "No issues found" in report

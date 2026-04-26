from pathlib import Path

from llm_wiki.lint.newlines import check_newlines


def test_clean_files_have_no_findings(tmp_path):
    d = tmp_path / "wiki"
    d.mkdir()
    (d / "a.md").write_text("# A\n")
    (d / "b.md").write_text("# B\n\nbody\n")
    assert check_newlines(d) == []


def test_missing_trailing_newline_flagged(tmp_path):
    d = tmp_path / "wiki"
    d.mkdir()
    (d / "a.md").write_bytes(b"# A")
    findings = check_newlines(d)
    assert len(findings) == 1
    assert findings[0].issue_type == "missing_newline"


def test_extra_trailing_newline_flagged(tmp_path):
    d = tmp_path / "wiki"
    d.mkdir()
    (d / "a.md").write_bytes(b"# A\n\n\n")
    findings = check_newlines(d)
    assert len(findings) == 1
    assert findings[0].issue_type == "extra_newline"


def test_empty_file_skipped(tmp_path):
    d = tmp_path / "wiki"
    d.mkdir()
    (d / "a.md").write_bytes(b"")
    assert check_newlines(d) == []


def test_dotdirs_excluded(tmp_path):
    d = tmp_path / "wiki"
    (d / ".tmp").mkdir(parents=True)
    (d / ".tmp" / "x.md").write_bytes(b"# no newline")
    assert check_newlines(d) == []

import subprocess
from pathlib import Path

import pytest

from llm_wiki.lint.append_only import check_log_append_only


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "wiki").mkdir()
    return repo


def test_no_findings_when_log_unchanged(repo):
    log = repo / "wiki" / "log.md"
    log.write_text("# Log\n\n## [2026-04-01] ingest | First\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init")
    assert check_log_append_only(repo / "wiki") == []


def test_appending_entry_passes(repo):
    log = repo / "wiki" / "log.md"
    log.write_text("# Log\n\n## [2026-04-01] ingest | First\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init")
    log.write_text(
        "# Log\n\n## [2026-04-01] ingest | First\n\n## [2026-04-02] ingest | Second\n"
    )
    assert check_log_append_only(repo / "wiki") == []


def test_overwriting_prior_header_flagged(repo):
    log = repo / "wiki" / "log.md"
    log.write_text("# Log\n\n## [2026-04-01] ingest | First\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init")
    log.write_text("# Log\n\n## [2026-04-02] ingest | Second\n")
    findings = check_log_append_only(repo / "wiki")
    assert len(findings) == 1
    assert findings[0].issue_type == "log_header_modified"
    assert "First" in findings[0].message


def test_modifying_prior_header_text_flagged(repo):
    log = repo / "wiki" / "log.md"
    log.write_text("# Log\n\n## [2026-04-01] ingest | First\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init")
    log.write_text("# Log\n\n## [2026-04-01] ingest | First — edited\n")
    findings = check_log_append_only(repo / "wiki")
    assert len(findings) == 1


def test_no_findings_outside_git_repo(tmp_path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "log.md").write_text("# Log\n\n## [2026-04-01] ingest | First\n")
    assert check_log_append_only(wiki) == []


def test_no_findings_when_log_missing_in_head(repo):
    log = repo / "wiki" / "log.md"
    (repo / "wiki" / "other.md").write_text("# Other\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init")
    log.write_text("# Log\n\n## [2026-04-01] ingest | First\n")
    assert check_log_append_only(repo / "wiki") == []

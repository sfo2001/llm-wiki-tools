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
    log.write_text(
        "# Log\n\n## [2026-04-01] ingest | First — edited\n", encoding="utf-8"
    )
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


def test_ref_parameter_compares_against_arbitrary_ref(repo):
    log = repo / "wiki" / "log.md"
    log.write_text("# Log\n\n## [2026-04-01] ingest | First\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "first")
    log.write_text(
        "# Log\n\n## [2026-04-01] ingest | First\n\n## [2026-04-02] ingest | Second\n"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "second")
    # Append a third entry but compare against HEAD~1 (which only had First+Second).
    log.write_text(
        "# Log\n\n## [2026-04-01] ingest | First\n\n"
        "## [2026-04-02] ingest | Second\n\n## [2026-04-03] ingest | Third\n"
    )
    assert check_log_append_only(repo / "wiki", ref="HEAD~1") == []
    # Now overwrite First. HEAD~1 contains only First, so HEAD~1 baseline flags
    # First missing; HEAD baseline (which had both) flags both missing.
    log.write_text("# Log\n\n## [2026-04-03] ingest | Third\n")
    findings_old = check_log_append_only(repo / "wiki", ref="HEAD~1")
    assert len(findings_old) == 1
    assert "First" in findings_old[0].message
    findings_head = check_log_append_only(repo / "wiki", ref="HEAD")
    assert len(findings_head) == 2


def test_round_trip_log_entry_to_lint_is_clean(repo):
    """append_log → commit → append_log → check_log_append_only is clean.

    Locks in the contract: the supported entry-point produces output
    the lint accepts. Regression guard for any future refactor of
    either side.
    """
    from llm_wiki.log import append_log

    wiki = repo / "wiki"
    (wiki / "log.md").write_text("# Log\n\n*Append-only.*\n")
    append_log(wiki, operation="ingest", title="First", body="- detail-a\n- detail-b")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "first-entry")
    append_log(wiki, operation="ingest", title="Second", body="- more")
    assert check_log_append_only(wiki) == []

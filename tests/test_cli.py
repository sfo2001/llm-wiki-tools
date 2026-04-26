import os
from click.testing import CliRunner
from llm_wiki.cli import main


def test_lwt_help():
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "ingest" in result.output
    assert "search" in result.output
    assert "lint" in result.output


def test_lwt_ingest_help():
    result = CliRunner().invoke(main, ["ingest", "--help"])
    assert result.exit_code == 0
    assert "--output" in result.output


def test_lwt_ingest_raw_file(tmp_path):
    source = tmp_path / "notes.md"
    source.write_text("# Notes\n\nContent here.", encoding="utf-8")
    wiki_dir = tmp_path / "wiki"
    result = CliRunner().invoke(main, [
        "ingest", str(source), "--wiki-dir", str(wiki_dir),
    ])
    assert result.exit_code == 0, result.output
    assert "Ingested:" in result.output
    assert "Lines:" in result.output


def test_lwt_ingest_stdout_mode(tmp_path):
    source = tmp_path / "notes.md"
    source.write_text("# Notes\n\nContent.", encoding="utf-8")
    wiki_dir = tmp_path / "wiki"
    result = CliRunner().invoke(main, [
        "ingest", str(source), "--wiki-dir", str(wiki_dir), "--output", "-",
    ])
    assert result.exit_code == 0
    assert "---" in result.output


def test_lwt_search(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "page.md").write_text(
        "# Topic\n\nContent about widgets.", encoding="utf-8"
    )
    result = CliRunner().invoke(main, ["search", "widgets",
                                       "--wiki-dir", str(wiki_dir)])
    assert result.exit_code == 0
    assert "page.md" in result.output


def test_lwt_lint_clean_wiki(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "index.md").write_text("# Index\n\n- [[page-a]] — Page A\n")
    (wiki_dir / "page-a.md").write_text("# Page A\n\nContent.\n")
    result = CliRunner().invoke(main, ["lint", "--structural",
                                       "--wiki-dir", str(wiki_dir)])
    assert result.exit_code == 0
    assert "No issues found" in result.output


def test_lwt_lint_writes_report_and_exits_nonzero(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "index.md").write_text("# Index\n\n- [[missing]] — Gone\n")
    result = CliRunner().invoke(main, ["lint", "--structural",
                                       "--wiki-dir", str(wiki_dir)])
    assert result.exit_code != 0
    assert (wiki_dir / "lint-report.md").exists()
    assert "missing" in (wiki_dir / "lint-report.md").read_text()


def test_lwt_lint_requires_a_check_flag(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    result = CliRunner().invoke(main, ["lint", "--wiki-dir", str(wiki_dir)])
    assert result.exit_code != 0
    assert "at least one check" in result.output.lower()


def test_lwt_lint_newlines_flag(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "a.md").write_bytes(b"# A")  # no trailing newline
    result = CliRunner().invoke(main, ["lint", "--newlines",
                                       "--wiki-dir", str(wiki_dir)])
    assert result.exit_code != 0
    assert "missing_newline" in (wiki_dir / "lint-report.md").read_text()


def test_lwt_lint_all_flag_runs_every_check(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "index.md").write_text("# Index\n\n- [[missing]] — Gone\n")
    (wiki_dir / "a.md").write_bytes(b"# A")
    result = CliRunner().invoke(main, ["lint", "--all",
                                       "--wiki-dir", str(wiki_dir)])
    assert result.exit_code != 0
    report = (wiki_dir / "lint-report.md").read_text()
    assert "missing_page" in report
    assert "missing_newline" in report


def test_lwt_log_entry_help():
    result = CliRunner().invoke(main, ["log-entry", "--help"])
    assert result.exit_code == 0
    assert "--op" in result.output
    assert "--title" in result.output


def test_lwt_log_entry_appends_to_log(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    result = CliRunner().invoke(main, [
        "log-entry", "--op", "ingest", "--title", "AI 2027",
        "--body", "- Source: https://ai-2027.com\n- Backend: web",
        "--wiki-dir", str(wiki_dir),
    ])
    assert result.exit_code == 0, result.output
    log = (wiki_dir / "log.md").read_text()
    assert "ingest | AI 2027" in log
    assert "- Source: https://ai-2027.com" in log


def test_lwt_log_entry_does_not_overwrite_prior(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "log.md").write_text(
        "# Log\n\n## [2026-04-25] ingest | First\n\n- detail\n"
    )
    before = (wiki_dir / "log.md").read_text()
    result = CliRunner().invoke(main, [
        "log-entry", "--op", "ingest", "--title", "Second",
        "--wiki-dir", str(wiki_dir),
    ])
    assert result.exit_code == 0, result.output
    after = (wiki_dir / "log.md").read_text()
    assert after.startswith(before.rstrip("\n"))
    assert "ingest | Second" in after


def test_lwt_log_entry_body_file_stdin(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    result = CliRunner().invoke(
        main,
        [
            "log-entry", "--op", "ingest", "--title", "From Stdin",
            "--body-file", "-",
            "--wiki-dir", str(wiki_dir),
        ],
        input="- piped body line\n",
    )
    assert result.exit_code == 0, result.output
    assert "- piped body line" in (wiki_dir / "log.md").read_text()


def test_lwt_lint_append_only_ref_flag(tmp_path):
    import subprocess
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    wiki = repo / "wiki"
    wiki.mkdir()
    log = wiki / "log.md"
    log.write_text("# Log\n\n## [2026-04-01] ingest | First\n")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "first"], cwd=repo, check=True)
    log.write_text("# Log\n\n## [2026-04-01] ingest | First\n\n## [2026-04-02] ingest | Second\n")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "second"], cwd=repo, check=True)
    # Overwrite First — comparing against HEAD~1 (where First was the only entry)
    # should flag, comparing against HEAD (where both existed) should also flag.
    log.write_text("# Log\n\n## [2026-04-03] ingest | Third\n")
    result = CliRunner().invoke(main, [
        "lint", "--append-only", "--ref", "HEAD~1",
        "--wiki-dir", str(wiki),
    ])
    assert result.exit_code != 0
    assert "HEAD~1" in (wiki / "lint-report.md").read_text()


def test_lwt_log_entry_rejects_body_and_body_file(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    body_file = tmp_path / "b.txt"
    body_file.write_text("x")
    result = CliRunner().invoke(main, [
        "log-entry", "--op", "ingest", "--title", "T",
        "--body", "y", "--body-file", str(body_file),
        "--wiki-dir", str(wiki_dir),
    ])
    assert result.exit_code != 0


# --- deploy tests ---
from unittest.mock import patch as mock_patch


def test_lwt_deploy_help():
    result = CliRunner().invoke(main, ["deploy", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "local" in result.output
    assert "docker" in result.output
    assert "confluence" in result.output


def test_lwt_deploy_local_starts_server(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "index.md").write_text("# Index")
    with mock_patch("llm_wiki.deploy.local.subprocess.run"):
        result = CliRunner().invoke(main, [
            "deploy", "--target", "local",
            "--wiki-dir", str(wiki_dir),
        ])
    assert result.exit_code == 0


def test_lwt_deploy_confluence_dry_run(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "index.md").write_text("# Index")
    (wiki_dir / "page-a.md").write_text("# Page A")
    result = CliRunner().invoke(
        main,
        ["deploy", "--target", "confluence", "--wiki-dir", str(wiki_dir), "--dry-run"],
        env={"CONFLUENCE_URL": "https://wiki.example.com",
             "CONFLUENCE_TOKEN": "tok",
             "CONFLUENCE_SPACE": "TEST"},
    )
    assert result.exit_code == 0
    assert "DRY-RUN" in result.output


# --- init tests ---

def test_lwt_init_help():
    result = CliRunner().invoke(main, ["init", "--help"])
    assert result.exit_code == 0
    assert "--name" in result.output


def test_lwt_init_creates_structure(tmp_path):
    result = CliRunner().invoke(main, [
        "init", str(tmp_path / "mywiki"), "--name", "Test Wiki",
    ])
    assert result.exit_code == 0, result.output
    wiki_path = tmp_path / "mywiki"
    assert (wiki_path / "raw").is_dir()
    assert (wiki_path / "wiki").is_dir()
    assert (wiki_path / "templates").is_dir()
    assert (wiki_path / "output").is_dir()
    assert (wiki_path / "AGENTS.md").exists()
    assert (wiki_path / "CLAUDE.md").exists()
    assert (wiki_path / ".gitignore").exists()
    assert (wiki_path / ".lwt.env.example").exists()


def test_lwt_init_creates_all_templates(tmp_path):
    CliRunner().invoke(main, ["init", str(tmp_path / "wiki")])
    templates = tmp_path / "wiki" / "templates"
    for name in ["default.md", "entity.md", "concept.md",
                 "source-summary.md", "query-answer.md"]:
        assert (templates / name).exists(), f"Missing template: {name}"


def test_lwt_init_index_contains_name(tmp_path):
    CliRunner().invoke(main, [
        "init", str(tmp_path / "wiki"), "--name", "My Project",
    ])
    index = (tmp_path / "wiki" / "wiki" / "index.md").read_text()
    assert "My Project" in index


def test_lwt_init_gitignore_excludes_tmp(tmp_path):
    CliRunner().invoke(main, ["init", str(tmp_path / "wiki")])
    gitignore = (tmp_path / "wiki" / ".gitignore").read_text()
    assert "wiki/.tmp/" in gitignore


# --- mkdocs deploy tests ---

def test_lwt_deploy_mkdocs_in_help():
    result = CliRunner().invoke(main, ["deploy", "--help"])
    assert result.exit_code == 0
    assert "mkdocs" in result.output


def test_lwt_deploy_mkdocs_serve(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "index.md").write_text("# Index")
    with mock_patch("llm_wiki.deploy.mkdocs_backend.subprocess.run"):
        result = CliRunner().invoke(main, [
            "deploy", "--target", "mkdocs",
            "--wiki-dir", str(wiki_dir),
        ])
    assert result.exit_code == 0


def test_lwt_deploy_mkdocs_build(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "index.md").write_text("# Index")
    with mock_patch("llm_wiki.deploy.mkdocs_backend.subprocess.run") as mock_run:
        result = CliRunner().invoke(main, [
            "deploy", "--target", "mkdocs",
            "--wiki-dir", str(wiki_dir),
            "--build",
        ])
    assert result.exit_code == 0
    cmd = mock_run.call_args[0][0]
    assert "build" in " ".join(str(a) for a in cmd)


def test_lwt_deploy_mkdocs_port_override(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "index.md").write_text("# Index")
    with mock_patch("llm_wiki.deploy.mkdocs_backend.subprocess.run") as mock_run:
        result = CliRunner().invoke(main, [
            "deploy", "--target", "mkdocs",
            "--wiki-dir", str(wiki_dir),
            "--port", "9000",
        ])
    assert result.exit_code == 0
    cmd = mock_run.call_args[0][0]
    assert "9000" in " ".join(str(a) for a in cmd)


# --- init scaffold: skills/ ---

def test_lwt_init_creates_skills_dir(tmp_path):
    result = CliRunner().invoke(main, ["init", str(tmp_path / "wiki")])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "wiki" / "skills").is_dir()


def test_lwt_init_skills_has_four_files(tmp_path):
    result = CliRunner().invoke(main, ["init", str(tmp_path / "wiki")])
    assert result.exit_code == 0, result.output
    skills = tmp_path / "wiki" / "skills"
    for name in ["ingest.md", "query.md", "lint.md", "deploy.md"]:
        assert (skills / name).exists(), f"Missing skill: {name}"


def test_lwt_init_skills_ingest_not_empty(tmp_path):
    result = CliRunner().invoke(main, ["init", str(tmp_path / "wiki")])
    assert result.exit_code == 0, result.output
    content = (tmp_path / "wiki" / "skills" / "ingest.md").read_text()
    assert "lwt ingest" in content


# --- init scaffold: README.md ---

def test_lwt_init_creates_readme(tmp_path):
    result = CliRunner().invoke(main, ["init", str(tmp_path / "wiki"), "--name", "My Research"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "wiki" / "README.md").exists()


def test_lwt_init_readme_contains_name(tmp_path):
    result = CliRunner().invoke(main, ["init", str(tmp_path / "wiki"), "--name", "My Research"])
    assert result.exit_code == 0, result.output
    content = (tmp_path / "wiki" / "README.md").read_text()
    assert "My Research" in content
    assert "__NAME__" not in content


def test_lwt_init_readme_contains_run_sh(tmp_path):
    result = CliRunner().invoke(main, ["init", str(tmp_path / "wiki")])
    assert result.exit_code == 0, result.output
    content = (tmp_path / "wiki" / "README.md").read_text()
    assert "run.sh" in content


# --- init scaffold: run scripts ---

def test_lwt_init_creates_run_sh(tmp_path):
    result = CliRunner().invoke(main, ["init", str(tmp_path / "wiki")])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "wiki" / "run.sh").exists()


def test_lwt_init_run_sh_is_executable(tmp_path):
    result = CliRunner().invoke(main, ["init", str(tmp_path / "wiki")])
    assert result.exit_code == 0, result.output
    assert os.access(tmp_path / "wiki" / "run.sh", os.X_OK)


def test_lwt_init_creates_run_ps1(tmp_path):
    result = CliRunner().invoke(main, ["init", str(tmp_path / "wiki")])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "wiki" / "run.ps1").exists()


# --- init scaffold: tools/ + --wheel ---

def test_lwt_init_creates_tools_dir(tmp_path):
    result = CliRunner().invoke(main, ["init", str(tmp_path / "wiki")])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "wiki" / "tools").is_dir()


def test_lwt_init_without_wheel_warns(tmp_path):
    result = CliRunner().invoke(main, ["init", str(tmp_path / "wiki")])
    assert result.exit_code == 0
    assert "tools/" in result.output
    assert "wheel" in result.output.lower()


def test_lwt_init_with_wheel_copies_it(tmp_path):
    wheel = tmp_path / "llm_wiki_tools-0.1.0-py3-none-any.whl"
    wheel.write_bytes(b"PK\x03\x04")
    target = tmp_path / "wiki"
    result = CliRunner().invoke(main, [
        "init", str(target), "--wheel", str(wheel),
    ])
    assert result.exit_code == 0, result.output
    assert (target / "tools" / "llm_wiki_tools-0.1.0-py3-none-any.whl").exists()


def test_lwt_init_with_wheel_does_not_warn(tmp_path):
    wheel = tmp_path / "llm_wiki_tools-0.1.0-py3-none-any.whl"
    wheel.write_bytes(b"PK")
    result = CliRunner().invoke(main, [
        "init", str(tmp_path / "wiki"), "--wheel", str(wheel),
    ])
    assert result.exit_code == 0
    assert "Drop a llm_wiki_tools" not in result.output


def test_lwt_init_with_invalid_wheel_rejects(tmp_path):
    bogus = tmp_path / "not-a-wheel.txt"
    bogus.write_bytes(b"nope")
    result = CliRunner().invoke(main, [
        "init", str(tmp_path / "wiki"), "--wheel", str(bogus),
    ])
    assert result.exit_code != 0

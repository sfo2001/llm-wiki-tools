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

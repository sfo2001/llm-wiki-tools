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

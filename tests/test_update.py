from pathlib import Path
import pytest
from click.testing import CliRunner
from llm_wiki.cli import main
from llm_wiki.update import (
    CANONICAL_FILES,
    CUSTOMISABLE_FILES,
    FileStatus,
    compute_status,
)


def _scaffold(tmp_path: Path) -> Path:
    target = tmp_path / "wiki-repo"
    CliRunner().invoke(main, ["init", str(target), "--name", "Test"])
    return target


def test_taxonomy_disjoint():
    assert set(CANONICAL_FILES).isdisjoint(set(CUSTOMISABLE_FILES))


def test_taxonomy_covers_every_bundled_file():
    from llm_wiki.update import _BUNDLED_FILES
    assert set(_BUNDLED_FILES) == set(CANONICAL_FILES) | set(CUSTOMISABLE_FILES)


def test_compute_status_fresh_scaffold_all_identical(tmp_path):
    target = _scaffold(tmp_path)
    statuses = compute_status(target, name="Test")
    for s in statuses:
        assert s.state == "identical", f"{s.rel_path}: {s.state}"


def test_compute_status_detects_canonical_drift(tmp_path):
    target = _scaffold(tmp_path)
    (target / "AGENTS.md").write_text("user butchered this\n")
    statuses = {s.rel_path: s for s in compute_status(target, name="Test")}
    assert statuses["AGENTS.md"].state == "differs"
    assert statuses["AGENTS.md"].class_ == "canonical"


def test_compute_status_detects_customisable_drift(tmp_path):
    target = _scaffold(tmp_path)
    (target / "CLAUDE.md").write_text("# my custom instructions\n")
    statuses = {s.rel_path: s for s in compute_status(target, name="Test")}
    assert statuses["CLAUDE.md"].state == "differs"
    assert statuses["CLAUDE.md"].class_ == "customisable"


def test_compute_status_handles_missing_file(tmp_path):
    target = _scaffold(tmp_path)
    (target / "run.sh").unlink()
    statuses = {s.rel_path: s for s in compute_status(target, name="Test")}
    assert statuses["run.sh"].state == "missing"


# --- apply_update ---

from llm_wiki.update import apply_update

_BUNDLED_AGENTS = (
    Path(__file__).parent.parent / "src/llm_wiki/data/AGENTS.md"
).read_bytes()


def test_apply_updates_canonical_silently(tmp_path):
    target = _scaffold(tmp_path)
    (target / "AGENTS.md").write_text("stale\n")
    written = apply_update(target, force=False, name="Test")
    assert "AGENTS.md" in [w.rel_path for w in written]
    assert (target / "AGENTS.md").read_bytes() == _BUNDLED_AGENTS


def test_apply_skips_customisable_without_force(tmp_path):
    target = _scaffold(tmp_path)
    (target / "CLAUDE.md").write_text("custom\n")
    written = apply_update(target, force=False, name="Test")
    assert "CLAUDE.md" not in [w.rel_path for w in written]
    assert (target / "CLAUDE.md").read_text() == "custom\n"


def test_apply_overwrites_customisable_with_force(tmp_path):
    target = _scaffold(tmp_path)
    (target / "CLAUDE.md").write_text("custom\n")
    written = apply_update(target, force=True, name="Test")
    assert "CLAUDE.md" in [w.rel_path for w in written]
    assert (target / "CLAUDE.md").read_bytes() != b"custom\n"


def test_apply_restores_missing_canonical_file(tmp_path):
    target = _scaffold(tmp_path)
    (target / "run.sh").unlink()
    apply_update(target, force=False, name="Test")
    assert (target / "run.sh").exists()


def test_apply_chmods_run_sh(tmp_path):
    target = _scaffold(tmp_path)
    (target / "run.sh").write_text("stale\n")
    (target / "run.sh").chmod(0o644)
    apply_update(target, force=False, name="Test")
    mode = (target / "run.sh").stat().st_mode & 0o777
    assert mode & 0o100, f"run.sh not executable: {oct(mode)}"


def test_apply_creates_parent_dirs_for_skills(tmp_path):
    target = _scaffold(tmp_path)
    import shutil
    shutil.rmtree(target / "skills")
    apply_update(target, force=False, name="Test")
    assert (target / "skills" / "ingest.md").exists()


def test_apply_is_idempotent(tmp_path):
    target = _scaffold(tmp_path)
    (target / "AGENTS.md").write_text("stale\n")
    apply_update(target, force=False, name="Test")
    second = apply_update(target, force=False, name="Test")
    assert second == [], "second apply should be a no-op"


# --- CLI ---

def test_cli_update_dry_run_default(tmp_path):
    target = _scaffold(tmp_path)
    (target / "AGENTS.md").write_text("stale\n")
    result = CliRunner().invoke(main, ["update", str(target)])
    assert result.exit_code == 0
    assert "AGENTS.md" in result.output
    assert "differs" in result.output
    assert (target / "AGENTS.md").read_text() == "stale\n"


def test_cli_update_apply_writes_canonical(tmp_path):
    target = _scaffold(tmp_path)
    (target / "AGENTS.md").write_text("stale\n")
    result = CliRunner().invoke(main, ["update", str(target), "--apply"])
    assert result.exit_code == 0
    assert (target / "AGENTS.md").read_text() != "stale\n"


def test_cli_update_apply_skips_customisable(tmp_path):
    target = _scaffold(tmp_path)
    (target / "CLAUDE.md").write_text("mine\n")
    CliRunner().invoke(main, ["update", str(target), "--apply"])
    assert (target / "CLAUDE.md").read_text() == "mine\n"


def test_cli_update_force_overwrites_customisable(tmp_path):
    target = _scaffold(tmp_path)
    (target / "CLAUDE.md").write_text("mine\n")
    CliRunner().invoke(main, ["update", str(target), "--apply", "--force"])
    assert (target / "CLAUDE.md").read_text() != "mine\n"


def test_cli_update_clean_repo_reports_no_changes(tmp_path):
    target = _scaffold(tmp_path)
    result = CliRunner().invoke(main, ["update", str(target), "--apply"])
    assert "Nothing to do" in result.output

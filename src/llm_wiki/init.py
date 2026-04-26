import os
from pathlib import Path

_DATA_DIR = Path(__file__).parent / "data"


def scaffold_data_repo(
    target_dir: Path,
    name: str = "my-wiki",
    wheel: Path | None = None,
) -> None:
    """Create the llm-wiki data repo directory structure at target_dir.

    If wheel is given, also seed target_dir/tools/ with the lwt wheel so
    run.sh / run.ps1 can bootstrap on first run.
    """
    target_dir.mkdir(parents=True, exist_ok=True)

    # Directory structure
    for d in ["raw", "wiki/queries", "output"]:
        (target_dir / d).mkdir(parents=True, exist_ok=True)
        (target_dir / d / ".gitkeep").touch()

    # Stub wiki files
    (target_dir / "wiki" / "index.md").write_text(
        f"# {name} Wiki\n\n"
        "*Index — updated by LLM on every write.*\n\n"
        "## Pages\n\n*(empty — add pages as you ingest sources)*\n",
        encoding="utf-8",
    )
    (target_dir / "wiki" / "log.md").write_text(
        "# Operation Log\n\n"
        "*Append-only. Each entry: `## [YYYY-MM-DD] op | title`*\n",
        encoding="utf-8",
    )

    # Templates (copied from bundled data)
    templates_src = _DATA_DIR / "templates"
    templates_dst = target_dir / "templates"
    templates_dst.mkdir(exist_ok=True)
    for tmpl in [
        "default.md", "entity.md", "concept.md",
        "source-summary.md", "query-answer.md",
    ]:
        (templates_dst / tmpl).write_bytes((templates_src / tmpl).read_bytes())

    # Skills (bundled — satisfies CLAUDE.md @path references)
    skills_dst = target_dir / "skills"
    skills_dst.mkdir(exist_ok=True)
    for skill in ["ingest.md", "query.md", "lint.md", "deploy.md"]:
        (skills_dst / skill).write_bytes(
            (_DATA_DIR / "skills" / skill).read_bytes()
        )

    # Schema files
    (target_dir / "AGENTS.md").write_bytes((_DATA_DIR / "AGENTS.md").read_bytes())
    (target_dir / "CLAUDE.md").write_bytes((_DATA_DIR / "CLAUDE.md").read_bytes())

    # Config files
    gitignore = (_DATA_DIR / ".gitignore.template").read_text(encoding="utf-8")
    (target_dir / ".gitignore").write_text(gitignore, encoding="utf-8")
    (target_dir / ".lwt.env.example").write_bytes(
        (_DATA_DIR / ".lwt.env.example").read_bytes()
    )

    # Human-facing HOWTO
    readme_template = (_DATA_DIR / "README.md.template").read_text(encoding="utf-8")
    (target_dir / "README.md").write_text(
        readme_template.replace("__NAME__", name), encoding="utf-8"
    )

    # Wrapper scripts
    (target_dir / "run.sh").write_bytes((_DATA_DIR / "run.sh").read_bytes())
    os.chmod(target_dir / "run.sh", 0o755)
    (target_dir / "run.ps1").write_bytes((_DATA_DIR / "run.ps1").read_bytes())

    # Tools dir for the bootstrap wheel
    (target_dir / "tools").mkdir(exist_ok=True)
    if wheel is not None:
        from llm_wiki.update import install_wheel
        install_wheel(target_dir, wheel)

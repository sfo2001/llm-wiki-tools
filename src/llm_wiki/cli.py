import sys
from pathlib import Path

import click

from llm_wiki import __version__
from llm_wiki.ingest import IngestResult, ingest_source
from llm_wiki.lint import check_log_append_only, check_newlines, lint_structural
from llm_wiki.lint.report import format_report
from llm_wiki.log import append_log
from llm_wiki.search import search


@click.group()
@click.version_option(__version__, prog_name="lwt")
def main() -> None:
    """llm-wiki-tools — LLM wiki maintenance toolchain."""


@main.command()
@click.argument("source")
@click.option("--wiki-dir", default="wiki", show_default=True)
@click.option("--output", default=None,
              help="Output path for temp file, or '-' for stdout.")
@click.option("--allow-internal", is_flag=True, default=False,
              help="Permit URLs pointing at loopback / RFC1918 / link-local hosts.")
def ingest(source: str, wiki_dir: str, output: str | None, allow_internal: bool) -> None:
    """Convert a source file or URL to markdown in wiki/.tmp/."""
    wiki_path = Path(wiki_dir)
    command = f"lwt ingest {source}" + (f" --output {output}" if output else "")
    if allow_internal:
        command += " --allow-internal"
    result: IngestResult = ingest_source(
        source=source,
        wiki_dir=wiki_path,
        ingest_command=command,
        output=output,
        allow_internal=allow_internal,
    )
    if output == "-":
        return
    click.echo(f"Ingested:   {result.path}")
    click.echo(f"Lines:      {result.lines}")
    click.echo(f"Sections:   {result.sections}")
    click.echo(f"Backend:    {result.backend}")
    click.echo(f"Source-SHA: {result.source_sha}")


@main.command(name="search")
@click.argument("query")
@click.option("--wiki-dir", default="wiki", show_default=True)
@click.option("-n", default=10, show_default=True)
@click.option("--reindex", is_flag=True)
def search_cmd(query: str, wiki_dir: str, n: int, reindex: bool) -> None:
    """BM25 keyword search over wiki pages."""
    wiki_path = Path(wiki_dir)
    if reindex:
        from llm_wiki.search.bm25 import BM25Index
        BM25Index(wiki_path).build()
        click.echo("Index rebuilt.")
    results = search(wiki_path, query, n=n)
    if not results:
        click.echo("No results.")
        return
    for r in results:
        try:
            rel = r.path.relative_to(wiki_path)
        except ValueError:
            rel = r.path
        click.echo(f"{rel}\tscore={r.score:.1f}\t{r.snippet}")


@main.command()
@click.option("--structural", is_flag=True, default=False,
              help="Broken links, orphans, missing pages.")
@click.option("--newlines", "newlines_flag", is_flag=True, default=False,
              help="Every wiki/**/*.md ends with exactly one trailing newline.")
@click.option("--append-only", "append_only_flag", is_flag=True, default=False,
              help="No prior log.md `## [date]` header has been removed or modified vs --ref.")
@click.option("--ref", default="HEAD", show_default=True,
              help="Git ref used as the baseline for --append-only (e.g. HEAD, origin/main, HEAD~1).")
@click.option("--all", "all_flag", is_flag=True, default=False,
              help="Run all available checks.")
@click.option("--wiki-dir", default="wiki", show_default=True)
@click.option("--output", default=None)
def lint(
    structural: bool, newlines_flag: bool, append_only_flag: bool,
    ref: str, all_flag: bool, wiki_dir: str, output: str | None,
) -> None:
    """Run lint checks over the wiki. At least one check flag is required."""
    if all_flag:
        structural = newlines_flag = append_only_flag = True
    if not (structural or newlines_flag or append_only_flag):
        raise click.UsageError(
            "Specify at least one check: --structural, --newlines, --append-only, or --all."
        )
    wiki_path = Path(wiki_dir)
    findings = []
    if structural:
        findings += lint_structural(wiki_path)
    if newlines_flag:
        findings += check_newlines(wiki_path)
    if append_only_flag:
        findings += check_log_append_only(wiki_path, ref=ref)
    report = format_report(findings)
    report_path = Path(output) if output else wiki_path / "lint-report.md"
    report_path.write_text(report, encoding="utf-8")
    click.echo(report.rstrip())
    if findings:
        click.echo(f"\nReport written to {report_path}")
        sys.exit(1)


@main.command(name="log-entry")
@click.option("--op", required=True, help="Operation type (e.g. ingest, lint, query).")
@click.option("--title", required=True, help="Entry title.")
@click.option("--body", default=None,
              help="Entry body (markdown). Use --body-file or '-' for stdin instead.")
@click.option("--body-file", default=None, type=click.Path(),
              help="Path to file containing entry body. Use '-' for stdin.")
@click.option("--wiki-dir", default="wiki", show_default=True)
def log_entry_cmd(
    op: str, title: str, body: str | None, body_file: str | None, wiki_dir: str,
) -> None:
    """Append an entry to wiki/log.md atomically. Never modifies prior entries."""
    if body and body_file:
        raise click.UsageError("Use either --body or --body-file, not both.")
    if body_file == "-":
        body = sys.stdin.read()
    elif body_file:
        body = Path(body_file).read_text(encoding="utf-8")
    append_log(Path(wiki_dir), operation=op, title=title, body=body)
    click.echo(f"Appended to {wiki_dir}/log.md: {op} | {title}")


@main.command()
@click.option(
    "--target", required=True,
    type=click.Choice(["local", "docker", "confluence", "mkdocs"]),
    help="Deployment target.",
)
@click.option("--wiki-dir", default="wiki", show_default=True)
@click.option("--port", default=None, type=int,
              help="Port override (default: 8080 local, 8443 docker, 8000 mkdocs).")
@click.option(
    "--mode", default="volume",
    type=click.Choice(["volume", "image"]), show_default=True,
    help="Docker mode: volume (live updates) or image (baked snapshot).",
)
@click.option(
    "--dry-run/--no-dry-run", default=True, show_default=True,
    help="Confluence: print diff without pushing (default: dry-run).",
)
@click.option(
    "--build", is_flag=True, default=False,
    help="MkDocs: build static site instead of serving (default: serve).",
)
@click.option(
    "--public", is_flag=True, default=False,
    help="Bind dev server to 0.0.0.0 (LAN-reachable). Default binds to 127.0.0.1.",
)
def deploy(
    target: str, wiki_dir: str, port: int | None, mode: str, dry_run: bool,
    build: bool, public: bool,
) -> None:
    """Deploy wiki/ to a target (local HTTP, Docker, Confluence, or MkDocs Material)."""
    import os
    wiki_path = Path(wiki_dir)
    bind = "0.0.0.0" if public else "127.0.0.1"
    if target == "local":
        from llm_wiki.deploy.local import LocalBackend
        backend = LocalBackend(wiki_path, port=port or 8080, bind=bind)
    elif target == "docker":
        from llm_wiki.deploy.docker import DockerBackend
        backend = DockerBackend(wiki_path, port=port or 8443, mode=mode)
    elif target == "mkdocs":
        from llm_wiki.deploy.mkdocs_backend import MkdocsBackend
        resolved_name = wiki_path.resolve().parent.name.replace("-", " ").title()
        name = resolved_name or "Wiki"
        backend = MkdocsBackend(
            wiki_path, port=port or 8000, name=name, build=build, bind=bind,
        )
    else:  # confluence
        from llm_wiki.deploy.confluence import ConfluenceBackend
        url = os.environ.get("CONFLUENCE_URL", "")
        token = os.environ.get("CONFLUENCE_TOKEN", "")
        space = os.environ.get("CONFLUENCE_SPACE", "")
        if not dry_run and not all([url, token, space]):
            missing = [k for k, v in [
                ("CONFLUENCE_URL", url), ("CONFLUENCE_TOKEN", token), ("CONFLUENCE_SPACE", space)
            ] if not v]
            raise click.UsageError(
                f"Missing required env vars for live Confluence deploy: {', '.join(missing)}\n"
                "Set them in .lwt.env or export them, or use --dry-run."
            )
        backend = ConfluenceBackend(url=url, token=token, space=space, dry_run=dry_run)
    backend.deploy(wiki_path)


@main.command(name="init")
@click.argument("path", default=".")
@click.option("--name", default="my-wiki", show_default=True,
              help="Human-readable name for this wiki.")
def init_cmd(path: str, name: str) -> None:
    """Scaffold a new llm-wiki data repository."""
    from llm_wiki.init import scaffold_data_repo
    target = Path(path)
    scaffold_data_repo(target, name=name)
    click.echo(f"Initialized wiki at {target.resolve()}")
    click.echo(f"  raw/              — drop source files here")
    click.echo(f"  wiki/             — LLM-maintained markdown pages")
    click.echo(f"  templates/        — page templates")
    click.echo(f"  AGENTS.md         — agent schema (edit to customize)")
    click.echo(f"  CLAUDE.md         — Claude Code configuration")
    click.echo(f"  .lwt.env.example  — copy to .lwt.env and fill in credentials")


@main.command(name="update")
@click.argument("path", default=".")
@click.option("--apply", "apply_changes", is_flag=True, default=False,
              help="Write changes (default: dry-run / status only).")
@click.option("--force", is_flag=True, default=False,
              help="Also overwrite customisable files (CLAUDE.md, templates/, …).")
def update_cmd(path: str, apply_changes: bool, force: bool) -> None:
    """Refresh bundled assets (AGENTS.md, skills/, run.sh) in an existing wiki repo."""
    from llm_wiki.update import apply_update, compute_status, detect_name
    target = Path(path)
    name = detect_name(target)
    statuses = compute_status(target, name=name)
    differs = [s for s in statuses if s.state != "identical"]
    if not differs:
        click.echo("All bundled files match. Nothing to do.")
        return
    width = max(len(s.rel_path) for s in differs)
    click.echo(f"{'File':<{width}}  {'Class':<13}  {'State':<10}  Action")
    click.echo("-" * (width + 40))
    for s in differs:
        action = (
            "will update" if (s.class_ == "canonical" or force)
            else "skip (use --force)"
        )
        click.echo(f"{s.rel_path:<{width}}  {s.class_:<13}  {s.state:<10}  {action}")
    if not apply_changes:
        click.echo("\nDry run — pass --apply to write changes.")
        return
    written = apply_update(target, force=force, name=name)
    click.echo(f"\nUpdated {len(written)} file(s).")

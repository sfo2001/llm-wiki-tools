import re
import subprocess
from pathlib import Path

from llm_wiki.lint.structural import Finding

_HEADER_RE = re.compile(r"^## \[\d{4}-\d{2}-\d{2}\] [^\n]+$", re.MULTILINE)


def _git_show(repo_root: Path, ref: str, rel_path: str) -> str | None:
    """Return file content at `ref:rel_path` or None if missing/not-a-repo."""
    try:
        result = subprocess.run(
            ["git", "show", f"{ref}:{rel_path}"],
            cwd=repo_root, capture_output=True, text=True, check=False,
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _find_repo_root(start: Path) -> Path | None:
    p = start.resolve()
    for candidate in [p, *p.parents]:
        if (candidate / ".git").exists():
            return candidate
    return None


def check_log_append_only(wiki_dir: Path, ref: str = "HEAD") -> list[Finding]:
    """Verify every `## [date] op | title` header present at `ref` is still
    present verbatim in current wiki/log.md."""
    log_path = wiki_dir / "log.md"
    if not log_path.exists():
        return []
    repo_root = _find_repo_root(wiki_dir)
    if repo_root is None:
        return []
    rel = log_path.resolve().relative_to(repo_root).as_posix()
    prior = _git_show(repo_root, ref, rel)
    if prior is None:
        return []
    current = log_path.read_text(encoding="utf-8")
    prior_headers = _HEADER_RE.findall(prior)
    current_headers = set(_HEADER_RE.findall(current))
    findings: list[Finding] = []
    for header in prior_headers:
        if header not in current_headers:
            findings.append(Finding(
                path=log_path, line=0, issue_type="log_header_modified",
                message=f"prior log entry missing or modified at {ref}: {header}",
            ))
    return findings

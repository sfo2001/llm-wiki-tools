from pathlib import Path

from llm_wiki.lint.structural import Finding


def check_newlines(wiki_dir: Path) -> list[Finding]:
    """Every wiki markdown file must end with exactly one trailing newline."""
    findings: list[Finding] = []
    for path in sorted(wiki_dir.rglob("*.md")):
        if any(part.startswith(".") for part in path.parts):
            continue
        data = path.read_bytes()
        if not data:
            continue
        if not data.endswith(b"\n"):
            findings.append(Finding(
                path=path, line=0, issue_type="missing_newline",
                message="file does not end with a trailing newline",
            ))
        elif data.endswith(b"\n\n"):
            extra = len(data) - len(data.rstrip(b"\n")) - 1
            findings.append(Finding(
                path=path, line=0, issue_type="extra_newline",
                message=f"file has {extra} extra trailing newline(s)",
            ))
    return findings

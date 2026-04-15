import re
from dataclasses import dataclass
from pathlib import Path

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


@dataclass
class Finding:
    path: Path
    line: int
    issue_type: str   # "broken_link" | "orphan" | "missing_page"
    message: str


def _slug(name: str) -> str:
    return name.strip().lower().replace(" ", "-")


def _page_map(wiki_dir: Path) -> dict[str, Path]:
    return {
        p.stem.lower(): p
        for p in wiki_dir.rglob("*.md")
        if not any(part.startswith(".") for part in p.parts)
    }


def _iter_pages(wiki_dir: Path):
    for path in wiki_dir.rglob("*.md"):
        if not any(part.startswith(".") for part in path.parts):
            yield path, path.read_text(encoding="utf-8", errors="replace")


def check_broken_links(wiki_dir: Path) -> list[Finding]:
    pages = _page_map(wiki_dir)
    findings = []
    for path, content in _iter_pages(wiki_dir):
        for lineno, line in enumerate(content.splitlines(), start=1):
            for m in WIKILINK_RE.finditer(line):
                if _slug(m.group(1)) not in pages:
                    findings.append(Finding(
                        path=path, line=lineno,
                        issue_type="broken_link",
                        message=f"broken link: [[{m.group(1)}]] — page not found",
                    ))
    return findings


def check_orphans(wiki_dir: Path) -> list[Finding]:
    pages = _page_map(wiki_dir)
    referenced: set[str] = set()
    for _, content in _iter_pages(wiki_dir):
        for m in WIKILINK_RE.finditer(content):
            referenced.add(_slug(m.group(1)))
    skip = {"index", "log", "lint-report"}
    return [
        Finding(path=path, line=0, issue_type="orphan",
                message=f"orphan page: no inbound links to [[{slug}]]")
        for slug, path in pages.items()
        if slug not in referenced and slug not in skip
    ]


def check_missing_pages(wiki_dir: Path) -> list[Finding]:
    index = wiki_dir / "index.md"
    if not index.exists():
        return []
    pages = _page_map(wiki_dir)
    findings = []
    for lineno, line in enumerate(
        index.read_text(encoding="utf-8").splitlines(), start=1
    ):
        for m in WIKILINK_RE.finditer(line):
            if _slug(m.group(1)) not in pages:
                findings.append(Finding(
                    path=index, line=lineno,
                    issue_type="missing_page",
                    message=f"index references missing page: [[{m.group(1)}]]",
                ))
    return findings

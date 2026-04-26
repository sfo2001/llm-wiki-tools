from pathlib import Path
from llm_wiki.lint.append_only import check_log_append_only
from llm_wiki.lint.newlines import check_newlines
from llm_wiki.lint.structural import (
    Finding,
    check_broken_links,
    check_missing_pages,
    check_orphans,
)


def lint_structural(wiki_dir: Path) -> list[Finding]:
    return (
        check_broken_links(wiki_dir)
        + check_orphans(wiki_dir)
        + check_missing_pages(wiki_dir)
    )


__all__ = [
    "lint_structural",
    "check_log_append_only",
    "check_newlines",
    "Finding",
]

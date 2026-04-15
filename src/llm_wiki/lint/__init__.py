from pathlib import Path
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


__all__ = ["lint_structural", "Finding"]

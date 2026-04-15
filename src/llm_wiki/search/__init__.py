from pathlib import Path
from llm_wiki.search.bm25 import BM25Index, SearchResult


def search(wiki_dir: Path, query: str, n: int = 10) -> list[SearchResult]:
    """Search wiki pages using BM25. Returns ranked list of SearchResult."""
    return BM25Index(wiki_dir).search(query, n=n)


__all__ = ["search", "SearchResult"]

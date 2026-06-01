import pytest
from pathlib import Path
from llm_wiki.search import search, SearchResult
from llm_wiki.search.bm25 import BM25Index


def test_bm25_build_and_search(wiki_dir):
    idx = BM25Index(wiki_dir)
    idx.build()
    results = idx.search("page links", n=5)
    assert len(results) > 0
    assert all(isinstance(r, SearchResult) for r in results)


def test_search_returns_ranked_results(wiki_dir):
    results = search(wiki_dir, "links page", n=10)
    assert len(results) >= 1
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_search_result_fields(wiki_dir):
    results = search(wiki_dir, "page", n=5)
    r = results[0]
    assert isinstance(r.path, Path)
    assert isinstance(r.score, float)
    assert isinstance(r.snippet, str)


def test_search_cache_created(wiki_dir):
    search(wiki_dir, "page", n=5)
    cache = wiki_dir / ".lwt_cache" / "bm25_cache.json"
    assert cache.exists()


def test_search_cache_is_valid_json(wiki_dir):
    import json
    search(wiki_dir, "page", n=5)
    cache = wiki_dir / ".lwt_cache" / "bm25_cache.json"
    data = json.loads(cache.read_text(encoding="utf-8"))
    assert "pages" in data
    assert "corpus" in data


def test_search_empty_query_returns_empty(wiki_dir):
    assert search(wiki_dir, "", n=5) == []

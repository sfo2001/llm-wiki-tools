import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SearchResult:
    path: Path
    score: float
    snippet: str


def _tokenize(text: str) -> list[str]:
    """Lowercase, strip markdown syntax, split on whitespace."""
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\[\[.*?\]\]", "", text)
    text = re.sub(r"\*+|`+|_+|---+", " ", text)
    tokens = text.lower().split()
    return [re.sub(r"[^a-z0-9]", "", t) for t in tokens if re.sub(r"[^a-z0-9]", "", t)]


def _extract_snippet(text: str, query_tokens: list[str], length: int = 120) -> str:
    lower = text.lower()
    for token in query_tokens:
        idx = lower.find(token)
        if idx != -1:
            start = max(0, idx - 40)
            end = min(len(text), idx + length)
            return "..." + text[start:end].replace("\n", " ").strip() + "..."
    return text[:length].replace("\n", " ").strip() + "..."


class BM25Index:
    def __init__(self, wiki_dir: Path) -> None:
        self.wiki_dir = wiki_dir
        self._cache_path = wiki_dir / ".lwt_cache" / "bm25_cache.json"
        self._pages: list[Path] = []
        self._texts: list[str] = []
        self._index = None

    def _md_files(self) -> list[Path]:
        return sorted(
            p for p in self.wiki_dir.rglob("*.md")
            if not any(part.startswith(".") for part in p.parts)
        )

    def _needs_rebuild(self) -> bool:
        if not self._cache_path.exists():
            return True
        cache_mtime = self._cache_path.stat().st_mtime
        return any(
            p.stat().st_mtime > cache_mtime for p in self._md_files()
        )

    def build(self) -> None:
        from rank_bm25 import BM25Plus

        self._pages = self._md_files()
        self._texts = [
            p.read_text(encoding="utf-8", errors="replace") for p in self._pages
        ]
        tokenized = [_tokenize(t) for t in self._texts]
        self._index = BM25Plus(tokenized) if tokenized else None

        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_data = {
            "pages": [str(p) for p in self._pages],
            "corpus": tokenized,
        }
        self._cache_path.write_text(
            json.dumps(cache_data, ensure_ascii=False), encoding="utf-8"
        )

    def _load_cache(self) -> None:
        from rank_bm25 import BM25Plus

        data = json.loads(self._cache_path.read_text(encoding="utf-8"))
        self._pages = [Path(p) for p in data["pages"]]
        self._texts = [
            p.read_text(encoding="utf-8", errors="replace")
            for p in self._pages
            if p.exists()
        ]
        self._index = BM25Plus(data["corpus"])

    def _ensure_ready(self) -> None:
        if self._needs_rebuild():
            self.build()
        elif self._index is None:
            self._load_cache()

    def search(self, query: str, n: int = 10) -> list[SearchResult]:
        if not query.strip():
            return []
        self._ensure_ready()
        if self._index is None:
            return []
        tokens = _tokenize(query)
        if not tokens:
            return []
        scores = self._index.get_scores(tokens)
        ranked = sorted(
            zip(scores, self._pages, self._texts),
            key=lambda x: x[0],
            reverse=True,
        )
        results = []
        for score, path, text in ranked[:n]:
            if score <= 0:
                break
            results.append(SearchResult(
                path=path,
                score=float(score),
                snippet=_extract_snippet(text, tokens),
            ))
        return results

from pathlib import Path

import requests

from llm_wiki.deploy.base import WikiBackend


class ConfluenceBackend(WikiBackend):
    """Confluence DC backend stub. dry_run=True by default — prints what would happen."""

    def __init__(
        self,
        url: str,
        token: str,
        space: str,
        parent_title: str = "",
        dry_run: bool = True,
    ) -> None:
        self.url = url.rstrip("/")
        self.token = token
        self.space = space
        self.parent_title = parent_title
        self.dry_run = dry_run

    @property
    def target_name(self) -> str:
        return "confluence"

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}

    def _title_from_path(self, rel_path: str) -> str:
        p = Path(rel_path)
        parts = list(p.parts[:-1]) + [p.stem]
        return " ".join(part.replace("-", " ").title() for part in parts)

    def _page_id(self, title: str) -> str | None:
        resp = requests.get(
            f"{self.url}/rest/api/content",
            headers=self._headers(),
            params={"title": title, "spaceKey": self.space, "expand": "version"},
            timeout=30,
        )
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            if results:
                return results[0]["id"]
        return None

    @staticmethod
    def _escape_cdata(content: str) -> str:
        """Split any ']]>' sequence so it can't terminate the enclosing CDATA section."""
        return content.replace("]]>", "]]]]><![CDATA[>")

    def write_page(self, rel_path: str, content: str) -> None:
        """Push page to Confluence. Prints dry-run message if self.dry_run=True."""
        title = self._title_from_path(rel_path)
        if self.dry_run:
            print(f"[DRY-RUN] Would push: {title}")
            return
        safe = self._escape_cdata(content)
        storage = (
            "<ac:structured-macro ac:name='noformat'>"
            f"<ac:plain-text-body><![CDATA[{safe}]]></ac:plain-text-body>"
            "</ac:structured-macro>"
        )
        page_id = self._page_id(title)
        if page_id is None:
            payload = {
                "type": "page",
                "title": title,
                "space": {"key": self.space},
                "body": {"storage": {"value": storage, "representation": "storage"}},
            }
            resp = requests.post(
                f"{self.url}/rest/api/content",
                json=payload,
                headers={**self._headers(), "Content-Type": "application/json"},
                timeout=30,
            )
            resp.raise_for_status()
        else:
            ver_resp = requests.get(
                f"{self.url}/rest/api/content/{page_id}",
                headers=self._headers(),
                params={"expand": "version"},
                timeout=30,
            )
            ver_resp.raise_for_status()
            version = ver_resp.json()["version"]["number"] + 1
            payload = {
                "type": "page",
                "title": title,
                "version": {"number": version},
                "body": {"storage": {"value": storage, "representation": "storage"}},
            }
            resp = requests.put(
                f"{self.url}/rest/api/content/{page_id}",
                json=payload,
                headers={**self._headers(), "Content-Type": "application/json"},
                timeout=30,
            )
            resp.raise_for_status()

    def delete_page(self, rel_path: str) -> None:
        title = self._title_from_path(rel_path)
        if self.dry_run:
            print(f"[DRY-RUN] Would delete: {title}")

    def deploy(self, wiki_dir: Path) -> None:
        """Sync all wiki pages to Confluence. dry_run=True prints a diff only."""
        pages = sorted(
            p for p in wiki_dir.rglob("*.md")
            if not any(part.startswith(".") for part in p.parts)
        )
        if self.dry_run:
            print(
                f"[DRY-RUN] Would sync {len(pages)} pages to Confluence space '{self.space}':"
            )
            for p in pages:
                print(f"  {p.relative_to(wiki_dir)}")
            print("Pass --no-dry-run to lwt deploy --target confluence to push.")
            return
        for page_path in pages:
            self.write_page(
                str(page_path.relative_to(wiki_dir)),
                page_path.read_text(encoding="utf-8"),
            )

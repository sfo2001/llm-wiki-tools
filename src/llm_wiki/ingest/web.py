import requests


def _try_trafilatura(url: str) -> str | None:
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None
        result = trafilatura.extract(downloaded, output_format="markdown",
                                     include_links=False)
        return result.strip() if result and result.strip() else None
    except Exception:
        return None


def _try_requests(url: str) -> str:
    """Fetch URL and convert HTML to markdown via html2text."""
    import html2text
    response = requests.get(url, timeout=30,
                            headers={"User-Agent": "lwt/1.0 (llm-wiki-tools)"})
    if response.status_code != 200:
        raise RuntimeError(f"HTTP {response.status_code} fetching {url}")
    h = html2text.HTML2Text()
    h.ignore_links = True
    h.ignore_images = True
    return h.handle(response.text).strip()


def convert_web(url: str) -> tuple[str, str]:
    """Convert URL to (backend_name, markdown_body)."""
    md = _try_trafilatura(url)
    if md:
        return "web.trafilatura", md
    md = _try_requests(url)
    return "web.requests-html2text", md

import requests

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xhtml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def _try_trafilatura(url: str) -> str | None:
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url, config=_trafilatura_config())
        if not downloaded:
            return None
        result = trafilatura.extract(downloaded, output_format="markdown",
                                     include_links=False)
        return result.strip() if result and result.strip() else None
    except Exception:
        return None


def _trafilatura_config():
    try:
        from trafilatura.settings import use_config
        cfg = use_config()
        cfg.set("DEFAULT", "USER_AGENTS", _HEADERS["User-Agent"])
        return cfg
    except Exception:
        return None


def _try_requests(url: str) -> str:
    """Fetch URL and convert HTML to markdown via html2text."""
    import html2text
    response = requests.get(url, timeout=30, headers=_HEADERS)
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

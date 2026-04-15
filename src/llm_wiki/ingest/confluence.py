import html2text
import requests


def convert_confluence(url: str, token: str) -> tuple[str, str]:
    """Fetch a Confluence DC page via REST API and convert to markdown.

    url: REST API URL, e.g. https://wiki.example.com/rest/api/content/12345
    token: Confluence personal access token
    """
    api_url = url if "?expand=" in url else f"{url}?expand=body.storage"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    response = requests.get(api_url, headers=headers, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(
            f"Confluence API error {response.status_code} for {url}"
        )

    data = response.json()
    storage_html = data.get("body", {}).get("storage", {}).get("value", "")
    title = data.get("title", "")

    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True
    body_md = h.handle(storage_html).strip()

    md = f"# {title}\n\n{body_md}" if title else body_md
    return "confluence.rest-api", md

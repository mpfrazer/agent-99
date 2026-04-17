"""Fetch a URL and return its content as clean, readable text."""

import re

import requests

_DEFAULT_MAX_CHARS = 8000
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; agent-99/0.1; +https://github.com/agent-99)"}
_STRIP_TAGS = ["script", "style", "nav", "footer", "header", "aside", "noscript"]


def fetch_url(url: str, max_chars: int = _DEFAULT_MAX_CHARS) -> str:
    """Fetch a web page and return its content as clean readable text.

    Strips HTML markup, scripts, navigation, and boilerplate. Useful for reading
    careers pages, articles, and job listings. Returns up to max_chars characters.

    Args:
        url: The full URL to fetch (must start with http:// or https://).
        max_chars: Maximum characters to return (default 8000).
    """
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        return f"Failed to fetch {url}: {exc}"

    content_type = resp.headers.get("content-type", "")
    if "html" not in content_type and "text" not in content_type:
        return f"Unsupported content type '{content_type}' at {url}"

    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(_STRIP_TAGS):
            tag.decompose()
        raw = soup.get_text(separator="\n")
    except ImportError:
        raw = re.sub(r"<[^>]+>", " ", resp.text)

    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    text = "\n".join(lines)

    if len(text) > max_chars:
        text = text[:max_chars] + f"\n\n[Truncated — showing {max_chars} of {len(text)} chars]"

    return text or f"No readable text found at {url}"

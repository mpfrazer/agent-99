"""General web search via the Brave Search API."""

import os

import requests

_API_URL = "https://api.search.brave.com/res/v1/web/search"


def web_search(query: str, num_results: int = 10) -> str:
    """Search the web and return titles, URLs, and descriptions for the top results.

    Uses the Brave Search API. Requires the environment variable BRAVE_SEARCH_API_KEY.
    Get a free API key (2000 queries/month) at https://api.search.brave.com/.

    Args:
        query: The search query. Be specific for best results.
        num_results: Number of results to return (1–20, default 10).
    """
    api_key = os.environ.get("BRAVE_SEARCH_API_KEY", "").strip()
    if not api_key:
        return (
            "Brave Search is not configured. "
            "Set the BRAVE_SEARCH_API_KEY environment variable. "
            "Get a free key at https://api.search.brave.com/."
        )

    num_results = max(1, min(num_results, 20))

    try:
        resp = requests.get(
            _API_URL,
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": api_key,
            },
            params={"q": query, "count": num_results},
            timeout=10,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        return f"Search request failed: {exc}"

    data = resp.json()
    results = data.get("web", {}).get("results", [])

    if not results:
        return f'No results found for "{query}".'

    lines = [f'Search results for "{query}" ({len(results)} result(s)):\n']
    for i, r in enumerate(results, 1):
        title = r.get("title", "(no title)")
        url = r.get("url", "")
        desc = r.get("description", "").replace("\n", " ").strip()
        lines.append(f"{i}. {title}\n   {url}\n   {desc}")

    return "\n\n".join(lines)

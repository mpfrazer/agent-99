"""Google search tool: execute a query and return titles, summaries, and links."""

import os

import requests

_API_URL = "https://www.googleapis.com/customsearch/v1"
_MAX_PER_REQUEST = 10  # Google CSE hard limit per call


def search_google(query: str, num_results: int = 10) -> str:
    """Search Google and return titles, summaries, and links for the top results.

    Uses the Google Custom Search JSON API. Requires the environment variables
    GOOGLE_CSE_API_KEY (API key) and GOOGLE_CSE_ID (Custom Search Engine ID).

    Args:
        query: The search query. Be specific and use concise keywords for best results.
        num_results: Number of results to return (1–25, default 10).
    """

    api_key = os.environ.get("GOOGLE_CSE_API_KEY", "").strip()
    cse_id = os.environ.get("GOOGLE_CSE_ID", "").strip()

    if not api_key or not cse_id:
        return (
            "Google search is not configured. "
            "Set the GOOGLE_CSE_API_KEY and GOOGLE_CSE_ID environment variables. "
            "Get an API key at https://developers.google.com/custom-search/v1/introduction "
            "and create a search engine at https://programmablesearchengine.google.com/."
        )

    num_results = max(1, min(num_results, 25))

    items: list[dict] = []
    index = 1
    while len(items) < num_results:
        batch = min(_MAX_PER_REQUEST, num_results - len(items))
        params: dict[str, str | int] = {
            "key": api_key,
            "cx": cse_id,
            "q": query,
            "num": batch,
            "start": index,
        }
        try:
            resp = requests.get(_API_URL, params=params, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as exc:
            return f"Search request failed: {exc}"

        data = resp.json()

        if "error" in data:
            err = data["error"]
            return f"Google API error {err.get('code')}: {err.get('message')}"

        page_items = data.get("items", [])
        if not page_items:
            break

        items.extend(page_items)
        index += batch

    items = items[:num_results]

    if not items:
        return f'No results found for "{query}".'

    lines: list[str] = [f'Search results for "{query}" ({len(items)} result(s)):\n']
    for i, item in enumerate(items, 1):
        title = item.get("title", "(no title)")
        link = item.get("link", "")
        snippet = item.get("snippet", "").replace("\n", " ").strip()
        lines.append(f"{i}. {title}\n   {link}\n   {snippet}")

    return "\n\n".join(lines)

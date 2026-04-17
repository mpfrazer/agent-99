"""ATS-aware job scrapers for Greenhouse and Lever public careers boards."""

import re

import requests

_TIMEOUT = 15
_PROBE_TIMEOUT = 5


def scrape_greenhouse(company_id: str, title_filter: str = "") -> str:
    """Fetch job listings from a company's Greenhouse ATS board.

    Uses the public Greenhouse Jobs API — no auth required. The company_id is
    the slug visible in the careers URL, e.g. for boards.greenhouse.io/stripe
    the company_id is "stripe".

    Args:
        company_id: Greenhouse board slug (e.g. "stripe", "airbnb", "figma").
        title_filter: Optional keyword to filter job titles (case-insensitive).
    """
    url = f"https://boards-api.greenhouse.io/v1/boards/{company_id}/jobs"
    try:
        resp = requests.get(url, timeout=_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        return f"Failed to fetch Greenhouse board '{company_id}': {exc}"

    data = resp.json()
    jobs = data.get("jobs", [])

    if title_filter:
        jobs = [j for j in jobs if title_filter.lower() in j.get("title", "").lower()]

    if not jobs:
        suffix = f" matching '{title_filter}'" if title_filter else ""
        return f"No jobs found on Greenhouse board '{company_id}'{suffix}"

    lines = [f"Greenhouse — {company_id} ({len(jobs)} listing(s)):\n"]
    for j in jobs:
        title = j.get("title", "(no title)")
        location = j.get("location", {}).get("name", "") or "Not specified"
        link = j.get("absolute_url", "")
        lines.append(f"- {title} | {location}\n  {link}")

    return "\n".join(lines)


def scrape_lever(company_id: str, title_filter: str = "") -> str:
    """Fetch job listings from a company's Lever ATS board.

    Uses the public Lever Postings API — no auth required. The company_id is
    the slug in the jobs URL, e.g. for jobs.lever.co/netflix the company_id
    is "netflix".

    Args:
        company_id: Lever posting slug (e.g. "netflix", "dropbox", "vercel").
        title_filter: Optional keyword to filter job titles (case-insensitive).
    """
    url = f"https://api.lever.co/v0/postings/{company_id}?mode=json"
    try:
        resp = requests.get(url, timeout=_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        return f"Failed to fetch Lever board '{company_id}': {exc}"

    postings = resp.json()
    if not isinstance(postings, list):
        return f"Unexpected response format from Lever for '{company_id}'"

    if title_filter:
        postings = [p for p in postings if title_filter.lower() in p.get("text", "").lower()]

    if not postings:
        suffix = f" matching '{title_filter}'" if title_filter else ""
        return f"No postings found on Lever board '{company_id}'{suffix}"

    lines = [f"Lever — {company_id} ({len(postings)} listing(s)):\n"]
    for p in postings:
        title = p.get("text", "(no title)")
        cats = p.get("categories", {})
        location = cats.get("location", "")
        team = cats.get("team", "")
        link = p.get("hostedUrl") or p.get("applyUrl", "")
        meta = " | ".join(filter(None, [location, team]))
        lines.append(f"- {title} | {meta}\n  {link}")

    return "\n".join(lines)


def probe_careers_url(company_name: str, company_domain: str = "") -> str:
    """Probe common careers page URL patterns for a company and return which ones respond.

    Tries ATS-hosted boards (Greenhouse, Lever, Ashby) and standard domain paths
    (/careers, /jobs) using fast HEAD requests. Use this to discover where a company
    posts jobs before calling scrape_greenhouse, scrape_lever, or fetch_url.

    Args:
        company_name: The company's name (e.g. "Acme Corp", "stripe").
        company_domain: Optional primary domain (e.g. "acme.com"). If omitted, derived
            from company_name.
    """
    slug = re.sub(r"[^a-z0-9]+", "", company_name.lower())
    slug_hyphen = re.sub(r"[^a-z0-9]+", "-", company_name.lower()).strip("-")

    if company_domain:
        domain = company_domain.lower().lstrip("https://").lstrip("http://").strip("/")
    else:
        domain = f"{slug}.com"

    slugs = list(dict.fromkeys([slug, slug_hyphen]))  # deduplicate, preserve order
    candidates: list[str] = []
    for s in slugs:
        candidates += [
            f"https://boards.greenhouse.io/{s}",
            f"https://jobs.lever.co/{s}",
            f"https://jobs.ashbyhq.com/{s}",
        ]
    candidates += [
        f"https://{domain}/careers",
        f"https://{domain}/jobs",
        f"https://careers.{domain}/",
        f"https://jobs.{domain}/",
    ]

    working: list[str] = []
    for url in candidates:
        try:
            r = requests.head(url, timeout=_PROBE_TIMEOUT, allow_redirects=True)
            if r.status_code < 400:
                working.append(url)
        except requests.RequestException:
            pass

    if not working:
        return (
            f"No careers URLs found for '{company_name}'. "
            "Try web_search for '{company_name} careers jobs' to locate their page."
        )

    lines = [f"Live careers URLs for '{company_name}':\n"]
    for url in working:
        if "greenhouse.io" in url:
            slug_found = url.rstrip("/").split("/")[-1]
            lines.append(f"- {url}  →  use scrape_greenhouse('{slug_found}')")
        elif "lever.co" in url:
            slug_found = url.rstrip("/").split("/")[-1]
            lines.append(f"- {url}  →  use scrape_lever('{slug_found}')")
        else:
            lines.append(f"- {url}  →  use fetch_url('{url}')")

    return "\n".join(lines)

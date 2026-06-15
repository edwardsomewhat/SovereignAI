"""
Scout Tools — Research and asset collection for the Creative Scout.

web_search: SearXNG (local) primary, DuckDuckGo fallback
web_fetch: urllib scraping (works) + Firecrawl extraction (when configured)
"""
import json
import re
import urllib.request
import urllib.parse
import os
from pathlib import Path
from crewai.tools import tool

OUTPUT_DIR = Path("/home/fated/hermes-crew/output/scout")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── SearXNG config ──────────────────────────────────────────────────
SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://localhost:8080")
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY", "")


def _strip_html(html: str) -> str:
    """Crude but effective HTML text extraction."""
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text)
    text = html_unescape(text)
    return text.strip()[:8000]


def html_unescape(text: str) -> str:
    """Basic HTML entity decoding."""
    entities = {
        '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"',
        '&#39;': "'", '&apos;': "'", '&nbsp;': ' ',
        '&mdash;': '—', '&ndash;': '–', '&rsquo;': "'", '&lsquo;': "'",
        '&ldquo;': '"', '&rdquo;': '"', '&#x27;': "'",
    }
    for ent, char in entities.items():
        text = text.replace(ent, char)
    return text


def _searxng_search(query: str, max_results: int = 5) -> list[dict]:
    """Search via local SearXNG instance. Returns list of {title, url, snippet}."""
    params = urllib.parse.urlencode({
        "q": query,
        "format": "json",
        "categories": "general",
        "pageno": 1,
    })
    url = f"{SEARXNG_URL}/search?{params}"

    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Accept": "application/json",
    })

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return []  # fall through to DDG

    results = []
    for r in data.get("results", [])[:max_results]:
        results.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": (r.get("content", "") or "")[:300],
        })
    return results


def _ddg_search(query: str, max_results: int = 5) -> list[dict]:
    """Fallback: DuckDuckGo HTML search."""
    encoded = urllib.parse.quote(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded}"

    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    })

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception:
        return []

    link_pattern = re.findall(
        r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
        html, re.DOTALL
    )
    snippet_pattern = re.findall(
        r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
        html, re.DOTALL
    )

    results = []
    for i, (href, title) in enumerate(link_pattern[:max_results]):
        title_clean = _strip_html(title)
        if 'uddg=' in href:
            parsed = urllib.parse.urlparse(href)
            qs = urllib.parse.parse_qs(parsed.query)
            actual_url = qs.get('uddg', [href])[0]
        else:
            actual_url = href

        snippet = _strip_html(snippet_pattern[i]) if i < len(snippet_pattern) else ""
        results.append({
            "title": title_clean,
            "url": actual_url,
            "snippet": snippet[:300],
        })
    return results


def _firecrawl_fetch(url: str) -> str | None:
    """Fetch via Firecrawl API (returns clean markdown). Returns None if unavailable."""
    if not FIRECRAWL_API_KEY:
        return None

    api_url = "https://api.firecrawl.dev/v1/scrape"
    body = json.dumps({"url": url, "formats": ["markdown"]}).encode("utf-8")
    req = urllib.request.Request(api_url, data=body, headers={
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("data", {}).get("markdown", "")[:8000]
    except Exception:
        return None


# ── Tools ───────────────────────────────────────────────────────────

@tool("web_search")
def web_search(
    query: str,
    max_results: int = 5,
) -> str:
    """
    Search the web using local SearXNG (primary) with DuckDuckGo fallback.

    Use this to find real events, dates, venues, company names, and
    reference material. Returns titles, snippets, and URLs.

    Args:
        query: Search query. Be specific — include location, date, type.
            E.g., "ballet performances NYC June 2026 schedule"
        max_results: Number of results (1-10, default 5).

    Returns:
        Numbered search results with titles, snippets, and URLs.
    """
    if not query or not query.strip():
        return "❌ Empty search query — provide a specific search term."

    # Primary: SearXNG
    results = _searxng_search(query.strip(), max_results)

    # Fallback: DuckDuckGo
    if not results:
        results = _ddg_search(query.strip(), max_results)

    if not results:
        return "No results found. Try a different query."

    lines = [f'🔍 Search: "{query}"', f"Results: {len(results)}", ""]
    for i, r in enumerate(results):
        lines.append(f"{i + 1}. {r['title']}")
        lines.append(f"   {r['url']}")
        if r.get('snippet'):
            lines.append(f"   {r['snippet']}")
    return "\n".join(lines)


@tool("web_fetch")
def web_fetch(
    url: str,
) -> str:
    """
    Fetch and extract the text content of a web page.

    Uses Firecrawl (clean markdown) when FIRECRAWL_API_KEY is set,
    otherwise falls back to raw HTML scraping. Strips HTML, scripts,
    and styles — returns clean text (capped at 8000 chars).

    Args:
        url: The URL to fetch.

    Returns:
        Extracted text content from the page.
    """
    if not url or not url.strip():
        return "❌ Empty URL — provide a valid URL to fetch."

    url = url.strip()

    # Try Firecrawl first (clean markdown, no HTML)
    if FIRECRAWL_API_KEY:
        md = _firecrawl_fetch(url)
        if md:
            return "\n".join([
                f"📄 {url} (via Firecrawl)",
                f"Content length: {len(md)} chars",
                "─" * 60,
                md,
            ])

    # Fallback: raw HTML scraping
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    })

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "text/html" not in content_type and "text/plain" not in content_type:
                return f"⚠️ Not an HTML page (Content-Type: {content_type})"
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return f"❌ Fetch failed: {e}"

    text = _strip_html(html)

    return "\n".join([
        f"📄 {url}",
        f"Content length: {len(text)} chars",
        "─" * 60,
        text,
    ])

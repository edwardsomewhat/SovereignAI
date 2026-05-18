# User's Search Stack Architecture

This user runs three complementary search tools, each for a different use case. No need to ask which one to use — infer from context.

## Tier 1 — SearXNG (quick web search)
**When:** You need facts, recent info, definitions, or URLs to start from.
**What it returns:** 5 results with title, URL, snippet — fast and lightweight.
**Use for:** "What is X?", "Find me sources about Y", "Latest news on Z".
**Command:** `python3 /home/fated/.hermes/skills/web-search/searxng/scripts/search.py "query"`

## Tier 2 — Firecrawl (deep scrape)
**When:** You already have a URL and need the full content as markdown.
**What it returns:** Full page content stripped of ads/navigation.
**Use for:** Reading full articles, documentation pages, long-form content from URLs found via SearXNG.
**Status:** **Running** — firecrawl-simple Docker Compose stack is live on port 3002.
**LAN access:** `http://100.69.153.16:3002/v1/scrape` (other agents on Tailscale can use this).
**Command:** `python3 /home/fated/.hermes/skills/web-search/firecrawl/scripts/scrape.py "https://example.com"`

## Tier 3 — Kiwix (offline Wikipedia)
**When:** You need encyclopedic knowledge about history, science, philosophy, well-known entities — especially useful offline.
**What it returns:** Full Wikipedia articles.
**Use for:** "Tell me about Francis Bacon", "What is quantum mechanics?", dead-internet scenarios.
**Command:** Direct URL: `http://127.0.0.1:8081/content/wikipedia_en_all_maxi_2025-08/Article_Name`

## Flow Rules
1. **Prefer SearXNG for broad questions** — it's the fastest path to finding relevant URLs
2. **Feed SearXNG URLs into Firecrawl** — results from step 1 provide targets for deep extraction
3. **Use Kiwix for well-known topics** — if the answer is likely on Wikipedia, skip the web entirely
4. **Do not use Firecrawl for search** — it's a single-page extractor, not a search engine

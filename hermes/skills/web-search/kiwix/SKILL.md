---
name: kiwix
description: "Search and read the local offline Wikipedia database instantly."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Web, Search, Offline, Knowledge, Wikipedia]
---

# Kiwix Offline Wikipedia

A lightning-fast, offline repository of Wikipedia. Use this to instantly search and extract encyclopedic knowledge without the latency of a web search.

## Quick Reference

| Action | Command |
|--------|---------|
| Search Wikipedia | `python3 scripts/kiwix.py search "Quantum Mechanics"` |
| Read an Article | `python3 scripts/kiwix.py read "Quantum_mechanics"` |

## Usage

Use the provided Python script to query the local Kiwix server on port 8081.

```bash
# To search for articles
python3 scripts/kiwix.py search "neural networks"

# To read the full content of an article
python3 scripts/kiwix.py read "Artificial_neural_network"
```

## Pitfalls

### `read` script may fail to match article IDs
The `read` action finds articles by searching the Kiwix search page, then matching the ID against href patterns. This is brittle — article IDs from the `search` output sometimes don't match the internal href format. **Francis_Bacon** is a known casualty: searches return it but `read "Francis_Bacon"` fails.

**Fallback — direct URL access (always works):**
```bash
curl -s "http://127.0.0.1:8081/content/{database_name}/{Article_Name}" | python3 -c "
import sys, re
html = sys.stdin.read()
text = re.sub(r'<style.*?</style>', '', html, flags=re.DOTALL)
text = re.sub(r'<script.*?</script>', '', text, flags=re.DOTALL)
text = re.sub(r'<[^>]+>', ' ', text)
text = re.sub(r'\s+', ' ', text).strip()
print(text[:8000])
"
```
Where `{database_name}` is the zim file identifier (e.g. `wikipedia_en_all_maxi_2025-08`) and `{Article_Name}` uses underscores for spaces.

### Search/read script relies on HTML parsing
The scripts scrape the Kiwix HTML search page with regex. If the Kiwix version changes or the search page layout updates, parsing may break. The direct URL approach (above) is more stable.

## Reference files
- `references/direct-url-access.md` — detailed direct URL access guide with database name info
- `references/search-stack.md` (in searxng) — tiered search architecture (SearXNG → Firecrawl → Kiwix)

## Related skills
- `searxng` — web search for non-Wikipedia topics
- `firecrawl` — deep page scrape from specific URLs

## When to use this skill
- You need deep, factual encyclopedic knowledge about history, science, math, or well-known entities.
- Prefer this over `searxng` or `firecrawl` when you know the information is likely on Wikipedia, as it is completely local and instant.

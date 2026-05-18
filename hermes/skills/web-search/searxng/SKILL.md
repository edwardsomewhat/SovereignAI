---
name: searxng
description: "Quickly search the web for facts, news, and basic information using the local SearxNG instance."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Web, Search, Information]
---

# SearxNG Web Search

Perform lightning-fast, private web searches to find facts, answers, or news.

## Quick Reference

| Action | Command |
|--------|---------|
| Search the web | `python3 scripts/search.py "your query"` |

## Usage

Use the provided Python script to query SearxNG. It returns the top 5 results formatted nicely.

```bash
python3 scripts/search.py "latest advancements in quantum computing"
```

## When to use this skill
- You need to look up a quick fact (e.g., population of a city, a recent event, a simple definition).
- You need to find URLs to feed into `firecrawl` for deep reading.
- DO NOT use this if you need to read the full text of an article; it only provides snippets!

## Reference files
- `references/search-stack.md` — the full tiered search architecture (SearXNG → Firecrawl → Kiwix)

## Related skills
- `firecrawl` — deep page scrape from a URL
- `kiwix` — offline Wikipedia


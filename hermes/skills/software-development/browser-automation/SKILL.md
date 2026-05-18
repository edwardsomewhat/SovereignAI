---
name: browser-automation
description: "Install, configure, and verify Playwright + Chromium headless browser automation for use with Hermes Agent's `browser` toolset. Covers the Ubuntu 26.04 workaround and system integration."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [Browser, Playwright, Chromium, Automation, Setup]
---

# Browser Automation (Playwright + Chromium)

Installs and configures headless Chromium via Playwright for Hermes Agent's `browser` toolset (visual page interaction, screenshots, JS-heavy site scraping).

## Overview

The `browser` toolset in Hermes provides visual browser automation — different from:
- **SearXNG** → text search results (fast, lightweight)
- **Firecrawl** → deep HTML→Markdown extraction from URLs
- **Kiwix** → offline Wikipedia articles

Browser automation enables: clicking, form filling, navigation, screenshots, and interacting with JavaScript-heavy single-page apps.

## Quick Reference

| Action | Command |
|--------|---------|
| Install Playwright | `uv pip install 'playwright<1.50' --python $HERMES_VENV/bin/python3` |
| Install Chromium | `$HERMES_VENV/bin/python3 -m playwright install chromium` |
| Verify | `python3 -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); print(p.chromium)"` |
| Smoke test | `python3 -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(); pg=b.new_page(); pg.goto('https://example.com'); print(pg.title()); b.close(); p.stop()"` |
| Check Hermes toolset | `hermes tools list \| grep browser` |

## Installation

### 1. Install the Python package

The Hermes Agent venv is at `~/.hermes/hermes-agent/venv/`.

```bash
uv pip install 'playwright==1.49.0' --python ~/.hermes/hermes-agent/venv/bin/python3
```

> **Why 1.49.0?** Ubuntu 26.04 (Resolute Raccoon) is not in Playwright's officially supported platform list. Versions ≥1.57.0 reject it outright. v1.49.0's downloader doesn't perform this check and installs Chromium fine. Once Playwright publishes builds for Ubuntu 26.04, this pin can be removed.

### 2. Install the Chromium browser binary

```bash
~/.hermes/hermes-agent/venv/bin/python3 -m playwright install chromium
```

This downloads Chromium (~161 MB) and FFMPEG (~2.3 MB) to `~/.cache/ms-playwright/`.

### 3. Verify

```bash
# Quick smoke test
~/.hermes/hermes-agent/venv/bin/python3 -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://en.wikipedia.org/wiki/Francis_Bacon')
    print(f'Page title: {page.title()}')
    browser.close()
"
```

Expected output: `Page title: Francis Bacon - Wikipedia`

## Integration with Hermes

The `browser` toolset is already enabled in Hermes config. No additional configuration needed — Hermes auto-discovers Playwright when it's installed.

```bash
hermes tools list | grep browser
# Expected: ✅ enabled  browser  🌐 Browser Automation
```

## Pitfalls

- **Don't install the latest Playwright** on Ubuntu 26.04 — pin to 1.49.0 or earlier until upstream adds support
- The `playwright install chromium` command must be run after the pip install — the package alone doesn't include the browser binary
- Chromium downloads to `~/.cache/ms-playwright/` (~300 MB total with dependencies)
- If the browser toolset was enabled before Playwright was installed, you might need to restart the agent session for it to pick up the new dependency

## Reference files

- `references/playwright-ubuntu-26-04.md` — Ubuntu 26.04 workaround details and platform detection internals

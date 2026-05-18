---
name: firecrawl
description: "Extract the full Markdown content of a URL via Firecrawl — supports both a self-hosted local instance (skill script) and the Hermes Agent cloud plugin path."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Web, Scrape, Extract, Markdown, Diagnostic]
---

# Firecrawl Web Extractor

Use this to retrieve the complete Markdown content of any webpage. Firecrawl has **two paths** on this machine — know which one is active before using it.

## Quick Reference

| Action | Command / Path |
|--------|----------------|
| Scrape a URL (skill script) | `python3 scripts/scrape.py "https://example.com"` |
| Hermes Agent plugin | Uses `web.backend: firecrawl` in config.yaml (cloud API) |
| Check local server | `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3002/health` |
| Check API key | `grep FIRECRAWL_API_KEY ~/.hermes/.env` or `echo $FIRECRAWL_API_KEY` |
| Check config setup | `grep -A5 '^web:' ~/.hermes/config.yaml` |
| Check installed SDK | `pip show firecrawl-py` (in the hermes venv) |

## Three Paths

### Path A — Skill Script (self-hosted local instance)
The `scrape.py` script in this skill's `scripts/` directory targets `http://127.0.0.1:3002/v1/scrape`. It requires a running local Firecrawl instance (see Path C for setup). Auth: `Bearer empty`.

**Use when:** You want a standalone scrape without going through Hermes tool dispatch.

### Path B — Hermes Agent Plugin (cloud API)
Hermes config has `web.backend: firecrawl` which uses the `firecrawl-py` SDK (v4.17.0 installed in the hermes venv) to talk to `https://api.firecrawl.dev`. Requires `FIRECRAWL_API_KEY` in `~/.hermes/.env`.

**Use when:** You're inside Hermes Agent tool calls and want web scraping as part of the agent loop.

### Path C — firecrawl-simple Docker Compose (self-hosted, preferred)
[firecrawl-simple](https://github.com/devflowinc/firecrawl-simple) is a stripped-down, stable fork of Firecrawl optimized for self-hosting. No billing, no AI features, no cloud dependency. Data stays entirely local.

**Location:** `/home/fated/firecrawl-simple/`
**API endpoint:** `http://127.0.0.1:3002/v1/scrape` (or via Tailscale IP for LAN access)

**Architecture (3 services):**
| Service | Role |
|---------|------|
| `api` | Main Firecrawl API server (`trieve/firecrawl` Docker image, built from `apps/api/`) |
| `puppeteer-service` | JS rendering for dynamic pages (built from `apps/puppeteer-service-ts/`) |
| `redis` | Job queue (`redis:alpine`) |

**Setup (already done):**
```bash
cd /home/fated/firecrawl-simple
# .env already created with: PORT=3002, HOST=0.0.0.0, NUM_WORKERS_PER_QUEUE=8
# Images pulled or built
sg docker -c "docker compose up -d"    # start the stack
sg docker -c "docker compose down"     # stop it
sg docker -c "docker compose logs -f"  # view logs
```

**Verification:**
```bash
curl -s -X POST http://127.0.0.1:3002/v1/scrape \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://en.wikipedia.org/wiki/Francis_Bacon", "formats": ["markdown"]}'
```

**Systemd service (auto-start on boot):**
A systemd unit is installed at `/etc/systemd/system/firecrawl.service` to bring the stack up automatically on system boot and provide clean service management.

```bash
sudo systemctl status firecrawl    # check if running
sudo systemctl start firecrawl     # start the stack
sudo systemctl stop firecrawl      # stop the stack
sudo systemctl restart firecrawl   # restart all containers
sudo journalctl -u firecrawl -f    # follow logs
```

The service runs `docker compose up -d` as user `fated` in group `docker`. Containers also have `restart: unless-stopped` so Docker restarts them automatically if they crash.

**Multi-agent LAN access:**
Other agents on the same Tailscale network use:
```
http://100.69.153.16:3002/v1/scrape
```
No API key needed — the self-hosted instance accepts requests directly. This replaces the need for each agent to have their own Firecrawl or cloud API key.

**Pitfalls:**
- `sudo docker` doesn't work without the password; use `sg docker -c "command"` instead (user was added to `docker` group but the group takes effect on next login)
- The firecrawl-py client SDK (Path B) and the firecrawl-simple server (Path C) are independent — you can use either or both
- Path B requires FIRECRAWL_API_KEY — skip it if you're only using Path C
- The Hermes plugin (`web.backend: firecrawl`) is set to use the cloud API; for self-hosted, use the skill scrape script directly instead
- **Docker DNS hostname:** The compose service is `puppeteer-service`, not `playwright-service`. The `PLAYWRIGHT_MICROSERVICE_URL` env var MUST be `http://puppeteer-service:3000/scrape` (includes the `/scrape` path). Using the wrong hostname or omitting `/scrape` silently returns empty content on all requests.
- **Corepack on Node 20:** If the API container crashes with `Cannot find matching keyid`, add `ENV COREPACK_ENABLE_STRICT=0` to `apps/api/Dockerfile` after `RUN corepack enable`, then `docker compose build api worker`.
- **API param diff:** firecrawl-simple rejects `onlyMainContent`. Use only `formats: ["markdown"]`.
- **Ubuntu 26.04 + Playwright:** Latest Playwright doesn't support Ubuntu 26.04. Use `playwright==1.49.0` for Chromium support.

## Diagnostics

If Firecrawl isn't working, run these checks in order:

1. **Which path are you on?**
   - If via `scrape.py` → need a local server on port 3002
   - If via Hermes plugin → need `FIRECRAWL_API_KEY` set

2. **Local server check:**
   ```bash
   curl -s http://127.0.0.1:3002/v1/scrape
   # Connection refused = server not running
   # Check Docker: docker ps | grep firecrawl
   # Check for Node.js server: ps aux | grep firecrawl
   ```

3. **Cloud API key check:**
   ```bash
   grep FIRECRAWL_API_KEY ~/.hermes/.env
   ```
   If commented out or empty, the plugin is wired but can't authenticate.

4. **Empty-response debugging** (API returns `success: true` but `markdown: ""`):
   The worker completed in ~100ms — too fast for real scraping. This means the API never reached a live scraper. Check these in order:

   a) **DNS hostname resolution** — containers on the `backend` network resolve each other by compose service name:
      ```bash
      docker exec firecrawl-worker-1 node -e "const http = require('http'); http.get('http://puppeteer-service:3000', (r) => { let d=''; r.on('data', c=>d+=c); r.on('end', ()=>console.log('Reachable:', d.substring(0,50))); }).on('error', e=>console.log('DNS fail:', e.message));"
      ```
      The compose service is named `puppeteer-service`, not `playwright-service`. If you see `ENOTFOUND`, the hostname is wrong.

   b) **Endpoint path** — the puppeteer service exposes `/scrape`, not the root. `PLAYWRIGHT_MICROSERVICE_URL` must be `http://puppeteer-service:3000/scrape` (full path included).

   c) **Environment propagation** — verify the var reached the container:
      ```bash
      docker exec firecrawl-worker-1 node -e "console.log(process.env.PLAYWRIGHT_MICROSERVICE_URL)"
      ```

   d) **Scrape the page directly from inside the worker** to isolate the scraper from the queue:
      ```bash
      docker exec firecrawl-puppeteer-service-1 node -e 'const http = require("http"); const d = JSON.stringify({url: "https://example.com"}); const r = http.request({hostname:"localhost",port:3000,path:"/scrape",method:"POST",headers:{"Content-Type":"application/json","Content-Length":d.length}},(res) => { let b=""; res.on("data",c=>b+=c); res.on("end",()=>{try{const j=JSON.parse(b);console.log("Content:",j.content?.length||0,"Status:",j.pageStatusCode)}catch(e){console.log("Raw:",b.slice(0,100))}}); }); r.write(d); r.end();'
      ```
      If this returns content, the puppeteer service is fine and the issue is in the queue-worker pipeline (env var not propagating, or wrong endpoint path in the compose config).

5. **SDK check:**
   ```bash
   source ~/.hermes/hermes-agent/venv/bin/activate
   python -c "from firecrawl import FirecrawlApp; print('OK')"
   pip show firecrawl-py
   ```

## Usage

### Skill script
```bash
python3 scripts/scrape.py "https://docs.docker.com/compose/"

# Summary mode (LLM-extracted)
python3 scripts/scrape.py "https://example.com" --summary

# Custom extract
python3 scripts/scrape.py "https://example.com" --extract "List all pricing tiers"
```

### Hermes plugin (inside agent loop)
The plugin is auto-loaded when `web.backend: firecrawl` is set and `FIRECRAWL_API_KEY` is present. No manual invocation needed — it's the backend for Hermes' web tool calls.

## When to use this skill
- You ALREADY have a URL (perhaps from `searxng`) and you need to deeply analyze its full content.
- You need to read documentation, an article, or a blog post.
- Firecrawl is missing or not responding — run the diagnostics section first.
- This is a slow operation, DO NOT use it for a broad search.

## Reference files
- `references/setup-diagnostics.md` — full diagnostic checklist from actual session
- `references/firecrawl-simple-docker.md` — Docker Compose config details and env reference
- `references/search-stack.md` (in searxng) — tiered search architecture (SearXNG → Firecrawl → Kiwix)

## Related skills
- `searxng` — web search to find URLs
- `kiwix` — offline Wikipedia fallback

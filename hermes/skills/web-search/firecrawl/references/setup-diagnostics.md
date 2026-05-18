# Firecrawl Setup Diagnostics

Last updated: 2026-05-16 (post setup session)

## Current State

| Component | Location | Status |
|-----------|----------|--------|
| firecrawl-py SDK | ~/.hermes/hermes-agent/venv/lib/python3.11/site-packages/firecrawl/ | Installed v4.17.0 |
| firecrawl-simple stack | /home/fated/firecrawl-simple/ | **Docker Compose running on port 3002** |
| Skill scrape script | ~/.hermes/skills/web-search/firecrawl/scripts/scrape.py | Points at localhost:3002 (now working) |
| Hermes config | ~/.hermes/config.yaml → `web.backend: firecrawl` | Configured for cloud API, not local |
| API key (cloud) | ~/.hermes/.env → `# FIRECRAWL_API_KEY=` | **Commented out** — not needed for self-hosted |
| Hermes browser toolset | Config → `browser` toolset enabled | Playwright 1.49.0 + Chromium 131 installed |

## Docker group workaround

User `fated` was added to `docker` group, but group changes don't take effect until next login.
**Use `sg docker -c "command"`** to run Docker commands in current shell sessions.

## firecrawl-simple stack

```
firecrawl-simple/
├── apps/
│   ├── api/              # Main API server
│   └── puppeteer-service-ts/  # JS rendering
├── docker-compose.yaml   # 3 services: api, puppeteer-service, redis
└── .env                  # PORT=3002, HOST=0.0.0.0, NUM_WORKERS_PER_QUEUE=8
```

Commands:
```bash
sg docker -c "cd ~/firecrawl-simple && docker compose up -d"     # start
sg docker -c "cd ~/firecrawl-simple && docker compose down"       # stop
sg docker -c "cd ~/firecrawl-simple && docker compose logs -f"    # logs
```

## Tailscale access

The firecrawl API is available on the tailnet at:
- IPv4: `http://100.69.153.16:3002`
- IPv6: `http://[fd7a:115c:a1e0::5e32:9910]:3002`

Other agents on the LAN can use this URL directly — no API key needed.

## Training data collector (separate stack)

Also running on the same host:
- `training_data_db` — PostgreSQL 15 on port 5432 (data at /mnt/hermes_data/collector/pgdata/)
- `training_data_proxy` — FastAPI proxy on port 4000, captures conversations to vLLM in ShareGPT format
- Stack location: `/mnt/hermes_data/collector/docker-compose.yml`
- Proxy currently returns errors because vLLM is not running on port 8020

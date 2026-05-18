# firecrawl-simple Docker Compose Reference

Repo: https://github.com/devflowinc/firecrawl-simple (656 stars)
Local: `/home/fated/firecrawl-simple/`

## Architecture (3 services)

```yaml
services:
  puppeteer-service:    # JS rendering (built from apps/puppeteer-service-ts/)
    image: trieve/puppeteer-service-ts  # must be built from source, not on Docker Hub
    environment:
      PORT: 3000
    networks: [backend]

  api:                  # Main API server
    image: trieve/firecrawl  # pre-built, pulls from Docker Hub
    ports: ["3002:3002"]     # exposed to host
    depends_on: [redis, puppeteer-service]
    environment:
      - REDIS_URL=redis://redis:6379
      - PLAYWRIGHT_MICROSERVICE_URL=http://puppeteer-service:3000
      - PORT=3002
      - HOST=0.0.0.0
    command: ["pnpm", "run", "start:production"]
    networks: [backend]

  redis:                # Job queue
    image: redis:alpine
    command: redis-server --bind 0.0.0.0
    networks: [backend]

networks:
  backend:
    driver: bridge
```

## .env file

```
PORT=3002
HOST=0.0.0.0
NUM_WORKERS_PER_QUEUE=8
BULL_AUTH_KEY=@
```

## Pitfalls (from actual setup)

### DNS hostname: puppeteer-service, not playwright-service
The Docker Compose service is named `puppeteer-service`. The `PLAYWRIGHT_MICROSERVICE_URL` env var resolves to `http://puppeteer-service:3000` internally via Docker DNS. Using `playwright-service` as hostname will fail with `getaddrinfo ENOTFOUND`.

### /scrape path suffix is required
The `PLAYWRIGHT_MICROSERVICE_URL` must end with `/scrape`:
```
PLAYWRIGHT_MICROSERVICE_URL=http://puppeteer-service:3000/scrape
```
The puppeteer service exposes `POST /scrape`, not at the root. Without the path, the API falls through to silent empty responses (~100ms jobs with no content).

### COREPACK_ENABLE_STRICT=0 for Node 20
The `trieve/firecrawl` image uses Node 20 with corepack, which performs strict pnpm signature verification. On newer corepack versions, this fails with `Cannot find matching keyid`. Fix: add `ENV COREPACK_ENABLE_STRICT=0` to `apps/api/Dockerfile` after the `RUN corepack enable` line, then rebuild with `docker compose build api worker`.

### onlyMainContent not supported by firecrawl-simple
The API rejects `onlyMainContent` as an unrecognized key. Use only `formats: ["markdown"]` in the request body.

### Wikipedia blocks fetch scrapers (403)
Direct axios/fetch scrapers get 403 from Wikipedia because they lack a proper User-Agent header. The puppeteer service handles this correctly with real browser UA strings — but only if the `PLAYWRIGHT_MICROSERVICE_URL` points to the correct hostname + path (see above).

## API endpoints

Once running, Firecrawl exposes:
- `POST /v1/scrape` — scrape a single URL
- `POST /v1/crawl` — crawl a site (returns job ID)
- `GET /v1/crawl/<id>` — check crawl status
- `GET /admin/@/queues` — Bull Queue Manager UI

### Example scrape call

```bash
curl -s -X POST http://127.0.0.1:3002/v1/scrape \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://example.com", "formats": ["markdown"]}'
```

## Building

The puppeteer-service must be built from source (no pre-built image available):

```bash
sg docker -c "cd ~/firecrawl-simple && docker compose build puppeteer-service"
```

This downloads Chromium (~175MB) and installs npm dependencies inside the container.
Takes 3-5 minutes on first build.

## Base image pulled separately

The main Firecrawl Docker image was also pulled:
- `ghcr.io/firecrawl/firecrawl:latest` (used for the full stack, not firecrawl-simple)

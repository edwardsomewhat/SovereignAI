# User's Training Data Capture Deployment

## Containers (both running)

| Container | Image | Port | Purpose |
|-----------|-------|------|---------|
| `training_data_db` | `postgres:15-alpine` | 5432 | PostgreSQL database |
| `training_data_proxy` | `collector-proxy` (custom build) | 4000 | FastAPI proxy + capture |

## Source Files

All at `/mnt/hermes_data/collector/`:

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Defines both containers, host networking |
| `Dockerfile` | Builds the proxy image (Python 3.11-slim + deps) |
| `proxy.py` | FastAPI app — captures all paths, streams responses, saves to DB |
| `requirements.txt` | fastapi, uvicorn, httpx, psycopg2-binary |
| `pgdata/` | PostgreSQL data directory (root-owned) |

## How It Works

1. `proxy.py` uses FastAPI with a catch-all route (`/{path:path}`)
2. It builds a request to the vLLM URL (`http://127.0.0.1:8020`)
3. On streaming response (SSE), it collects the full text
4. After the stream completes, it saves the conversation as ShareGPT format
5. ShareGPT format: `{"conversations": [{"from": "human"/"gpt", "value": "..."}]}`

## Current Status

- **vLLM is NOT running** on port 8020 — proxy returns HTTP errors
- PostgreSQL has been running for ~26 hours (as of 2026-05-16)
- The proxy is on the `host` Docker network, so `DB_HOST=127.0.0.1` resolves correctly
- No conversations have been captured yet (vLLM was never pointed at 8020)

## To Use Later

1. Start vLLM on port 8020
2. Point LLM clients at `http://127.0.0.1:4000/v1/chat/completions` instead of port 8020
3. Every completed stream gets saved to PostgreSQL automatically
4. Export as JSONL for fine-tuning: `psql -h 127.0.0.1 -U collector -d training_data -t -A -c "SELECT sharegpt_format::text FROM interactions;" > training_data.jsonl`

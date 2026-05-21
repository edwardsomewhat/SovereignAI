---
name: training-data-capture
description: "Capture LLM conversation data for fine-tuning — intercept proxy that records requests/responses to PostgreSQL in ShareGPT format, ready for Axolotl/LLaMA-Factory."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Training, Data, Capture, ShareGPT, FineTuning]
---

# Training Data Capture

Capture conversations with an LLM (vLLM, OpenAI-compatible API) and save them to PostgreSQL in **ShareGPT format** — the native format for Axolotl, LLaMA-Factory, and most fine-tuning frameworks.

## Architecture

```
Client (Hermes / other apps) 
    → port 4000 (FastAPI proxy)
        → proxies request to vLLM on port 8020
        → captures full conversation on response
            → saves to PostgreSQL (ShareGPT format)
```

The proxy sits between your LLM clients and vLLM. Point your apps at port 4000 instead of directly at vLLM, and every conversation is silently captured.

## Services

| Container | Image | Port | Role |
|-----------|-------|------|------|
| `training_data_db` | `postgres:15-alpine` | 5432 | Data storage, persistent volume at `/mnt/hermes_data/collector/pgdata/` |
| `training_data_proxy` | `collector-proxy` (built locally) | 4000 (host mode) | Intercepts vLLM calls, captures ShareGPT, forwards to vLLM |

## Location

```
/mnt/hermes_data/collector/
├── docker-compose.yml    # 2 services: db + proxy
├── Dockerfile            # Builds the proxy image
├── proxy.py              # FastAPI app -- the actual capture logic
├── requirements.txt      # fastapi, uvicorn, httpx, psycopg2-binary
└── pgdata/               # PostgreSQL data volume (persistent)
```

## Quick Reference

| Action | Command |
|--------|---------|
| Start stack | `sg docker -c "cd /mnt/hermes_data/collector && docker compose up -d"` |
| Stop stack | `sg docker -c "cd /mnt/hermes_data/collector && docker compose down"` |
| Check containers | `sg docker -c "docker ps --filter name=training_data"` |
| Proxy logs | `sg docker -c "docker logs training_data_proxy -f"` |
| View DB count | `sg docker -c "docker exec training_data_db psql -U collector -d training_data -c 'SELECT count(*) FROM interactions;'"` |
| View sample | `sg docker -c "docker exec training_data_db psql -U collector -d training_data -c '\x' -c 'SELECT sharegpt_format FROM interactions LIMIT 1;'"` |
| Export all data | `sg docker -c "docker exec training_data_db psql -U collector -d training_data -c \"SELECT json_agg(sharegpt_format) FROM interactions;\" -t -A > collected_conversations.json"` |

## Database Schema

```sql
CREATE TABLE interactions (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    request_payload JSONB,
    response_payload JSONB,
    sharegpt_format JSONB
);
```

The `sharegpt_format` column stores conversations in ShareGPT format:
```json
{
  "conversations": [
    {"from": "human", "value": "user message"},
    {"from": "gpt", "value": "assistant response"}
  ]
}
```

## How It Works

1. Point LLM clients at `http://<host>:4000/v1/chat/completions` instead of vLLM directly
2. The proxy forwards the request to vLLM at `http://127.0.0.1:8020/v1/chat/completions`
3. As the streaming response arrives, the proxy collects all content chunks
4. After the stream ends, it assembles the conversation into ShareGPT format
5. Saves to PostgreSQL — one row per conversation

## When to Use

- You want to collect conversation data for fine-tuning an LLM
- You need to build a training dataset in ShareGPT format from live inference
- You want to audit or inspect a vLLM instance's conversation history
- You need to export collected conversations for Axolotl, LLaMA-Factory, or other training frameworks

## Pitfalls

- **vLLM must be running on port 8020** for the proxy to forward requests. Without vLLM, the proxy returns "Internal Server Error"
- The proxy uses `network_mode: "host"` in Docker — this lets it reach vLLM on `127.0.0.1:8020` and PostgreSQL on `127.0.0.1:5432`
- PostgreSQL data persists at `/mnt/hermes_data/collector/pgdata/` — back up this directory to preserve collected data
- The proxy captures the raw request payload as-is, including system prompts and metadata. Filter/purge data before training
- The proxy expects `VLLM_URL` to be set (defaults to `http://127.0.0.1:8020`)
- DB credentials: User=`collector`, Password=`collector_password`, Database=`training_data`
- Both containers use `host` network mode — accessible on the LAN via Tailscale IP

## Reference files
- `references/user-setup.md` — the actual deployment on this machine
- `references/session-mining-pipeline.md` — Sovereign session mining pipeline (post-hoc curation from Hermes session DB; separate from the proxy capture system)

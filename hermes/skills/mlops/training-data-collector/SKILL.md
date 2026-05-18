---
name: training-data-collector
description: "Manage the ShareGPT-format conversation capture pipeline — a FastAPI proxy + PostgreSQL backend that intercepts vLLM API calls and stores conversation data for fine-tuning."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [Training, Data, Collection, Fine-tuning, ShareGPT, PostgreSQL]
---

# Training Data Collector

A self-hosted conversation capture pipeline that sits between LLM clients and a vLLM inference server. Every request/response pair is logged to PostgreSQL in **ShareGPT format** — the standard format used by Axolotl, LLaMA-Factory, and most fine-tuning frameworks.

## Architecture

```
Client to Port 4000 to Proxy (FastAPI) to vLLM (port 8020)
                         |
                   PostgreSQL (training_data_db)
                   Schema: interactions
                   - request_payload  (JSONB)
                   - response_payload (JSONB)
                   - sharegpt_format  (JSONB)
```

### Services

| Container | Image | Port | Role |
|-----------|-------|------|------|
| `training_data_db` | `postgres:15-alpine` | 5432 | Data storage, persistent volume at `/mnt/hermes_data/collector/pgdata/` |
| `training_data_proxy` | `collector-proxy` (built locally) | 4000 (host mode) | Intercepts vLLM calls, captures ShareGPT, forwards to vLLM |

## Location

```
/mnt/hermes_data/collector/
- docker-compose.yml    # 2 services: db + proxy
- Dockerfile            # Builds the proxy image
- proxy.py              # FastAPI app -- the actual capture logic
- requirements.txt      # fastapi, uvicorn, httpx, psycopg2-binary
- pgdata/               # PostgreSQL data volume (persistent)
```

## Commands

```bash
# Start
sg docker -c "cd /mnt/hermes_data/collector && docker compose up -d"

# Stop
sg docker -c "cd /mnt/hermes_data/collector && docker compose down"

# View logs
sg docker -c "docker logs training_data_proxy"

# Check database
sg docker -c "docker exec training_data_db psql -U collector -d training_data -c 'SELECT count(*) FROM interactions;'"

# Export collected data (ShareGPT format)
sg docker -c "docker exec training_data_db psql -U collector -d training_data -c \"SELECT json_agg(sharegpt_format) FROM interactions;\" -t -A > collected_conversations.json"
```

## Database Schema

The `interactions` table is auto-created on startup:

```sql
CREATE TABLE IF NOT EXISTS interactions (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    request_payload JSONB,
    response_payload JSONB,
    sharegpt_format JSONB
);
```

The `sharegpt_format` column stores arrays in this shape:
```json
{
  "conversations": [
    {"from": "system", "value": "You are..."},
    {"from": "human", "value": "User's question"},
    {"from": "gpt", "value": "Model's response"}
  ]
}
```

## How It Works

1. Point LLM clients at `http://<host>:4000/v1/chat/completions` instead of vLLM directly
2. The proxy forwards the request to vLLM at `http://127.0.0.1:8020/v1/chat/completions`
3. As the streaming response arrives, the proxy collects all content chunks
4. After the stream ends, it assembles the conversation into ShareGPT format
5. Saves to PostgreSQL -- one row per conversation

## Pitfalls

- **vLLM must be running on port 8020** for the proxy to forward requests. Without vLLM, the proxy returns "Internal Server Error".
- The proxy uses `network_mode: "host"` in Docker, so it shares the host's network stack -- this lets it reach vLLM on `127.0.0.1:8020` and PostgreSQL on `127.0.0.1:5432`.
- PostgreSQL data is on a Docker volume mapped to `/mnt/hermes_data/collector/pgdata/`. Backup this directory to preserve collected data.
- The proxy does NOT strip system prompts or metadata -- it captures the raw request payload as-is. Filter/purge data before training.

## When to Use This Skill

- You want to collect conversation data for fine-tuning an LLM
- You need to build a training dataset in ShareGPT format from live inference
- You want to audit or inspect a vLLM instance's conversation history

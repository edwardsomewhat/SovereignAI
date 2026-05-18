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

## Quick Reference

| Action | Command |
|--------|---------|
| Check containers | `sg docker -c "docker ps --filter name=training_data"` |
| View DB | `psql -h 127.0.0.1 -U collector -d training_data -c "SELECT count(*) FROM interactions;"` |
| View sample | `psql -h 127.0.0.1 -U collector -d training_data -c "\x" -c "SELECT sharegpt_format FROM interactions LIMIT 1;"` |
| Restart stack | `cd /mnt/hermes_data/collector && sg docker -c "docker compose up -d"` |
| Proxy logs | `sg docker -c "docker logs training_data_proxy -f"` |

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

## Notes

- The proxy expects `VLLM_URL` to be set (defaults to `http://127.0.0.1:8020`)
- Currently vLLM is NOT running on port 8020 — proxy returns errors until vLLM starts
- PostgreSQL data persists at `/mnt/hermes_data/collector/pgdata/`
- Both containers use `host` network mode — accessible on the LAN via Tailscale IP
- Password: `collector_password`, Database: `training_data`, User: `collector`

## Reference files
- `references/user-setup.md` — the actual deployment on this machine

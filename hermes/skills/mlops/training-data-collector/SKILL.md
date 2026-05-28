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

The Docker collector stack (proxy + PostgreSQL at /mnt/hermes_data/collector/) is aspirational — NOT YET DEPLOYED. What IS running is the session mining pipeline:

```
/home/fated/training_pipeline.py           # 3-stage capture→summarize→grade
/home/fated/.hermes/training_data/
├── raw/                                   # Stage 1: session text extracts
├── processed/                             # Stage 2: LLM-summarized entries
├── curated/                               # Stage 3: A/B-graded training data
└── pipeline_state.json                    # Tracks last processed session
```

Cron runs every 4 hours:
```
0 */4 * * * python /home/fated/training_pipeline.py all
```

### Docker Stack (aspirational — NOT deployed)

```
/mnt/hermes_data/collector/
- docker-compose.yml    # 2 services: db + proxy
- Dockerfile            # Builds the proxy image
- proxy.py              # FastAPI app -- the actual capture logic
- requirements.txt      # fastapi, uvicorn, httpx, psycopg2-binary
- pgdata/               # PostgreSQL data volume (persistent)
```

## Quick Reference

### Session Mining Pipeline (ACTIVE)

| Action | Command |
|--------|---------|
| Initialize directories | `mkdir -p ~/.hermes/training_data/{raw,processed,curated}` |
| Run all stages | `python /home/fated/training_pipeline.py all` |
| Capture only | `python /home/fated/training_pipeline.py capture` |
| Summarize only | `python /home/fated/training_pipeline.py summarize` |
| Grade only | `python /home/fated/training_pipeline.py grade` |
| View curated | `ls ~/.hermes/training_data/curated/` |
| Check pipeline log | `tail ~/.hermes/training_data/pipeline.log` |
| Check for LLM errors | `grep LLM_ERROR ~/.hermes/training_data/pipeline.log` |
| CPU/GPU diagnosis | See `references/ollama-cpu-diagnosis.md` |

### Docker Collector Stack (aspirational — NOT deployed)

| Action | Command |
|--------|---------|
| Check containers | `docker ps --filter name=training_data` |
| View DB row count | `docker exec training_data_db psql -U collector -d training_data -c 'SELECT count(*) FROM interactions;'` |
| Restart stack | `cd /mnt/hermes_data/collector && docker compose up -d` |
| Proxy logs | `docker logs training_data_proxy -f` |

### Current Deployment Status

**Session Mining Pipeline (ACTIVE on sovereign):**
- Runs via cron every 4 hours on sovereign
- LLM: hq-ai Ollama hermes3:8b at http://100.84.92.74:11434
- Output: ~/.hermes/training_data/curated/ — A/B-graded training examples
- First-time setup: `mkdir -p ~/.hermes/training_data/{raw,processed,curated}` before running capture

**Docker Collector Stack (NOT deployed):**
- Proxy expects vLLM on port 8020
- PostgreSQL data persists at `/mnt/hermes_data/collector/pgdata/`
- Credentials: Password `collector_password`, Database `training_data`, User `collector`

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

## Alternative: Session Mining Pipeline (Post-hoc Capture)

Instead of intercepting API calls at the proxy level (real-time), a post-hoc approach mines Hermes session transcripts for training data. This pipeline extracts session JSONs to markdown, summarizes them with a local LLM, grades quality, and curates the best entries.

See `references/session-mining-pipeline.md` for the full pipeline spec (capture → summarize → grade → curate). Run via `python training_pipeline.py all` — curated data feeds into graphify and the RAG database. Cron runs every 4 hours on both nodes.

## Pitfalls

### Session Mining Pipeline

- **Directories must exist before first run.** The session mining pipeline writes to `~/.hermes/training_data/{raw,processed,curated}/` but does not auto-create them. If directories are missing, the cron job fails silently — run `mkdir -p ~/.hermes/training_data/{raw,processed,curated}` once before the first capture.

- **128K context window causes CPU thrashing.** The Ollama server on hq-ai defaults to `OLLAMA_CONTEXT_LENGTH=131072`. For summarization/grading tasks, this creates an enormous KV cache that forces 50% of model layers onto CPU — the pipeline runs at 12+ CPU load with near-zero GPU utilization. Each `/api/generate` call takes 35-70 seconds instead of seconds.

  **Fix:** The pipeline passes `num_ctx: 32768` per-request in the Ollama options. Ollama respects per-request context caps — the server keeps 128K globally for other workloads, but pipeline calls use 32K, fitting all layers in GPU VRAM.

- **Grade parsing is fragile.** Ollama may return `"A."` or `"Grade: B"` instead of bare `"A"`. Without robust extraction, A/B sessions get mis-classified as C/D and deleted. The pipeline uses `re.search(r'[A-D]', grade_raw)` to extract just the letter.

- **LLM errors cause re-processing loops.** If `call_ollama` returns an error during summarize (timeout, model not loaded), the raw file stays in `raw/` and gets retried on the next `all` run. If the same files consistently error, the pipeline spins re-summarizing the same stuck files forever. Check for errors: `grep LLM_ERROR ~/.hermes/training_data/pipeline.log`. See `references/ollama-cpu-diagnosis.md` for the full diagnosis workflow.

### Docker Collector Stack

- **vLLM must be running on port 8020** for the proxy to forward requests. Without vLLM, the proxy returns "Internal Server Error".
- The proxy uses `network_mode: "host"` in Docker, so it shares the host's network stack -- this lets it reach vLLM on `127.0.0.1:8020` and PostgreSQL on `127.0.0.1:5432`.
- PostgreSQL data is on a Docker volume mapped to `/mnt/hermes_data/collector/pgdata/`. Backup this directory to preserve collected data.
- The proxy does NOT strip system prompts or metadata -- it captures the raw request payload as-is. Filter/purge data before training.

## Session Mining Pipeline (SovereignAI)

A post-hoc capture pipeline that mines Hermes session transcripts for training data. Located at `/home/fated/training_pipeline.py` on sovereign. Three stages:
1. CAPTURE: Scan Hermes sessions, extract new ones to raw/
2. SUMMARIZE: Process via local LLM (hq-ai Ollama hermes3:8b, Q4_0 GGUF) into structured template
3. GRADE: Score A/B/C/D, keep A/B in curated/, delete C/D

Full spec and pitfalls: `references/session-mining-pipeline.md`
CPU/GPU diagnosis workflow: `references/ollama-cpu-diagnosis.md`

Cron: `0 */4 * * * /home/fated/.hermes/hermes-agent/venv/bin/python /home/fated/training_pipeline.py all`

### Initialization

The pipeline output directory must exist before first run. Cron fails silently without it:

```bash
mkdir -p /home/fated/.hermes/training_data/{raw,processed,curated}
```

### Model Configuration

Default: hq-ai Ollama at `http://100.84.92.74:11434` with model `hermes3:8b`.
Override via env vars: `TRAINING_LLM_URL`, `TRAINING_LLM_MODEL`.

The pipeline passes `num_ctx: 32768` per-request in Ollama options to cap the
context window. Without this, the server default (128K) forces 50% of layers
to CPU — each request takes 35-70 seconds instead of 2-5. The server keeps
128K for other workloads; only pipeline calls are capped.

**Pitfall:** If the configured model isn't loaded in Ollama, all summarization calls return HTTP 404. Verify with `curl -s http://100.84.92.74:11434/api/tags` before running. The pipeline silently records errors in processed files rather than crashing — check processed/ for `LLM_ERROR` strings.

- You want to collect conversation data for fine-tuning an LLM
- You need to build a training dataset in ShareGPT format from live inference
- You want to audit or inspect a vLLM instance's conversation history

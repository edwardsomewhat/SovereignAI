# Session Mining Pipeline — Diagnosis & Init (May 21, 2026)

## What we found

The pipeline was defined but silently failing:
- `training_pipeline.py` existed at `/home/fated/training_pipeline.py` (8.5KB, 3-stage)
- Cron job was running: `0 */4 * * * python /home/fated/training_pipeline.py all`
- But `/home/fated/.hermes/training_data/` didn't exist — no subdirectories
- Log path pointed to `/home/fated/.hermes/training_data/pipeline.log` — also nonexistent
- Net result: cron ran every 4 hours, silently failed because `raw/` didn't exist

## Fix

```bash
mkdir -p /home/fated/.hermes/training_data/{raw,processed,curated}
python /home/fated/training_pipeline.py capture
# → Captured 22 sessions (29K lines total)
python /home/fated/training_pipeline.py summarize   # calls hq-ai qwen3.5:9b
python /home/fated/training_pipeline.py grade
```

## Architecture

```
Session JSONs → capture → raw/*.md → summarize (via hq-ai Ollama) → processed/*.md → grade → curated/*.md (A/B only)
```

## Differences from Docker collector stack

| | Docker stack | Session mining |
|---|---|---|
| Status | NOT deployed | ACTIVE on sovereign |
| Capture method | Intercepts vLLM API calls in real-time | Mines Hermes session JSONs post-hoc |
| Format | ShareGPT JSON in PostgreSQL | Markdown entries in filesystem |
| LLM for processing | None (raw capture) | hq-ai qwen3.5:9b for summarize + grade |
| Deployment | /mnt/hermes_data/collector/ | /home/fated/.hermes/training_data/ |

## LLM config

The pipeline reads these env vars (with defaults):
- `TRAINING_LLM_URL` → `http://100.84.92.74:11434` (hq-ai Ollama)
- `TRAINING_LLM_MODEL` → `qwen3.5:9b`

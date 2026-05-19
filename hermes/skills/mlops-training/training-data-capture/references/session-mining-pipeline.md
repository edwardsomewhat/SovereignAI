# Session Mining Pipeline (Deployed)

Post-hoc approach: mines Hermes session transcripts for training data without intercepting API calls.

## Current State (Monolithic)

Single Python script (`~/training_pipeline.py`) runs all stages:

1. **Capture** — extracts Hermes session JSONs to markdown text in `~/.hermes/training_data/raw/`
2. **Summarize** — local LLM compresses each session into a 5-field template
3. **Grade** — same model scores each entry, keeps A/B, deletes C/D

## Target State (Crew Agents)

The user's vision: split into independent crew agents on sovereign:
- Summarizer agent watches `raw/`, processes new files
- Grader agent watches `processed/`, scores and filters
- Both report to the orchestrator

Current monolithic script is a validated prototype; refactor to agents later.

## 5-Field Template

```
INTERACTION:  [debug | architecture | implementation | correction | discovery]
SUBJECT:      [one-line description]
CONFLICT:     [what was broken, unknown, or blocked]
RESOLUTION:   [what fixed it, with specifics]
RATIONALE:    [why — tied to Sovereign Codex principle]
```

## Grading Rubric

- **A (keep)**: User correction + agent adapts. Novel problem. Architecture decision.
- **B (keep)**: Multi-turn reasoning chain. Non-trivial workflow.
- **C (discard)**: Mechanical success. File reads, simple queries.
- **D (discard)**: Failures, dead ends, no resolution.

## Deployment Details

**Conchai:**
- Script: `~/training_pipeline.py`
- Cron: Hermes cron job `8c5332db9b3a`, every 4 hours, local delivery
- Trigger: `TRAINING_LLM_MODEL=hermes3:8b /path/to/venv/bin/python training_pipeline.py all`
- ⚠️ Must set `TRAINING_LLM_MODEL=hermes3:8b` — default `qwen3.5:9b` is broken

**Sovereign:**
- Script: `~/training_pipeline.py` (synced via Git)
- Cron: system crontab, every 4 hours
- Trigger: same as conchai

**LLM backend:** Both nodes use HQ Ollama at `http://100.84.92.74:11434`. No external API spend.

**⚠️ Model status (2026-05-19):** `qwen3.5:9b` and `qwen3:14b` are BROKEN on hq-ai — both return empty responses via `/api/generate`. Fallback: `hermes3:8b` works. Set `TRAINING_LLM_MODEL=hermes3:8b` env var to override. Working models on hq-ai: `hermes3:8b`, `gemma4:e4b`, `deepseek-r1:14b`, `qwen2.5-coder:14b`.

**hermes3:8b caveat:** ~24% of grading calls return empty responses (empty string grades default to "deleted" in the pipeline, causing false discards). The grading stage is lossy with this model — consider bumping to a larger model for better yield.

## First-Run Results (2026-05-19)

- 54 sessions captured from conchai's session DB
- 54 summarized by qwen3.5:9b
- 4 kept as A-grade (7.4% survival):
  - Dashboard --tui setup (correction, Self-Documentation)
  - Kiwix offline Wikipedia (implementation, Local First)
  - Network-file-access skill (implementation, Build Over Buy)
  - File transfer documentation (correction, Self-Documentation)
- 50 deleted — mechanical sessions, single-turn Q&A

## Second-Run Results (2026-05-19, later)

- Switched to `hermes3:8b` after qwen3.5:9b broke
- 0 new captured (all 66 already extracted)
- 36 newly summarized (30 were already processed from first run)
- 66 total graded: **49 kept** (15 A's, 34 B's), **17 deleted**
- 74% survival rate (up from 7.4% — hermes3:8b is more generous than qwen3.5:9b)
- 16 of the 17 deleted had empty grades (model failure), only 1 genuine C-grade

## Script Location

`~/training_pipeline.py` on both nodes. Also pushed to SovereignAI repo under `scripts/training_pipeline.py`.

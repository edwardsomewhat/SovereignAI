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
- ⚠️ **Model choice matters**: `hermes3:8b` = ~74% keep rate (generous grader, ~24% empty-response rate). `qwen3.5:9b` = ~13% keep rate (harsh grader, fewer empty responses). Choose based on desired curation strictness.

**Sovereign:**
- Script: `~/training_pipeline.py` (synced via Git)
- Cron: system crontab, every 4 hours
- Trigger: same as conchai

**LLM backend:** Both nodes use HQ Ollama at `http://100.84.92.74:11434`. No external API spend.

**⚠️ Model status (2026-05-20):** `qwen3.5:9b` is working again — confirmed reachable and responding via `/api/generate`. However, its grading yield is low (~13% keep rate vs 74% for hermes3:8b). `qwen3:14b` status unknown. Fallback: `hermes3:8b` works reliably but has ~24% empty-response rate on grading calls. Working models on hq-ai: `hermes3:8b`, `qwen3.5:9b`, `gemma4:e4b`, `deepseek-r1:14b`, `qwen2.5-coder:14b`.

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
- 66 total graded: **49 kept** (15 A's, 9 B's), **17 deleted**
- 74% survival rate (up from 7.4% — hermes3:8b is more generous than qwen3.5:9b)
- 16 of the 17 deleted had empty grades (model failure), only 1 genuine C-grade

## Third-Run Results (2026-05-20)

- Model: `qwen3.5:9b` (default, no env override — `qwen3.5:9b` is working again)
- 1 new session captured (cron session from previous pipeline run)
- 58 raw files summarized (29 newly, rest already had processed counterparts)
- 68 total graded: **9 kept** (9 A's), **59 deleted**
- 13.2% survival rate — far lower than hermes3:8b's 74%
- Many deleted entries had blank grades (model returned empty string, defaulted to delete)
- Curation count: 50 → 51 (net +1 — 8 of the 9 kept were already present from prior runs)
- Pipeline ran ~44 min (2618s); foreground 300s timeout insufficient — use background mode

## Operational Notes

- **Run background, not foreground**: the pipeline takes 30-60 min. Use `background=true` + `notify_on_complete=true` in the terminal call.
- **Python buffers stdout**: output is invisible until the process exits or buffer fills. Monitor progress by polling file counts (`ls raw/ | wc -l`, `ls processed/ | wc -l`) instead of waiting for terminal output.
- **LLM health check**: before running, verify the model responds: `curl http://100.84.92.74:11434/api/generate -d '{"model":"qwen3.5:9b","prompt":"say hi","stream":false}'`. Non-empty `response` field = model is alive.
- **Grading yield varies wildly by model**: hermes3:8b = ~74% keep rate, qwen3.5:9b = ~13%. The larger the model, the more generous the grader.

## Script Location

`~/training_pipeline.py` on both nodes. Also pushed to SovereignAI repo under `scripts/training_pipeline.py`.

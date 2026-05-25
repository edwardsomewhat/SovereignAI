---
name: sovereign-training-pipeline
description: Run and maintain the Sovereign training data pipeline — capture sessions, summarize via local LLM, and grade into curated training data.
---

# Sovereign Training Pipeline

Run the training data curation pipeline: `/home/fated/training_pipeline.py`.

## Directory Layout

```
~/.hermes/training_data/
├── pipeline_state.json    # Tracks last session timestamp
├── raw/                   # Stage 1: extracted session transcripts (*.md)
├── processed/             # Stage 2: LLM summaries (*.txt)
└── curated/               # Stage 3: A/B-graded final training data (*.txt)
```

Sessions live in `~/.hermes/sessions/session_*.json`.

## Running

### Single stage
```bash
cd /home/fated
./.hermes/hermes-agent/venv/bin/python training_pipeline.py {capture|summarize|grade}
```

### All stages (full run)
```bash
cd /home/fated
./.hermes/hermes-agent/venv/bin/python training_pipeline.py all
```

**⚠️ Always run in background mode.** The pipeline makes one LLM call per session (Ollama at `http://100.84.92.74:11434`, model `qwen3.5:9b`). With 100+ sessions, foreground mode will time out at 600s. Use:

```bash
PYTHONUNBUFFERED=1 ./.hermes/hermes-agent/venv/bin/python training_pipeline.py all
```

The `PYTHONUNBUFFERED=1` is **critical** — without it, Python buffers stdout when not connected to a TTY, and the capture/summarize stage output is lost. Only the grade stage output flushes on exit. See pitfall below.

Hermes invocation:
```bash
terminal(command="PYTHONUNBUFFERED=1 .../venv/bin/python training_pipeline.py all", background=true, notify_on_complete=true, timeout=1800)
```

Then poll with `process(action="poll", session_id="...")` or watch file counts:
```bash
ls ~/.hermes/training_data/processed/*.txt | wc -l   # growing = summarize stage
ls ~/.hermes/training_data/curated/*.txt | wc -l     # growing = grade stage
```

File-count monitoring is the **primary** way to track progress — even with `PYTHONUNBUFFERED=1`, small print() output from capture/summarize stages typically does not flush through the process pipe until process exit. Only the verbose LLM grading output (thousands of chars) overflows the OS pipe buffer and appears mid-run. Also check the state file for capture count: `cat ~/.hermes/training_data/pipeline_state.json`.

**⚠️ Pitfall: `process(action="wait")` is clamped to 60s.** Regardless of the timeout value you pass (e.g., 600s), the wait action is internally clamped to 60 seconds. You cannot do a single long blocking wait — you must poll in a loop. Use file-count checks between wait calls to track progress:
```bash
# Check file counts frequently rather than doing one long wait
echo "Raw: $(ls raw/*.md | wc -l) | Processed: $(ls processed/*.txt | wc -l) | Curated: $(ls curated/*.txt | wc -l)"
```

**⚠️ Pitfall: Stale capture output.** The capture-stage `print()` lines at the top of the process log may reflect a *previous* pipeline invocation, not the current one. Do NOT trust "Captured N new sessions" from the log. Always verify against the state file and raw/ directory file counts — if `pipeline_state.json` and `ls raw/*.md | wc -l` show no change, no new sessions were captured regardless of what the log says.

### Pitfall: Stdout Buffering Kills Pipeline Visibility

Even with `PYTHONUNBUFFERED=1`, Python's small print() output (capture and summarize stage progress lines) typically does NOT flush through the Hermes process pipe in background mode — OS pipe buffering still applies. Result:
- Capture and summarize `print()` output is usually invisible until process exit
- Only the verbose LLM grading output (2000+ char reasoning chains) overflows the pipe buffer and appears mid-run
- The agent must track progress via directory file counts and state file — do not rely on process log output

`PYTHONUNBUFFERED=1` is still important (without it, even the verbose grading output may not flush), but it does not guarantee visibility of small print() calls.

## Known Bug: Re-summarization Loop

`stage_summarize()` checks `processed/{stem}.txt` to skip already-summarized sessions. But `stage_grade()` **deletes** processed files after grading (A/B → moves to curated; C/D → deleted). On the next run, summarize re-processes ALL raw files — including the 90%+ that were already graded A/B. This wastes ~100+ LLM calls per run.

**Observed behavior note (24 May 2026):** In a run with 129 raw files and 0 processed, only 18 files were actually summarized+graded — not all 129. The pipeline's final output reported "Graded: 0 kept, 18 deleted." This may indicate the bug has been partially mitigated (e.g., a hidden check or limit), or it depends on specific conditions. The full re-summarization behavior described above should be considered the worst case; observed behavior may be less severe.

### Fix
In `stage_summarize()`, add a curated-path skip before the LLM call:

```python
# In stage_summarize(), inside the for-loop, after the processed check:
curated_file = CURATED_DIR / f"{rf.stem}.txt"
if curated_file.exists():
    continue
```

This prevents re-summarizing sessions that were already graded and kept in previous runs.
See `references/re-summarization-bug.md` for full root-cause analysis and reproduction.

## LLM Details

- Endpoint: `http://100.84.92.74:11434` (configurable via `TRAINING_LLM_URL` env var)
- Model: `qwen3.5:9b` (configurable via `TRAINING_LLM_MODEL`)
- Timeout: 120s per call (set in `call_ollama()`)
- Summarize prompt: ~200-400 tokens in → ~100 tokens out (5-field template)
- Grade prompt: ~100 tokens in → **~500-2000 tokens out** (qwen3.5 ignores "return ONLY the letter" and outputs full reasoning chains)
- Real-world performance: each file requires 2 LLM calls (summarize + grade). Budget ~90s per call at normal Ollama load, so total wall-clock ≈ `num_files × 180s`. Observed runs: 11 files in ~18 min (May 2026), 16 files in ~23 min (May 2026), 18 files in ~20-25 min (May 2026 — all graded C/D), 20 files in ~23 min (May 2026 — all graded C/D). Times vary with Ollama load; budget ~100s per LLM call for conservative planning.

### Pitfall: qwen3.5 Ignores Concise Grading Instructions

The grading system prompt says "Output ONLY the letter grade (A, B, C, or D). No explanation." The qwen3.5:9b model **completely ignores this** and outputs 500-2000 tokens of reasoning before (or instead of) the grade letter. The pipeline still works because `call_ollama()` returns the full response and `stage_grade()` takes `.strip().upper()` — the letter is somewhere in the response, typically on the last line.

This inflates grade stage time from a theoretical ~1-3s to ~60-120s per file and wastes Ollama throughput.

**Workaround** (not yet applied in the pipeline): Strip reasoning by extracting only the first non-empty line, or regex for `[ABCD]`, or set `num_predict: 5` to cap output. See `references/verbose-grading-output.md` for real output samples.

## Grading Rubric

| Grade | Action | Criteria |
|-------|--------|----------|
| A     | Keep   | User correction + agent adapts. Novel problem solved. Architecture decision. |
| B     | Keep   | Multi-turn reasoning chain with tool calls that succeeded. Non-trivial workflow. |
| C     | Discard | Mechanical success. File reads, simple queries. Single tool calls. |
| D     | Discard | Failures, dead ends, agent spinning with no resolution. |

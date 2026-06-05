---
name: sovereign-training-pipeline
description: Run and maintain the Sovereign training data pipeline — capture sessions, summarize via local LLM, and grade into curated training data.
---

# Sovereign Training Pipeline

Two approaches exist for producing fine-tuning data from Hermes Agent sessions:

1. **Batch Session Mining** (this skill's primary focus) — post-hoc pipeline that extracts Hermes session DB transcripts, summarizes via local LLM, and grades into curated training data. Script: `~/training_pipeline.py`.
2. **Real-time Proxy Capture** — Docker-based intercept proxy that sits between LLM clients and vLLM, capturing every conversation in ShareGPT format to PostgreSQL. See `references/proxy-capture.md`.

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

**⚠️ Always run in background mode.** The pipeline makes one LLM call per session (Ollama at `http://hq-ai:11434`, model `qwen3.5:9b`). The default `http://100.84.92.74:11434` is unreachable from this node — always override with `TRAINING_LLM_URL=http://hq-ai:11434`. With 100+ sessions, foreground mode will time out at 600s. Use:

```bash
TRAINING_LLM_URL=http://hq-ai:11434 PYTHONUNBUFFERED=1 ./.hermes/hermes-agent/venv/bin/python training_pipeline.py all
```

The `PYTHONUNBUFFERED=1` is **critical** — without it, Python buffers stdout when not connected to a TTY, and the capture/summarize stage output is lost. Only the grade stage output flushes on exit. The `TRAINING_LLM_URL=http://hq-ai:11434` is also critical — the hardcoded default IP `100.84.92.74:11434` is unreachable from this node. See pitfall below.

Hermes invocation:
```bash
terminal(command="TRAINING_LLM_URL=http://hq-ai:11434 PYTHONUNBUFFERED=1 .../venv/bin/python training_pipeline.py all", background=true, notify_on_complete=true, timeout=1800)
```

Then poll with `process(action="poll", session_id="...")` or watch file counts:
```bash
ls ~/.hermes/training_data/processed/*.txt | wc -l   # growing = summarize stage
ls ~/.hermes/training_data/curated/*.txt | wc -l     # growing = grade stage
```

File-count monitoring is one way to track progress — `PYTHONUNBUFFERED=1` doesn't help with Hermes process pipe buffering for small print() calls. However, **redirecting stdout to a file** (`> /tmp/pipeline_out.txt 2>&1`) captures ALL output immediately, including capture and summarize stage progress lines. Read the log file with `cat /tmp/pipeline_out.txt` or `tail -3 /tmp/pipeline_out.txt` to see which session is being processed right now — much more informative than directory counts alone.

**Monitoring options (prefer the log file when you need real-time visibility):**

```bash
# Option A: Log-file redirect (best for real-time progress)
.../python training_pipeline.py all > /tmp/pipeline_out.txt 2>&1

# Then from another terminal call:
cat /tmp/pipeline_out.txt
tail -3 /tmp/pipeline_out.txt

# Option B: File-count monitoring (lightweight, works without file redirect)
ls ~/.hermes/training_data/processed/*.txt | wc -l   # growing = summarize stage
ls ~/.hermes/training_data/curated/*.txt | wc -l     # growing = grade stage

# Option C: State file (capture stage only)
cat ~/.hermes/training_data/pipeline_state.json
```

**⚠️ Pitfall: `process(action="wait")` is clamped to 60s.** Regardless of the timeout value you pass (e.g., 180s or 1800s), the wait action is internally clamped to 60 seconds. You cannot do a single long blocking wait — you must poll in a loop. Use `sleep N` in combination with file-count checks between polls.

**⚠️ Pitfall: Foreground terminal timeout caps monitoring sleeps.** Hermes enforces a 600s maximum foreground terminal timeout. When monitoring with `sleep N && echo ...`, the total `sleep + terminal timeout` must stay under 600s. Keep sleeps at ≤580s to avoid `"Foreground timeout exceeds the maximum of 600s"` rejections. Pattern:
```bash
terminal("sleep 300 && echo ...", timeout=310)  # ok: 310 ≤ 600
terminal("sleep 600 && echo ...", timeout=610)  # REJECTED: 610 > 600
```
```bash
# Check file counts frequently rather than doing one long wait
echo "Raw: $(ls raw/*.md | wc -l) | Processed: $(ls processed/*.txt | wc -l) | Curated: $(ls curated/*.txt | wc -l)"
```

**⚠️ Pitfall: Orphaned processed files inflate graded counts.** If a previous pipeline run was interrupted during the grade stage (timeout, kill, crash), processed files remain in `processed/` and don't get cleaned up. The next full run will grade them alongside newly-summarized files, making the graded count appear much higher than the summarized count (e.g., 13 summarized but 29 graded — 16 orphaned from a prior interrupted run). This is harmless but misleading when reading the output. The orphaned files are genuinely graded (kept or deleted) on the subsequent run.

**⚠️ Pitfall: Stale capture output.** The capture-stage `print()` lines at the top of the process log may reflect a *previous* pipeline invocation, not the current one. Do NOT trust "Captured N new sessions" from the log. Always verify against the state file and raw/ directory file counts — if `pipeline_state.json` and `ls raw/*.md | wc -l` show no change, no new sessions were captured regardless of what the log says.

### Pitfall: Stdout Buffering Kills Pipeline Visibility

Even with `PYTHONUNBUFFERED=1`, Python's small print() output (capture and summarize stage progress lines) typically does NOT flush through the Hermes process pipe in background mode — OS pipe buffering still applies. Result:
- Capture and summarize `print()` output is usually invisible until process exit
- Only the verbose LLM grading output (2000+ char reasoning chains) overflows the pipe buffer and appears mid-run
- The agent must track progress via directory file counts and state file — do not rely on process log output

`PYTHONUNBUFFERED=1` is still important (without it, even the verbose grading output may not flush), but it does not guarantee visibility of small print() calls.

## Known Bug: Re-summarization Loop

`stage_summarize()` checks `processed/{stem}.txt` to skip already-summarized sessions. But `stage_grade()` **deletes** processed files after grading (A/B → moves to curated; C/D → deleted). On the next run, summarize re-processes ALL raw files — including the 90%+ that were already graded A/B. This wastes ~100+ LLM calls per run.

**Observed behavior (cumulative):**
| Date | Raw | Summarized | Graded | Kept | Deleted |
|------|-----|-----------|--------|------|---------|
| 24 May 2026 | 129 | 18 | 18 | 0 | 18 |
| 25 May 2026 (early) | 133 | 20 | 20 | 0 | 20 |
| 28 May 2026 (cron) | 178 | 52 | 52 | 3 | 49 |
| 28 May 2026 (cron #2) | 180 | 19 | 51 | 2 | 49 |
| 28 May 2026 (cron #4) | 185 | 18 | 54 | 3 | 51 |
| 29 May 2026 (cron)     | 189 | 42 | 51 | 5 | 46 |
| 29 May 2026 (cron #2) | 193 | 42 | 42 | 2 | 40 |
| 30 May 2026 (cron)     | 197 | 39 | 39 | 1 | 38 |
| 30 May 2026 (cron #2) | 199 | 29 | ≥12¹| — | — |
| 30 May 2026 (cron #3) | 201 | 39 | 39 | 3 | 36 |
| 30 May 2026 (cron #4) | 203 | 38 | 38 | 0 | 38 |
| 31 May 2026 (cron)     | 204 | 39 | 39 | 0 | 39 |
| 31 May 2026 (cron #2)  | 206 | 15 | 41 | 0 | 41 |
| 31 May 2026 (cron #3)  | 208 | 43 | 43 | 0 | 43 |
| 31 May 2026 (cron #4)  | 212 | 47 | 47 | 0 | 47 |
| 01 Jun 2026 (cron)     | 216 | 51 | 51 | 0 | 51 |
| 01 Jun 2026 (cron #2)  | 218 | 53 | 53 | 0 | 53 |
| 02 Jun 2026 (cron)     | 221 | 56 | 56 | 0 | 56 |
| 03 Jun 2026 (cron)     | 229 | 56 | 56 | 0 | 56 |
| 03 Jun 2026 (cron #2)  | 231 | 58 | 58 | 0 | 58 |
| 03 Jun 2026 (cron #3)  | 233 | 60 | 60 | 0 | 60 |
| 04 Jun 2026 (cron)     | 236 | 63 | 63 | 4 | 59 |

The curated-path skip

The curated-path skip (applied in the code) prevents re-summarizing **A/B-kept sessions** (curated files exist → skip). However, **C/D-graded sessions have no curated file**, so `stage_summarize()` re-processes them on every run. This is the dominant source of wasted LLM calls: on `27 May cron #3`, 36 of 38 files summarized were previously-graded C/D sessions, not new captures. The cumulative `raw - curated` gap grows by ~2 per run as new sessions arrive; the summarize cost is ≈ `raw - curated` files per run, not just `delta(new captures)`.

*Orphaned processed files* from interrupted runs can also cause graded > summarized in the same run.

**⚠️ Low keeper rate (0–3 per run) — partially a grade-extraction bug.** `stage_grade()` checks `if grade in ("A", "B")` which is an **exact match** against the full response string — not a substring search. When qwen3.5 outputs 2000+ characters of thinking-chain reasoning, the full string never equals `"A"` or `"B"`, so even sessions the model internally considers A/B quality are silently deleted. The 1-3 keepers observed in some runs are sessions where the model happened to output just a bare letter (rare). Zero-keeper runs occur when the model is verbose on every grading call.

The genuine quality issue is real — cron job executions, pipeline runs, and single-tool-call sessions dominate the corpus and would be C/D even with correct parsing — but the extraction bug makes it impossible to know the true keeper rate. **Until the grade parsing is fixed (e.g., regex extract `[ABCD]` from the last line of output), the pipeline is silently discarding all A/B sessions alongside C/D.** See `references/verbose-grading-output.md` for root cause and fix options.

### Fix (already applied in code)

The curated-path skip was added to `stage_summarize()` on 2026-05-27 (lines 187-189):

```python
# Already in stage_summarize(), lines 187-189:
curated_file = CURATED_DIR / f"{rf.stem}.txt"
if curated_file.exists():
    continue
```

This prevents re-summarizing sessions that were already graded and kept in previous runs.
See `references/re-summarization-bug.md` for full root-cause analysis and reproduction.

## LLM Details

- Endpoint: `http://hq-ai:11434` (configurable via `TRAINING_LLM_URL` env var)
- Model: `qwen3.5:9b` (configurable via `TRAINING_LLM_MODEL`)
- Timeout: 120s per call (set in `call_ollama()`)
- Summarize prompt: ~200-400 tokens in → ~100 tokens out (5-field template)
- Grade prompt: ~100 tokens in → **~500-2000 tokens out** (qwen3.5 ignores "return ONLY the letter" and outputs full reasoning chains)
- Real-world performance: each file requires 2 LLM calls (summarize + grade). Budget ~90s per call at normal Ollama load, so total wall-clock ≈ `num_files × 180s`. Observed runs: 11 files in ~18 min (May 2026), 16 files in ~23 min (May 2026), 18 files in ~20-25 min (May 2026 — all graded C/D), 20 files in ~23 min (May 2026 — all graded C/D), 72 calls (18 summarize + 54 grade) in ~27 min (28 May cron #4 — ~22s/call, moderate load), 52 calls (18 summarize + 34 grade) in ~13 min (27 May — ~15s/call, much faster than typical). Times vary with Ollama load; budget ~100s per LLM call for conservative planning, but recent performance suggests ~15-40s per call depending on load: 52 calls in ~13 min (~15s/call, 27 May — light load), 76 calls in ~50 min (~40s/call, 27 May cron #3 — moderate load), 78 calls in ~90 min (~69s/call, 30 May cron #3 — heavy load/slow).

### ⚠️ Pitfall: LLM Endpoint — Prefer Hostname Over Raw IP

The hardcoded default LLM endpoint `http://100.84.92.74:11434` may or may not be reachable depending on Tailscale subnet routing state. The Tailscale hostname `http://hq-ai:11434` is the canonical, reliable choice.

**Status as of 2026-06-03:** The default IP has been reachable for several consecutive runs (since ~31 May), suggesting it is now reliably routable. However, the hostname remains the safer choice — the raw IP could become unreachable again if Tailscale subnet routing changes.

```bash
TRAINING_LLM_URL=http://hq-ai:11434 PYTHONUNBUFFERED=1 .../python training_pipeline.py all
```

Verify connectivity before running: `tailscale ping hq-ai`.

### ⚠️ Pitfall: Ollama Not Running on hq-ai

The Ollama service on hq-ai may be down (e.g., after a reboot). Symptoms: `ConnectionRefusedError: [Errno 111] Connection refused` on any `http://hq-ai:11434` request, even though `tailscale ping hq-ai` succeeds (ping tests network, not the service).

**Check:** `tailscale ssh hq-ai 'systemctl is-active ollama'` — if it returns `inactive`, start it:
```bash
tailscale ssh hq-ai 'sudo systemctl start ollama && sleep 2 && systemctl is-active ollama'
```

After starting, the model still needs a warm-up call (see Cold Model Timeout below).

**Pre-flight checklist** before running the pipeline:
1. `tailscale ping hq-ai` — network reachable?
2. `tailscale ssh hq-ai 'systemctl is-active ollama'` — service running? If `inactive`, start it.
3. Warm-up call (below) — model loaded? If it times out, wait and retry.

### ⚠️ Pitfall: Cold Model Timeout (first run after Ollama restart)

If the model `qwen3.5:9b` is not already loaded in Ollama memory (e.g., after an Ollama restart), the first `/api/generate` call will **time out at 120s** while the model loads. The `/api/tags` GET endpoint returns instantly because it doesn't trigger model loading — do not mistake a successful tags check for pipeline readiness.

**Warm-up test** before running the pipeline:
```bash
./venv/bin/python -c "
import urllib.request, json
req = urllib.request.Request('http://hq-ai:11434/api/generate',
    data=json.dumps({'model':'qwen3.5:9b','prompt':'ping','stream':False,'options':{'num_predict':5}}).encode(),
    headers={'Content-Type':'application/json'})
print(json.loads(urllib.request.urlopen(req, timeout=30).read()).get('response','') or 'warm')
"
```

If it returns within ~30s, the model is loaded and the pipeline will run. Otherwise, let it finish (up to 120s), then re-run the pipeline — the model stays warm for subsequent calls.

### Pitfall: qwen3.5 Ignores Concise Grading Instructions (Grade-Extraction Bug)

Plus a **timeout bug**: with `num_predict=2048` and a 120s timeout, qwen3.5:9b takes ~142s per call (warm model). All calls time out silently. Fix applied 2026-05-30 in `call_ollama()`: reduced `num_predict` to 512 and increased timeout to 300s. Historical runs (cron #1-#3 on 30 May) all timed out and produced zero results — those were re-run with the fix applied.

The grading system prompt says "Output ONLY the letter grade (A, B, C, or D). No explanation." The qwen3.5:9b model **completely ignores this** and outputs 500-2000 tokens of reasoning before (or instead of) the grade letter.

**The pipeline does NOT recover from this.** `call_ollama()` returns the full response (including thinking chain), and `stage_grade()` does `grade in ("A", "B")` — an **exact match**, not a substring search. When the verbose response contains 2000+ characters, it never equals the single-letter strings `"A"` or `"B"`. Result: **all sessions are silently deleted, including those the model internally graded A/B.**

The 1-3 keepers observed in some past runs (including 3 in the 28 May cron #4 run) were sessions where the model happened to output a bare letter — this is luck, not the pipeline working. Zero-keeper runs are the norm when the model is consistently verbose on every grading call.

This also inflates grade stage time from a theoretical ~1-3s to ~60-120s per file.

### Pitfall: Thinking-Model Output Problems in Summarize Stage

The `call_ollama()` function handles thinking models that return separate `response` and `thinking` fields. Two failure modes exist:

**Mode 1 — Empty files (fixed):** The original logic returned `""` when `response` was empty and `thinking` > 500 chars. Fixed 2026-05-29 with fallback extraction from `thinking` field. Empty files blocking re-processing are a solved problem.

**Mode 2 — Garbage thinking traces (unresolved):** The thinking-field fallback extraction often captures raw CoT reasoning instead of the structured 5-field template. The LLM internally thinks about how to summarize but never outputs the structured result, and the fallback logic saves the reasoning chain as the "summary."

**Observed (2026-06-03):** 26 of 47 processed files (55%) were raw thinking traces like:

```
1.  **ANALYZE THE REQUEST:**
    *   ROLE: TRAINING DATA CURATOR...
    *   TASK: READ THE PROVIDED AGENT SESSION TRANSCRIPT...
```

instead of the expected structured template starting with `INTERACTION:`.

**Detection:** Garbage summaries don't start with `INTERACTION:`. Check with:
```bash
cd ~/.hermes/training_data/processed
for f in *.txt; do head -c 13 "$f" | grep -q "^INTERACTION:" || echo "GARBAGE: $f"; done
```

**Remediation:** Delete garbage files so the summarizer can re-process on the next run (though same raw session may produce another garbage summary — root cause is in `call_ollama()` extraction logic):
```bash
for f in processed/*.txt; do head -c 13 "$f" | grep -q "^INTERACTION:" || rm "$f"; done
```

**Workaround — batch grading with non-thinking model:** When grading is needed and the pipeline's qwen3.5:9b is too slow or produces unparseable output, switch to batch grading with `hermes3:8b` (non-thinking, 4.7 GB). Group 5-10 summaries per batch, ask for `FILENAME:GRADE` output. See [`references/garbage-summaries-and-batch-grading.md`](references/garbage-summaries-and-batch-grading.md) for the full pattern.

## Grading Rubric

| Grade | Action | Criteria |
|-------|--------|----------|
| A     | Keep   | User correction + agent adapts. Novel problem solved. Architecture decision. |
| B     | Keep   | Multi-turn reasoning chain with tool calls that succeeded. Non-trivial workflow. |
| C     | Discard | Mechanical success. File reads, simple queries. Single tool calls. |
| D (discard) | Delete | Failures, dead ends, agent spinning with no resolution. |

## References

- [`references/proxy-capture.md`](references/proxy-capture.md) — Real-time Docker-based intercept proxy architecture.
- [`references/operations.md`](references/operations.md) — Operational notes: monitoring background runs, timing expectations, stage behavior, and file locations.
- [`references/garbage-summaries-and-batch-grading.md`](references/garbage-summaries-and-batch-grading.md) — Detecting thinking-trace garbage from summarizer, and batch-grading with non-thinking models (hermes3:8b) as a faster workaround.

# Session Mining Pipeline (Alternative to Proxy Capture)

Instead of intercepting API calls at the proxy level, this post-hoc approach mines Hermes session transcripts for training data.

## Pipeline Stages

1. **Capture** — extracts Hermes session JSONs to markdown text in `~/.hermes/training_data/raw/`
2. **Summarize** — local LLM (hermes3:8b on hq-ai Ollama) compresses each session into a 5-field template:
   ```
   INTERACTION:  [debug | architecture | implementation | correction | discovery]
   SUBJECT:      [one-line description]
   CONFLICT:     [what was broken, unknown, or blocked]
   RESOLUTION:   [what fixed it]
   RATIONALE:    [why — tied to Sovereign Codex principle]
   ```
3. **Grade** — same model scores each entry A/B/C/D. A/B kept in `curated/`, C/D deleted.

## Grading Rubric

- **A (keep)**: User correction + agent adapts. Novel problem. Architecture decision.
- **B (keep)**: Multi-turn reasoning chain. Non-trivial workflow.
- **C (discard)**: Mechanical success. File reads, simple queries.
- **D (discard)**: Failures, dead ends, no resolution.

## Usage

```bash
python training_pipeline.py capture    # Stage 1
python training_pipeline.py summarize  # Stage 2
python training_pipeline.py grade      # Stage 3
python training_pipeline.py all        # All stages
```

## LLM Configuration

Default: hq-ai Ollama at `http://100.84.92.74:11434` with model `hermes3:8b` (Q4_0 GGUF, ~4.7GB weights).

Override via env vars:
```bash
export TRAINING_LLM_URL="http://100.84.92.74:11434"
export TRAINING_LLM_MODEL="hermes3:8b"
# To switch to DeepSeek:
# export TRAINING_LLM_URL="https://api.deepseek.com"
# export TRAINING_LLM_MODEL="deepseek-chat"
```

**Critical: per-request context cap.** The pipeline passes `num_ctx: 32768` in Ollama options. Without this, the server default (128K) creates a massive KV cache that forces layers to CPU — resulting in 35-70s per request, 1248% CPU, and near-zero GPU utilization. The server keeps 128K globally for other workloads; only pipeline requests are capped.

## Pitfalls

- **LLM errors cause re-processing loops.** If `call_ollama` returns `LLM_ERROR` during summarize, the raw file stays in `raw/` and gets retried on every `all` run. Check with `grep LLM_ERROR ~/.hermes/training_data/pipeline.log`. Stuck files need manual cleanup from `raw/` if they'll never summarize successfully.

- **Grade parsing requires regex extraction.** The pipeline extracts `[A-D]` via `re.search` because Ollama may return `"A."` or `"Grade: B"` instead of bare letters. Without this, valid A/B sessions get mis-classified as C/D and deleted.

- **CPU thrashing from 128K context.** If the pipeline suddenly runs slow (60s+ per request, 12+ load on hq-ai), the per-request `num_ctx` cap may have been removed or the server default changed. See `references/ollama-cpu-diagnosis.md` for the full diagnosis workflow (nvidia-smi, ollama ps, journalctl, ps aux).

## Cron

Runs every 4 hours on sovereign. Curated data feeds into graphify for pattern discovery and into the RAG database for retrieval.

## Script

Located at `~/training_pipeline.py` on sovereign.

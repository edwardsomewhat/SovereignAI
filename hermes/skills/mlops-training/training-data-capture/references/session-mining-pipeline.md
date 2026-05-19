# Session Mining Pipeline (Alternative to Proxy Capture)

Instead of intercepting API calls at the proxy level, this post-hoc approach mines Hermes session transcripts for training data.

## Pipeline Stages

1. **Capture** — extracts Hermes session JSONs to markdown text in `~/.hermes/training_data/raw/`
2. **Summarize** — local LLM (qwen3.5:9b on HQ Ollama) compresses each session into a 5-field template:
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

## Cron

Runs every 4 hours on both nodes. Curated data feeds into graphify for pattern discovery and into the RAG database for retrieval.

## Script

Located at `~/training_pipeline.py` on both conchai and sovereign nodes.

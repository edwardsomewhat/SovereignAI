# Pipeline Operations Notes

## Monitoring background runs

When running `training_pipeline.py all` in background mode (terminal `background=true`), Python's stdout is fully buffered when piped — **no output is visible until the process exits**. Do not wait for stdout to appear.

**Monitor progress by checking file counts in the processed/ directory:**

```bash
ls ~/.hermes/training_data/processed/*.txt | wc -l
```

Or via `search_files`:
```
search_files(path="~/.hermes/training_data/processed", pattern="*.txt", target="files")
```

## Timing

Local LLM endpoint (`qwen3.5:9b` via Ollama) processes **~1 session per minute** for summarization. A full backlog of 46 sessions takes ~70 minutes. Grading is similarly paced since each entry gets a separate LLM call.

## Stage behavior

| Stage | What it does | Skipping condition |
|-------|-------------|-------------------|
| **capture** | Extracts new sessions from `~/.hermes/sessions/` to `raw/` | Session already has a `raw/` file AND its mtime ≤ `last_session_ts` in state |
| **summarize** | Sends each `raw/` file to LLM for 5-field template, saves to `processed/` | File already exists in `processed/` OR `curated/` |
| **grade** | Scores each `processed/` file via LLM; A/B → `curated/`; C/D → deleted | None — all files in `processed/` are graded |

This means sessions that were graded A/B in a prior run are skipped during summarize (they're already in `curated/`). Only genuinely new or previously-failed sessions get re-processed.

## File locations

- Raw extracts: `~/.hermes/training_data/raw/session_*.md`
- Summarized: `~/.hermes/training_data/processed/session_*.txt`
- Curated (A/B grade): `~/.hermes/training_data/curated/session_*.txt`
- State: `~/.hermes/training_data/pipeline_state.json`
- Script: `/home/fated/training_pipeline.py`

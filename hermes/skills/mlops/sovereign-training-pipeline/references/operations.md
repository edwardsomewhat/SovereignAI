# Pipeline Operations Notes

## Monitoring background runs

When running `training_pipeline.py all` in background mode, two monitoring strategies are available:

### Log-file redirect (preferred for real-time visibility)

Redirect stdout to a file — all output is written immediately and can be read in real time:

```bash
.../python training_pipeline.py all > /tmp/pipeline_out.txt 2>&1
```

Then from another terminal:
```bash
cat /tmp/pipeline_out.txt          # see all progress
tail -3 /tmp/pipeline_out.txt       # see latest session being processed
grep 'Summarized\|Graded' /tmp/pipeline_out.txt  # extract summary lines
```

This captures capture, summarize, AND grade stage output — including the small print() calls that don't flush through the Hermes process pipe.

### File-count monitoring (lightweight, no log file needed)

```bash
ls ~/.hermes/training_data/processed/*.txt | wc -l   # growing = summarize stage
ls ~/.hermes/training_data/curated/*.txt | wc -l     # growing = grade stage
```

## Timing

Local LLM endpoint (`qwen3.5:9b` via Ollama) processes **~1 session per minute** for summarization. Grading is slower (~90-120s per file) due to verbose qwen3.5 output (500-2000+ chars of reasoning). A grading run of ~30 files can take 30-50 minutes and may exceed the 600s foreground terminal timeout. When that happens, run `grade` again — it picks up remaining `processed/` files and is safe to re-run idempotently.

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

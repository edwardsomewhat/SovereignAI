# Garbage Summary Detection & Batch Grading Workaround

## Garbage Summaries: A Second Manifestation of the Thinking-Model Bug

The `call_ollama()` fix for empty `response` fields (2026-05-29) captures the `thinking` field when `response` is empty. But this introduces a **second failure mode**: when qwen3.5:9b outputs a long reasoning chain in `thinking` but the extracted "answer" is still CoT, not a structured 5-field template.

**Observed 2026-06-03:** 26 of 47 processed files (55%) were raw thinking traces — the LLM's internal reasoning about how to summarize, not the structured template itself. These files look like:

```
1.  **ANALYZE THE REQUEST:**
    *   ROLE: TRAINING DATA CURATOR...
    *   TASK: READ THE PROVIDED AGENT SESSION TRANSCRIPT...
    ... [hundreds of chars of reasoning] ...
    *   THEREFORE, INTERACTION TYPE SHOULD BE implementation...
```

instead of:

```
INTERACTION: implementation
SUBJECT: Sovereign training data pipeline execution
CONFLICT: ...
RESOLUTION: ...
RATIONALE: ...
```

### Detection

Garbage summaries do **not** start with `INTERACTION:`. Detection command:

```bash
cd ~/.hermes/training_data/processed
for f in *.txt; do
    head -c 13 "$f" | grep -q "^INTERACTION:" || echo "GARBAGE: $f"
done
```

Or in Python:
```python
from pathlib import Path
for f in Path("processed").glob("*.txt"):
    if not f.read_text().strip().startswith("INTERACTION:"):
        print(f"GARBAGE: {f.name}")
```

### Remediation

Delete garbage files so the summarizer can re-process the raw session on the next run:

```bash
cd ~/.hermes/training_data
for f in processed/*.txt; do
    head -c 13 "$f" | grep -q "^INTERACTION:" || rm "$f"
done
```

**Note:** Simply deleting garbage files won't fix the root cause — the same raw session will likely produce another garbage summary on re-processing. The fix needs to happen in `call_ollama()` or the summarizer prompt to reliably extract structured output from thinking models.

## Batch Grading with Non-Thinking Models

When the grading stage is too slow (qwen3.5:9b produces 500-2000 token reasoning chains per file, ~90-120s each), switch to batch grading with a non-thinking model.

### Available Non-Thinking Models on hq-ai

From `GET /api/tags` (2026-06-03):

| Model | Size | Notes |
|-------|------|-------|
| `hermes3:8b` | 4.7 GB | Fast, reliable structured output. Best choice for grading. |
| `deepseek-coder:6.7b` | 3.8 GB | Smaller, faster. May work for grading. |
| `granite4.1:8b` | 5.3 GB | Alternative. |

### Batch Grading Script Pattern

Group multiple summaries into a single prompt, ask for `FILENAME:GRADE` output, parse results:

```python
RUBRIC = """Score each training example A, B, C, or D.
Return ONLY: FILENAME:GRADE for each, one per line. No explanation."""

# Group 5-10 summaries per batch
batch_prompt = "\n\n".join([
    f"--- EXAMPLE {i+1} ({name}) ---\n{text[:1500]}"
    for i, (name, text) in enumerate(batch)
])

payload = {
    "model": "hermes3:8b",  # non-thinking model
    "system": RUBRIC,
    "options": {"temperature": 0.0, "num_predict": 256}
}
```

**Observed performance (2026-06-03):** 21 files graded in ~180s (3 batches of 10/10/1), 8 kept (A/B), 13 deleted (C/D). Hermes3:8b reliably produced parseable `FILENAME:GRADE` output unlike qwen3.5:9b which buried grades in 2000-char reasoning chains.

### Why This Works

- Non-thinking models obey "return ONLY" instructions
- Batch mode reduces overhead (N files in 1 call vs N calls)
- Structured output format (`FILENAME:GRADE`) is reliably parseable
- Temperature 0.0 ensures deterministic grading

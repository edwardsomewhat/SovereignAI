# Re-Summarization Bug: Root Cause & Fix

## Discovery
2026-05-23: Pipeline run on 117 sessions. `processed/` held 27 files at start, but 110 were already in `curated/`. The summarize stage kept producing new summaries for already-graded sessions because `stage_grade()` had deleted their `processed/` files.

## Root Cause
In `training_pipeline.py`, the state machine has a gap:

```
Capture  →  Summarize  →  Grade
(raw/)      (processed/)   (curated/ or delete)
```

`stage_summarize()` skip-check:
```python
out_file = PROCESSED_DIR / f"{rf.stem}.txt"
if out_file.exists():
    continue
```

`stage_grade()` deletion:
```python
if grade in ("A", "B"):
    dest = CURATED_DIR / pf.name
    dest.write_text(text)
    pf.unlink()           # ← processed file DELETED
else:
    pf.unlink()           # ← also deleted for C/D
```

Result: every run, ALL raw files are re-summarized because no `processed/` files remain from the prior run.

## Fix
Add a curated-path guard in `stage_summarize()` (line ~184 of training_pipeline.py):

```python
for rf in raw_files:
    out_file = PROCESSED_DIR / f"{rf.stem}.txt"
    if out_file.exists():
        continue
    
    # NEW: skip if already graded and kept
    curated_file = CURATED_DIR / f"{rf.stem}.txt"
    if curated_file.exists():
        continue
    
    # ... rest of summarize logic
```

## Impact
- Before fix: 117 LLM summarize calls + 117 grade calls = 234 calls per run (110+ are wasted)
- After fix: only genuinely new sessions need processing
- Time savings: ~30+ minutes per scheduled run

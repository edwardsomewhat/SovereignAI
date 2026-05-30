# qwen3.5 Verbose Grading Output

## Problem

The grading stage system prompt explicitly says: *"Output ONLY the letter grade (A, B, C, or D). No explanation."*

qwen3.5:9b ignores this and outputs 500-2000 tokens of reasoning. Real output from 2026-05-24 run:

```
THINKING PROCESS:

1.  **ANALYZE THE REQUEST:**
    *   ROLE: TRAINING DATA QUALITY GRADER FOR THE SOVEREIGN AI PROJECT.
    *   TASK: SCORE EACH TRAINING EXAMPLE A, B, C, OR D BASED ON SPECIFIC CRITERIA.
    ... [hundreds of tokens of reasoning] ...

    *   THEREFORE, THE GRADE SHOULD BE D.

    *   WAIT, I NEED TO CHECK IF THE PROMPT IS ASKING ME TO *GENERATE* THE TEMPLATE...
    ... [more second-guessing] ...

*FINAL DECISION:* D.
```

The pipeline works because it takes the **last non-empty line** or the full response's trimmed uppercase — the letter is somewhere in the output. But the verbose output:

1. Wastes 20-40s per file (vs expected 1-3s)
2. Saturates Ollama throughput (blocking other consumers)
3. Fills Hermes process logs with noise (492 lines for 11 files)

## Why It Happens

- qwen3.5 is a "thinking" model — it naturally outputs reasoning before answers
- The `call_ollama()` function already handles `response` vs `thinking` fields, but both contain reasoning
- Simple "no explanation" instructions are systematically ignored by thinking-tuned models

## Root Cause: `grade in ("A", "B")` Is an Exact Match, Not a Substring Search

The grading code in `stage_grade()`:

```python
grade = call_ollama(text, system_prompt).strip().upper()
if grade in ("A", "B"):
    # keep
else:
    # delete
```

`grade in ("A", "B")` does an **exact match** of the full response against the single-letter strings `"A"` and `"B"`. When the model outputs 2000 characters of reasoning like `"THINKING PROCESS:\n...\nFINAL DECISION: B"`, the test fails — the full verbose string is not equal to `"A"` or `"B"`. **Both A/B and C/D sessions are deleted.**

The 1-2 keepers observed in some runs were sessions where the model happened to output just a single letter (rare). The 0-keeper runs occur when the model is verbose on every grading call. The underlying session quality doesn't matter — even sessions the model internally grades B are lost.

## Fix Options (not yet applied)

1. **Cap tokens**: `"num_predict": 5` in the Ollama payload for grade calls only — forces short output
2. **Post-process**: Regex extract `[ABCD]` from the response, or split on newline and take the last line before calling `.strip().upper()`. Most reliable for thinking models.
3. **Different prompt**: Use a system prompt that the model can't "reason around" — e.g., `"You are a classifier. Output exactly one character: A, B, C, or D."`
4. **Different model**: A non-thinking model for grading only. qwen3.5 thinking variants systematically ignore "no explanation" instructions.
5. **Parse thinking field separately**: For thinking models, Ollama returns `response` and `thinking` fields separately. The pipeline could read only `response` (the final answer token after thinking), not `thinking`. But qwen3.5 often puts the grade in `thinking` and leaves `response` empty — this needs testing.

## Impact on Recent Runs

| Date | Graded | Kept | Notes |
|------|--------|------|-------|
| 24 May | 18 | 0 | All C/D |
| 25 May (cron) | 22 | 1 | First keeper |
| 25 May (cron #2) | 23 | 1 | |
| 25 May (cron #3) | 29 | 1 | Orphaned files from interrupt |
| 26 May (cron) | 31 | 2 | Best keeper rate (6.5%) |
| 26 May (cron #2) | 31 | 1 | Clean run |
| 27 May (cron) | 34 | 0 | First all-delete since 24 May |
| 27 May (cron #2) | 36 | 0 | |
| 27 May (cron #3) | 38 | 1 | |
| 28 May (cron) | 52 | 3 | |
| 28 May (cron #2) | 51 | 2 | |
| 28 May (this run) | 49 | 0 | All 49 deleted. Model verbose on every call. No sessions happened to output bare letters. |
| 30 May (cron #2)  | 12¹ | 0 | All 12 deleted so far. 28 remaining when conversation cut off.¹ Pipeline ran without TRAINING_LLM_URL override (default IP 100.84.92.74 worked this session — but hq-ai hostname remains the safer choice). |

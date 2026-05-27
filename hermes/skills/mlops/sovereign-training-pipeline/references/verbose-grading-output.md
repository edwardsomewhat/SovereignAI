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

## Fix Options (not yet applied)

1. **Cap tokens**: `"num_predict": 5` in the Ollama payload for grade calls only — forces short output
2. **Post-process**: Regex extract `[ABCD]` from the first 100 chars, fallback to last line
3. **Different prompt**: Use a system prompt that the model can't "reason around" — e.g., `"You are a classifier. Output exactly one character: A, B, C, or D."`
4. **Different model**: A non-thinking model (e.g., `qwen3.5:3b` or a non-thinking variant) for grading only

## Impact on Recent Runs

| Date | Graded | Kept | Notes |
|------|--------|------|-------|
| 24 May | 18 | 0 | All C/D |
| 25 May (cron) | 22 | 1 | First keeper |
| 25 May (cron #2) | 23 | 1 | |
| 25 May (cron #3) | 29 | 1 | Orphaned files from interrupt |
| 26 May (cron) | 31 | 2 | Best keeper rate (6.5%) |
| 26 May (cron #2) | 31 | 1 | Clean run |
| 27 May (cron) | 34 | 0 | First all-delete since 24 May; model possibly upgraded |

**⚠️ 27 May observation:** All 34 graded files received C/D. Previous runs consistently had 1-2 keepers. The model may have been upgraded to a newer thinking variant where the chain-of-thought completely takes over the response field, burying the grade letter beyond what `.strip().upper()` can recover.

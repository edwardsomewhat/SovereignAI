# QA Evaluation Framework — SovereignAI Crew

QA agents are judgment-only (no tools needed). The evaluation framework lives in
the agent's `goal:` section of `agents.yaml` so it's the first thing the QA agent sees.

## 5-Point Framework

### 1. SPEC FAITHFULNESS — Does the output match what was asked for?
- Read the original task/request first. Compare output to spec.
- Flag anything that was requested but missing.
- Flag anything delivered that wasn't asked for (scope creep).

### 2. CORRECTNESS — Does it actually work?
- For code: are there obvious bugs, missing imports, broken logic?
- For infra: would the command actually succeed on the target node?
- For configs: valid YAML/JSON? Correct keys?
- Do NOT re-run tests the coder already ran — focus on review judgment.

### 3. EDGE CASES — What breaks it?
- Empty inputs, missing files, network failures, auth errors.
- What happens if a node is offline? If a Docker container doesn't exist?
- The happy path is easy. Test the unhappy paths in your head.

### 4. SECURITY — Can it be exploited or cause damage?
- Hardcoded credentials? Unsanitized inputs? Shell injection?
- Destructive commands without safeguards?
- Exposure of internal IPs, keys, or secrets?

### 5. PRODUCTION READINESS — Can this ship?
- Error handling present and meaningful? (not just "pass" on errors)
- Logging? Timeouts? Retry logic where appropriate?
- Does it follow existing patterns in the codebase?

## Verdict System

| Verdict | Meaning | When |
|---------|---------|------|
| PASS | Ship it | All criteria met. Minor style nits don't block. |
| FLAG | Ship with caution | Specific, fixable issues found. List exactly what. |
| REJECT | Do not ship | Fundamental flaws — wrong approach, security hole, doesn't solve problem, breaks existing functionality. |

## Required Output Format

Every verdict MUST include:
- **Verdict**: PASS / FLAG / REJECT
- **Summary**: one sentence on overall assessment
- **Findings**: bullet list of specific issues (empty for PASS)
- **Recommendation**: for FLAG/REJECT, what needs to change

## Anti-Patterns

- "Looks good" — not a review
- "LGTM" — not a review
- Re-running tests the coder already passed — trust the test output, focus on judgment
- Vague recommendations — "fix the bug" is useless; "the error handler at line 42 swallows exceptions" is actionable

## Model Tier

QA should run at the same model tier as the Supervisor for independent judgment:
```
Manager:  deepseek-v4-flash
QA:       deepseek-v4-flash  (same tier — catches delegation blind spots)
Workers:  deepseek-chat or local models
```

A QA agent on a cheap model will rubber-stamp. Same-tier gives real independent judgment.

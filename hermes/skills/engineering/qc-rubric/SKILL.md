---
name: qc-rubric
description: Quality control evaluation rubrics per domain — measurable pass/fail criteria for code, images, copy, config, and infrastructure. Used by the QC agent and referenced by all worker agents to format their output for QC checks.
---

# QC Rubric — Domain-Specific Evaluation Criteria

Every domain has a checklist of measurable items. QC returns APPROVE only when all required items pass.

## Code

| # | Dimension | Measurable Item | Required | How to Check |
|---|-----------|----------------|----------|--------------|
| C1 | Correctness | All tests pass (new + existing) | YES | Run test suite, verify exit code 0 |
| C2 | Correctness | Diff only touches files relevant to GOAL | YES | Inspect diff scope |
| C3 | Safety | No hardcoded secrets, tokens, or keys | YES | Scan diff for credential patterns |
| C4 | Safety | No regression — existing functionality unchanged | YES | Existing tests still pass |
| C5 | Style | Follows codebase conventions (lint clean) | NO | Run linter, count new warnings |
| C6 | Style | Functions/classes have clear names and purpose | NO | Manual review |

## Image

| # | Dimension | Measurable Item | Required | How to Check |
|---|-----------|----------------|----------|--------------|
| I1 | Subject | Primary subject matches GOAL description | YES | Vision model comparison |
| I2 | Subject | Image style matches requested style (photorealistic, illustration, etc.) | YES | Vision model assessment |
| I3 | Quality | No visible artifacts, corruption, or glitches | YES | Technical quality scan |
| I4 | Quality | Resolution meets minimum specified in GOAL | YES | Check file dimensions |
| I5 | Legibility | All text in image is readable and correct (if applicable) | NO | OCR + comparison |
| I6 | Legibility | No offensive or inappropriate content | YES | Content safety scan |

## Copy / Ad Text

| # | Dimension | Measurable Item | Required | How to Check |
|---|-----------|----------------|----------|--------------|
| T1 | Voice | Matches brand voice guidelines | YES | Compare to voice reference |
| T2 | Accuracy | All stated facts, prices, dates are correct | YES | Verify against GOAL spec |
| T3 | Grammar | No spelling or grammar errors | YES | Automated grammar check |
| T4 | CTA | Call-to-action is present and clear | YES | Contains actionable verb + link/instruction |
| T5 | Length | Within specified word/character limit | NO | Word count check |
| T6 | Tone | Appropriate for target audience/demographic | NO | Tone analysis |

## Config / Infrastructure

| # | Dimension | Measurable Item | Required | How to Check |
|---|-----------|----------------|----------|--------------|
| N1 | Syntax | Config parses without errors (YAML/JSON/TOML valid) | YES | Parse with language tool |
| N2 | No Conflicts | No port, path, or name collisions with existing config | YES | Compare against INITIAL STATE |
| N3 | Secrets | No hardcoded credentials, keys, or tokens | YES | Pattern scan |
| N4 | Idempotent | Can be applied multiple times without side effects | NO | Reasoning check |
| N5 | Backward | Compatible with existing services/consumers | NO | Dependency check |

## QC Response Format

All QC checks return this exact format:

```
QC VERDICT: APPROVE | REJECT
SENSE CHECK: PASS | FLAG | ESCALATE
  — [one-line assessment]
PASSED: [list of passed item IDs]
FAILED: [list of failed item IDs with one-line reason each]
NOTES: [optional — suggested fix, observations, context]
```

Required items that fail = automatic REJECT. Non-required items that fail = noted but don't block. 

SENSE CHECK is the reasoning layer on top of the mechanics:
- PASS: result matches intent, approach is sound
- FLAG: result is mechanically correct but approach has issues — noted, may independently REJECT
- ESCALATE: fundamental problem detected (wrong architecture, security risk, downstream cascade). Bypasses strike system. Supervisor is notified immediately with full context.

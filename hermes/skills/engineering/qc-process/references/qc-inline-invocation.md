# QC Inline Invocation Template

When the `qc-handoff` skill name is ambiguous or the QC profile lacks skill-loading capability, inline the rubric directly in the prompt. Copy-paste this template, replacing `{TASK_ID}` and `{DOMAIN}`.

```bash
qc chat -q "Read /tmp/qc-handoff-{TASK_ID}.md and evaluate against the {DOMAIN} rubric:

{CODE|IMAGE|COPY|CONFIG|INFRA} domain required items:
[list the required rubric item IDs and descriptions from qc-rubric]
Optional items:
[list optional items]

Also do a SENSE CHECK: does the result match intent? Is the approach sound? Any architectural or security concerns?

Return:
QC VERDICT: APPROVE | REJECT
SENSE CHECK: PASS | FLAG | ESCALATE
  — [one-line assessment]
PASSED: [list of passed item IDs]
FAILED: [list of failed item IDs with one-line reason each]
NOTES: [optional — suggested fix, observations, context]" --quiet
```

## Example — CODE domain

```bash
qc chat -q "Read /tmp/qc-handoff-coders-001.md and evaluate the code output against this rubric:

CODE domain:
C1: All tests pass (new + existing) — REQUIRED
C2: Diff only touches files relevant to GOAL — REQUIRED
C3: No hardcoded secrets, tokens, or keys — REQUIRED
C4: No regression — existing functionality unchanged — REQUIRED
C5: Follows codebase conventions (lint clean) — optional
C6: Functions/classes have clear names and purpose — optional

Also do a SENSE CHECK: does the result match intent? Is the approach sound? Any architectural concerns?

Return:
QC VERDICT: APPROVE | REJECT
SENSE CHECK: PASS | FLAG | ESCALATE
  — [one-line assessment]
PASSED: [list]
FAILED: [list with reasons]
NOTES: [optional]" --quiet
```

This approach produced a correct APPROVE + SENSE CHECK PASS on the coders-001 handoff without loading any skills.

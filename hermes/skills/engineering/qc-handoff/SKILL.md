---
name: qc-handoff
description: Format specification for agent→QC handoff packets. Workers use this to package their output for QC review. Loaded by worker agents before hitting QC checkpoints and by the QC agent to parse incoming reviews.
---

# QC Handoff — Agent→QC Packet Format

When a worker agent completes a task requiring QC review, it produces a handoff file at `/tmp/qc-handoff-{TASK_ID}.md` using the `/handoff` skill with this structure:

## Packet Structure

```
# QC HANDOFF | {TASK_ID}
## AGENT
{agent_name} | attempt {1|2|3}
## DOMAIN
{code|image|copy|config|infra} — selects which rubric to use
## INITIAL STATE
{file contents before, config state, system metrics — only what's relevant}
## GOAL
{the task as assigned, including explicit success criteria}
## RESULT
{what was produced: unified diff, image path, config snippet, deployment endpoint}
## TRAJECTORY (only on attempt 2+)
{compressed session summary — key decisions, tool calls, reasoning}
```

## Rules

- INITIAL STATE: Include ONLY what changed. Not the entire codebase. If modifying auth.py, include the original auth.py. Not every file in the project.
- GOAL: Copy verbatim from the task assignment. Include any explicit "must have" or "must not" constraints.
- RESULT: For code, use unified diff format (`diff -u original modified`). For images, use absolute path. For config, show only changed sections.
- TRAJECTORY: Only included on re-attempts (strike 2+). On first attempt, QC only evaluates outcome. On re-attempt, trajectory helps QC understand what went wrong.
- Token budget: The entire handoff file should stay under 8K tokens for local model processing. If a result is larger (e.g., a full codebase change), include only the key functions/sections that changed.

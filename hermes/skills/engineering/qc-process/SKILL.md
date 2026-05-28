---
name: qc-process
description: The 3-strike QC escalation flow — when and how workers invoke QC, how re-attempts work, fallback behavior, and escalation rules. Loaded by all agents that have QC-gated actions.
---

# QC Process — 3-Strike Escalation

## When QC Is Triggered

A worker agent hits a QC checkpoint when:
- It has produced an output that will be deployed, merged, delivered, or executed
- Its task definition includes `qc_required: true`
- It's performing a gated action (Infra restarts, DB migrations, Creative deliveries)

## Flow

### Strike 1 — Initial Review

1. Worker completes task → produces RESULT
2. Worker loads `qc-handoff` skill → creates `/tmp/qc-handoff-{TASK_ID}.md` using `/handoff`
3. Worker loads `qc-rubric` skill → invokes QC agent:
   ```
   infra chat -q "QC check: /tmp/qc-handoff-{TASK_ID}.md against rubric domain {DOMAIN}. Load qc-handoff and qc-rubric skills."
   ```
4. QC returns: APPROVE | REJECT + notes
5. If APPROVE → task complete, deliver/merge/deploy
6. If REJECT → go to Strike 2

### Strike 2 — V4 Flash Fallback (1M context)

1. Worker starts fresh session
2. Loads original `/tmp/qc-handoff-{TASK_ID}.md`
3. Loads QC notes from Strike 1
4. Does NOT compress — v4-flash has 1M context
5. Fixes issues using QC notes as guidance
6. Produces new handoff with attempt=2, includes TRAJECTORY section
7. Re-invokes QC
8. Supervisor is notified that Strike 2 is in progress
9. If APPROVE → done
10. If REJECT → go to Strike 3

### Strike 3 — Escalation

1. QC notifies supervisor with full context:
   - Both failed attempts
   - All QC notes
   - Current state
2. Supervisor decides: reassign to different agent, user intervention, or accept with override
3. User is notified

## Escalation Triggers

QC can escalate to supervisor through two paths:

### Path A — Strike Escalation (mechanical)
Three consecutive REJECT verdicts → supervisor notified with all attempts and notes.

### Path B — SENSE CHECK ESCALATE (reasoning)
If QC's SENSE CHECK returns ESCALATE, the strike system is bypassed entirely. QC immediately notifies supervisor with:
- The handoff that triggered the escalation
- The specific concern (architectural, security, downstream risk)
- Recommendation: halt task, reassign, or user consult
- A QUESTION: "Can this condition be ignored going forward?"

Supervisor may respond:
- **Override (one-time):** "Proceed this time." Task continues, pattern not stored.
- **Override (permanent):** "Approved. Ignore this pattern in future." QC saves the pattern as a learned exception — future reviews skip this specific concern.
- **Halt:** Kill the task, reassign, or escalate to user.
- **Clarify:** Ask QC for more detail before deciding.

### Learned Exceptions

When supervisor permanently overrides a SENSE CHECK concern, QC records it:

```
QC EXCEPTION | {pattern}
SENSE CHECK: {the concern that was escalated}
SUPERVISOR: "Approved — ignore in future"
DATE: {timestamp}
```

Exceptions are stored in `/home/fated/.hermes/profiles/qc/exceptions.yaml`. QC loads these at the start of every review. If a new handoff matches a stored exception, the SENSE CHECK notes "matches exception X" and does not escalate.

## Agent QC Checkpoint Locations

Each agent's SOUL.md or workflow includes designated QC points:

| Agent | QC Checkpoint |
|-------|---------------|
| Coders | Before merge/deploy |
| Creative | Before image delivery to Telegram/user |
| Web Dev | Before deployment to csweb |
| DB Manager | Before migration execution |
| Infra | Before destructive actions (restart, kill) |
| Cloudflare | Before DNS changes |
| Payments | Before production payment code deploy |
| QA | Self-checks own test results |
| N8N Manager | Before workflow activation |
| Vision | Before analysis results delivered |

## Pitfalls

### Ambiguous skill name: qc-handoff

The skill name `qc-handoff` matches TWO files in the skills directory:
- `engineering/qc-handoff/SKILL.md` — the format spec
- `engineering/qc-agent/templates/qc-handoff.md` — a template copy

When you run `qc chat -s qc-handoff`, Hermes refuses: `Ambiguous skill name — 2 skills match`.

**Workaround A — use full path:**
```bash
qc chat -s engineering/qc-handoff -s qc-rubric -q "QC check: /tmp/qc-handoff-{TASK_ID}.md..."
```

**Workaround B — inline the rubric (faster, no skill-load overhead):**
Pass the rubric items and response format directly in the prompt. This avoids the ambiguous-skill issue entirely and works with file-tools-only profiles. See `references/qc-inline-invocation.md` for a copy-paste ready prompt template.

### QC profile needs DEEPSEEK_API_KEY or OPENROUTER_API_KEY

The qc profile uses minimax-m2.7 via OpenRouter. If the `.env` is missing `OPENROUTER_API_KEY`, QC invocations fail silently. Verify with `grep OPENROUTER ~/.hermes/profiles/qc/.env`.

## Token Budgets

| Stage | Model | Max Tokens |
|-------|-------|------------|
| Strike 1 (handoff) | Local (hermes3:8b) | 8K |
| Strike 1 (QC review) | API (minimax-m2.7) | 4K prompt, 1K response |
| Strike 2 (worker fix) | API (v4-flash) | 1M context, no compress |
| Strike 2 (QC review) | API (minimax-m2.7) | 8K prompt (includes trajectory) |
| Strike 3 (supervisor) | API (deepseek-v4-pro) | Full context |

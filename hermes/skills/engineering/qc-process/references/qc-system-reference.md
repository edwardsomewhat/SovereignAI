# QC System Reference

Built May 21-22, 2026. The SovereignAI quality control gate.

## Architecture

Three skills define the protocol. One profile executes it. All agents share the same skills — zero context window cost, just `load skill`.

## Skills

### qc-rubric
Five domains with measurable pass/fail criteria:
- **Code**: tests, secrets, regression, lint, scope (C1-C6)
- **Image**: subject, style, artifacts, resolution, legibility, safety (I1-I6)
- **Copy**: voice, accuracy, grammar, CTA, length, tone (T1-T6)
- **Config**: syntax, conflicts, secrets, idempotency, backward compat (N1-N5)
- **Infra**: service response, disk, logs (N1-N5 reused)

Each item marked Required or Not. Required failures = automatic REJECT.

### qc-handoff
Agent→QC packet format. Workers produce `/tmp/qc-handoff-{TASK_ID}.md`:
- AGENT, DOMAIN, INITIAL STATE, GOAL, RESULT, TRAJECTORY (strike 2+)
- 8K token budget for local models. Include only what changed.

### qc-process
Two escalation paths:
- **Path A (Strike)**: 3 consecutive REJECTs → supervisor
- **Path B (SENSE CHECK ESCALATE)**: Bypasses strikes. Supervisor gets a question: "Can this condition be ignored going forward?" Supervisor can permanently override → stored in exceptions.yaml

## QC Profile
- Location: `~/.hermes/profiles/qc/`
- Model: minimax-m2.7 via OpenRouter (strong reasoning, cheap)
- Tools: file only (reads handoffs)
- Wrapper: `qc chat`
- Personality: concise, verdict-only output
- Exceptions: `/home/fated/.hermes/profiles/qc/exceptions.yaml`

## Response Format
```
QC VERDICT: APPROVE | REJECT
SENSE CHECK: PASS | FLAG | ESCALATE — [one-line]
PASSED: [items]
FAILED: [items with reason]
NOTES: [optional]
```

## Key Design Decisions
- SENSE CHECK uses the model's reasoning, not just checklist — catches architectural problems rubrics miss
- Skills as protocol, not prompt bloat — agents load the skill, don't carry the instructions
- ESCALATE is a conversation, not a fire alarm — supervisor can permanently override
- Three-strike system with progressive fallback: local model → v4-flash (1M ctx) → supervisor
- Token budgets per stage to prevent context window blowout on 8B local models

## Agent QC Checkpoints
Coders (pre-merge), Creative (pre-delivery), Web Dev (pre-deploy), DB Manager (pre-migration), Infra (destructive actions), Cloudflare (DNS changes), Payments (production code), QA (self-check), N8N (workflow activation), Vision (analysis results)

## Industry Basis
Built on Anthropic's agent evals framework (outcome + trajectory grading) and Galileo's 3-tier rubric taxonomy (dimension → sub-dimension → measurable item). LLM-as-judge calibrated for 0.80+ Spearman correlation target.
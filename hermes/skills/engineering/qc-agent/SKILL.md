---
name: qc-agent
description: Quality Control agent design for the SovereignAI CrewAI system — 3-strike escalation, domain rubrics, handoff format, and QC checkpoint pattern. Use when building or modifying the QC agent profile or defining quality gates for crew tasks.
---

# QC Agent — SovereignAI Quality Gate

The QC agent is a verifier, not a builder. It receives task output from worker agents, evaluates it against a domain-specific rubric, and returns PASS/FLAG/REJECT with notes.

> **Updated 2026-05-25**: The QA agent in SovereignAI now uses a simplified 5-point
> evaluation framework (spec faithfulness, correctness, edge cases, security,
> production readiness) instead of domain-specific rubrics. See
> `crewai-setup` → `references/qa-evaluation-framework.md` for the current framework.
> The 3-strike escalation below is still valid for gated workflows.

## Architecture

### 3-Strike Escalation Loop

```
Worker completes task → hits QC checkpoint
  │
  ▼
Session compressed via /handoff → /tmp/qc-handoff-{task_id}.md
  │
  ▼
QC agent evaluates against rubric
  │
  ├── APPROVE → task ships
  │
  └── REJECT + notes
        │
        Strike 1: fresh session, load handoff + QC notes, fix
        │
        Strike 2: fallback to v4-flash (1M ctx, no compress), supervisor notified
        │
        Strike 3: escalate to supervisor, user notified
```

### Handoff Format (what the worker passes to QC)

```markdown
# QC HANDOFF | {task_id} | Strike {1|2|3}
## INITIAL STATE
{system config, file contents, service status, disk usage before the task}

## GOAL
{task description with measurable success criteria}

## RESULT
{output: code diff, image path, config change, deployment endpoint, new system state}

## TRAJECTORY (only loaded on Strike 2+)
{tool calls, reasoning steps, decision points}
```

### QC Return Format

```markdown
# QC VERDICT | {task_id}
## VERDICT: APPROVE | REJECT
## SCORE: {dimension scores}
## NOTES
{itemized issues or praise}
## SOLUTION_PATH (if known)
{concrete fix directions — only if the fix is obvious and cheap}
```

## Domain Rubrics

Each domain has measurable items. QC scores each item, returns aggregate verdict.

### Code

| Dimension | Measurable Items |
|-----------|-----------------|
| Correctness | All unit tests pass, integration tests pass |
| Safety | No hardcoded secrets, no auth bypasses, no injection vectors |
| Style | Matches codebase conventions, lint clean |
| Completeness | All edge cases handled, error states covered |

### Image

| Dimension | Measurable Items |
|-----------|-----------------|
| Subject Accuracy | Matches prompt description, correct subject present |
| Quality | Correct resolution, no visible artifacts, proper composition |
| Legibility | If text present: readable, correct spelling, properly rendered |
| Format | Correct file format, appropriate file size |

### Copy / Ad Copy

| Dimension | Measurable Items |
|-----------|-----------------|
| Voice | On-brand tone, matches SovereignAI voice guide |
| Accuracy | Facts correct, no false claims, no hallucinations |
| Grammar | Clean grammar, no typos, professional presentation |
| CTA | Call-to-action present, clear next step for reader |

### Config / Infrastructure

| Dimension | Measurable Items |
|-----------|-----------------|
| Syntax | Valid YAML/JSON/TOML, no parse errors |
| No Conflicts | No port collisions, no duplicate keys, no broken references |
| No Secrets | No hardcoded API keys, passwords, or tokens |
| Service Health | Target service responds, no cascading failures |

### Deployment

| Dimension | Measurable Items |
|-----------|-----------------|
| Pre-deploy State | Snapshot of system before deployment |
| Post-deploy State | Service responds, health check passes |
| Rollback Plan | Reversible change, rollback script available |
| Monitoring | Logs clean, no unexpected errors after deploy |

### General (applies to all domains)

| Dimension | Measurable Items |
|-----------|-----------------|
| Goal Alignment | Output satisfies the stated GOAL |
| No Regression | INITIAL STATE functionality preserved |
| Token Efficiency | Solution is minimal, no bloat |

## QC Checkpoints Per Agent

| Agent | When QC gates |
|-------|--------------|
| Coders | Before merge/deploy to any branch |
| Web Dev | Before deployment to csweb |
| Creative | Before image/video delivery to user or Telegram |
| DB Manager | Before migration execution |
| Infra | Before destructive actions (restart, kill, rm) |
| Cloudflare | Before DNS changes go live |
| Payments | Before any transaction-affecting change |

## Usage

When building or modifying the QC agent profile:
1. Load this skill for the rubric structure
2. Clone the infra profile as a starting template
3. Set model to OpenRouter MiniMax M2.7
4. Install the handoff skill (`hermes skills install handoff`)
5. Define the QC checkpoint in each worker agent's SOUL.md

## Pitfalls

- QC is not a supervisor — it only approves/rejects, it does not reassign work
- Trajectory data is expensive in tokens — only load on Strike 2+
- Rubrics must be measurable: "looks professional" is not measurable; "no grammar errors, CTA present, on-brand tone" is
- The handoff file must include INITIAL STATE — without it, QC can't detect regressions

# SovereignAI Crew Architecture — C+D Hybrid

Decision from May 21, 2026 session. CrewAI decomposes and routes. Each worker agent is a full Hermes profile with isolated memory, tools, and session history. One Hermes install on sovereign, profiles point to different compute nodes.

## Why This Model

- **Option A (CrewAI native tools):** Reimplementing everything Hermes already has — terminal, SSH, file system, web. Non-starter.
- **Option B (CrewAI calls Hermes via API):** Adds indirection. Works but messy.
- **Option C (Hermes as execution layer):** Each worker is a standalone Hermes process. Full tools, memory, sessions. Supervisor coordinates.
- **Option D (Spaces as interface):** Space Agent dashboard wraps each profile as a "room" the user can enter.
- **C+D hybrid (chosen):** CrewAI decomposes/routes. Workers are Hermes profiles. Space Agent is the visual layer.

## How It Works

```
sovereign (one Hermes install)
  ├─ profile: vern (supervisor)  → DeepSeek V4 Pro API
  ├─ profile: infra              → hq-ai Ollama hermes3:8b
  ├─ profile: coders             → TBD (probably TheConch or hq-ai)
  ├─ profile: creative           → TBD
  ├─ profile: qa                 → TBD
  └─ ...etc
```

Key properties:
- One install to maintain
- Per-agent memory and session history (profiles are isolated)
- Compute load-balanced across nodes (hq-ai, TheConch, nano)
- Individual chat: `hermes --profile infra` drops you into infra's room
- Group chat: supervisor orchestrates the crew via CrewAI hierarchical process
- Training data naturally captured per profile via session mining pipeline

## Build Priority

1. Tier 1: Infra ✅ + Coders (parallel)
2. Tier 2: Web Dev + Creative
3. Tier 3: Cloudflare + DB Manager
4. Tier 4: Payments + QA
5. Tier 5: N8N + Vision

## Profile Creation Pattern

```bash
hermes profile create <name> --clone-from default
# Then customize: hermes config set model.provider custom:hq-ollama --profile <name>
# Add SOUL.md: ~/.hermes/profiles/<name>/SOUL.md
# Create wrapper: hermes profile alias <name>
```

Each profile gets the same starting toolkit. Differentiated only by what it builds.

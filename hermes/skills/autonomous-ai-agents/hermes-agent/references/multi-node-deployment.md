# Multi-Node Hermes Deployment with Skill Sync

This workflow keeps multiple Hermes nodes (e.g., conchai and sovereign) identical in skills and configuration using a shared git repo.

## Architecture

```
conchai (image gen node)          sovereign (orchestrator)
    │                                    │
    │  sovereign-sync.sh                 │  manual rsync
    │  (cron every hour)                  │  from repo
    ▼                                    ▼
┌─────────────────────────────────────────────┐
│     SovereignAI git repo (GitHub)           │
│     hermes/                                 │
│       skills/     (rsync'd from conchai)    │
│       config.yaml (sanitized, no secrets)   │
│       SOUL.md     (persona)                 │
│     scripts/                                │
│       sovereign-sync.sh                     │
│     systemd/                                │
│       hermes-dashboard.service              │
│       firecrawl.service                     │
└─────────────────────────────────────────────┘
```

## Setup on a New Node

```bash
# 1. Clone the repo (needs GitHub SSH key or PAT)
git clone git@github.com:edwardsomewhat/SovereignAI.git ~/repos/sovereign-ai

# 2. Sync skills from repo to Hermes
rsync -a ~/repos/sovereign-ai/hermes/skills/ ~/.hermes/skills/

# 3. Sync config and persona
cp ~/repos/sovereign-ai/hermes/SOUL.md ~/.hermes/SOUL.md
# config.yaml: merge manually or use hermes config set commands
```

## Sync from Conchai to Repo

The sync script at `~/.hermes/scripts/sovereign-sync.sh`:
- Compares and copies config.yaml, SOUL.md
- Rsyncs entire skills directory
- Copies systemd service files
- Detects untracked files (new skills)
- Auto-commits and pushes to GitHub

```bash
# Run manually:
bash ~/.hermes/scripts/sovereign-sync.sh

# Or set up cron (runs hourly):
# hermes cron create "0 * * * *" --script ~/.hermes/scripts/sovereign-sync.sh --no-agent
```

## Pitfalls

- **GitHub PAT issues**: Classic PATs (`ghp_*`) are being phased out. Use SSH key auth on sovereign.
- **Untracked files**: The sync script (v1) didn't detect new/untracked files. Fixed in the version committed to the repo.
- **Secrets**: Never commit `.env` files. The `config.yaml` has empty API key fields.
- **Large skills**: Full skill sync is ~12MB. Rsync is efficient for incremental changes.

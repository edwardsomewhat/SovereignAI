# Multi-Node Hermes Deployment

Pattern for deploying identical Hermes builds across multiple machines on a
Tailscale tailnet, using a Git repo as the source of truth.

## Architecture

```
conchai (image gen node)
    │
    ├── hermes skills/config/persona
    ├── sovereign-sync.sh (cron: push to repo)
    │
    ▼
  GitHub (SovereignAI repo)
    │
    ▼
sovereign (orchestrator node)
    │
    ├── git clone → rsync skills
    └── Fresh memory/sessions per node
```

## Node Setup Checklist

### 1. Install Hermes on target node
```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

### 2. Copy config from source node
```bash
# API keys only (secrets NOT in repo)
scp source:.hermes/.env target:.hermes/.env

# Model config
hermes config set model.default deepseek-v4-pro
hermes config set model.provider deepseek
hermes config set model.base_url https://api.deepseek.com/v1
```

### 3. Enable passwordless SSH between nodes
```bash
# From source node
cat ~/.ssh/id_ed25519.pub | ssh user@target 'cat >> ~/.ssh/authorized_keys'
```

### 4. Clone the skills repo
```bash
git clone git@github.com:USER/REPO.git ~/repos/REPO
rsync -a ~/repos/REPO/hermes/skills/ ~/.hermes/skills/
```

### 5. Verify parity
```bash
echo "Source: $(ssh source 'find ~/.hermes/skills -name SKILL.md | wc -l')"
echo "Target: $(find ~/.hermes/skills -name SKILL.md | wc -l)"
```

## Sync Script (runs on source node)

The sync script pushes skills, config, SOUL.md, and systemd files to the Git repo.
Cron job runs every hour. Key behaviors:

- `rsync -a --delete` mirrors skills exactly
- `git diff --quiet` checks for tracked file changes
- `git ls-files --others` catches new/untracked files  
- Systemd service files are pulled from `/etc/systemd/system/` and `~/.config/systemd/user/`

## Divergence Strategy

- **Base template:** both nodes identical (skills, config, tools)
- **Post-divergence:** each node gets role-specific additions
  - Image gen node: ComfyUI models, image workflows
  - Orchestrator node: crew agents, RAG database
- **Shared core:** skills, persona, sync pipeline stay synced

## Pitfalls

1. **GitHub PAT expiration** — Classic PATs (`ghp_*`) get rejected for HTTPS git operations. Use SSH keys instead. Register each node's key at github.com/settings/keys.
2. **Untracked files in sync** — `git diff --quiet` only checks tracked files. New files (untracked) won't trigger a sync commit. Fix: add `git ls-files --others` check to the sync script.
3. **Memory/sessions are node-specific** — Don't rsync `memories/`, `sessions/`, or `state.db`. Each node builds its own context.
4. **Different sudo passwords per node** — The network map and memory track these separately. Don't assume one password works everywhere.

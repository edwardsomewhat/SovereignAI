---
name: hermes-node-bootstrap
description: Replicate a Hermes Agent node's full configuration (config, skills, systemd services) across machines via a git repo. Use when the user wants to clone their Hermes setup to a new machine, maintain consistent agent config across a fleet, or bootstrap a fresh host with their existing skill library.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [devops, replication, bootstrap, setup, fleet-management]
    related_skills: [hermes-agent, import-external-agent-skills, github-auth]
---

# Hermes Node Bootstrap

## Overview

A Hermes Agent node accumulates a lot of configuration over time: customized `config.yaml`, a `SOUL.md` persona, 100+ skills, systemd service definitions, and environment variables. When you want to replicate this setup to another machine — a new server, a second workstation, a Tailscale-connected box — you need a repeatable process.

This skill covers **packaging a Hermes node for replication** and **bootstrapping fresh machines** from the repo.

## When to Use

- User wants to "put this Hermes setup elsewhere"
- User asks to "keep this setup consistent across machines"
- User wants to clone their config+skills+services into a git repo for DR
- User asks for a setup script that new machines can run
- User references "scattered around the network" nodes that should converge

## Workflow: Packaging a Hermes Node for Replication

### Step 1: Create the repo structure

```
sovereign-node/
├── hermes/
│   ├── config.yaml       # Hermes Agent configuration
│   ├── SOUL.md           # Agent persona (optional)
│   └── skills/           # Full skill tree
├── systemd/
│   └── *.service         # Service definitions
├── setup.sh              # Bootstrap script
├── .gitignore            # Excludes secrets
└── README.md
```

### Step 2: Copy config (redact secrets)

```bash
# Copy the config — config.yaml typically has empty `api_key: ''` fields (safe)
cp ~/.hermes/config.yaml hermes/config.yaml

# Copy SOUL.md
cp ~/.hermes/SOUL.md hermes/SOUL.md

# Copy skills tree
cp -r ~/.hermes/skills/* hermes/skills/

# Copy systemd services
sudo cp /etc/systemd/system/hermes-*.service systemd/
sudo cp /etc/systemd/system/firecrawl*.service systemd/
```

**Check the config first for secrets:**
```bash
grep -n -i "api_key\|token\|password\|secret" ~/.hermes/config.yaml
```
Config fields like `api_key: ''` (empty string) are safe. Environment variables in `.env` are NOT — that file must never be committed.

### Step 3: Set up .gitignore

```gitignore
# Secrets — NEVER COMMIT
.env
*.env
*token*
*credential*

# OS junk
.DS_Store
Thumbs.db
*.swp
*~

# Python
__pycache__/
*.pyc
.venv/
venv/
```

**Do NOT commit `~/.hermes/.env`** — it contains API keys and the GITHUB_TOKEN.

### Step 4: Create the bootstrap script

The setup script should:
1. Install Hermes Agent (if not installed)
2. Apply config.yaml, SOUL.md, and skills
3. Install systemd services (with sudo)
4. Print next steps (configure secrets, start services)

```bash
#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

# 1. Install Hermes Agent
if ! command -v hermes &>/dev/null; then
    curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
fi

# 2. Apply configuration
mkdir -p ~/.hermes
cp -r "$REPO_DIR/hermes/config.yaml" ~/.hermes/config.yaml
cp -r "$REPO_DIR/hermes/SOUL.md" ~/.hermes/SOUL.md 2>/dev/null || true

# 3. Install skills
rm -rf ~/.hermes/skills
cp -r "$REPO_DIR/hermes/skills" ~/.hermes/skills

# 4. Install systemd services (if present)
if [ -d "$REPO_DIR/systemd" ]; then
    for svc in "$REPO_DIR/systemd/"*.service; do
        sudo cp "$svc" "/etc/systemd/system/$(basename "$svc")"
        sudo systemctl daemon-reload
        sudo systemctl enable "$(basename "$svc")" 2>/dev/null || true
    done
fi

echo "Setup complete. Next steps:"
echo "  1. Configure API keys: $EDITOR ~/.hermes/.env"
echo "  2. Start services: sudo systemctl start hermes-dashboard"
```

### Step 5: Write a self-documenting README

The README should describe:
- What the repo contains (config, skills, services)
- Quick start instructions
- Node requirements (OS, Python, Tailscale)
- The vision/intent behind the node

## Workflow: Bootstrapping a Fresh Machine

### From a cloned repo

```bash
git clone https://github.com/<user>/<repo>.git
cd <repo>
./setup.sh

# Then configure secrets
hermes config edit   # or set GITHUB_TOKEN in ~/.hermes/.env
```

### Verify the setup

```bash
# Check skills installed
find ~/.hermes/skills -name "SKILL.md" | wc -l

# Check config applied
hermes config | head -10

# Check services
systemctl list-units --type=service | grep hermes
```

## Git Config for Repo Commits

When pushing to the repo from an agent session, set the git identity:

```bash
cd <repo>
git config user.name "Nicholas Schweska"
git config user.email "edwardsomewhat@gmail.com"
```

Use `git add -A && git commit -m "<message>" && git push origin main` for initial bulk pushes. The repo should be `--private` since it contains configuration patterns you may not want public.

## Common Pitfalls

1. **Committing .env or secrets.** The `.env` file contains API keys and the GITHUB_TOKEN. Always gitignore it. Triple-check before commit with `git diff --cached --name-only | grep -i env`.

2. **Including personal/ or deprecated/ skills.** User-local skill trees often contain `personal/`, `deprecated/`, or `in-progress/` buckets. These are personal drafts and should not be replicated. Either exclude them or add them to `.gitignore`.

3. **Forgetting systemd services.** On a fresh machine, the services won't exist. Include the `.service` files in a `systemd/` directory so the bootstrap script can install them.

4. **Config differences between machines.** If the new machine has different hardware (GPU vs CPU, different disk layout), the config may need tuning. Document per-machine overrides in the README.

5. **Not verifying after commit.** After pushing the initial commit, always check the remote repo for accidental secrets and verify the file structure is correct.

6. **Expecting the bootstrap to work without Tailscale.** If your network relies on Tailscale (node IPs, `--insecure` dashboard flags, cross-machine file access), the bootstrap script should note this as a prerequisite.

## Verification Checklist

- [ ] `.gitignore` excludes `.env`, tokens, and credentials
- [ ] Config file checked for accidental secrets (`grep -n -i "api_key\|token" hermes/config.yaml`)
- [ ] Skills tree is complete and excludes deprecated buckets
- [ ] Systemd service files included in repo
- [ ] Setup script is executable and handles install+config+skills+services
- [ ] Initial commit pushed and verified on remote
- [ ] README describes requirements and quick-start steps

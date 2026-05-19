# SovereignAI Repo Sync Workflow

## Overview

The SovereignAI GitHub repo (`github.com/edwardsomewhat/SovereignAI`) is the canonical source
for this node's Hermes configuration. A cron-driven sync script at
`~/.hermes/scripts/sovereign-sync.sh` pushes changes back to the repo hourly.

## What Gets Synced

- `~/.hermes/config.yaml` → `hermes/config.yaml`
- `~/.hermes/SOUL.md` → `hermes/SOUL.md`
- `~/.hermes/skills/` (entire directory, via rsync --delete) → `hermes/skills/`
- Systemd service files → `systemd/`

## Sync Script Location

`~/.hermes/scripts/sovereign-sync.sh`

The script uses `rsync -a --delete` for skills and `diff -q` for config/persona.
It only commits and pushes when changes are detected.

## Bug Fixed: Untracked Files Not Detected

The original script only checked `git diff --quiet` on tracked files. New skills
added to `~/.hermes/skills/` were rsync'd to the repo directory but never
committed because `git diff` doesn't flag untracked files.

**Fix applied** (after the `rsync` block, before the commit block):

```bash
# Also detect new untracked files
if [ -z "$(git ls-files --others --exclude-standard)" ]; then
    : # no untracked
else
    changed=1
fi
```

## Multi-Node Sync Pattern

To sync another Hermes node from the repo:

```bash
# Clone with GitHub token
TOKEN=$(grep GITHUB_TOKEN ~/.hermes/.env | cut -d= -f2)
git clone "https://${TOKEN}@github.com/edwardsomewhat/SovereignAI.git" ~/repos/sovereign-ai

# Pull skills from repo into Hermes
rsync -a ~/repos/sovereign-ai/hermes/skills/ ~/.hermes/skills/

# Optional: also sync config and persona
cp ~/repos/sovereign-ai/hermes/config.yaml ~/.hermes/config.yaml
cp ~/repos/sovereign-ai/hermes/SOUL.md ~/.hermes/SOUL.md
```

**Important:** The GitHub token in `.env` must use the format
`https://TOKEN@github.com/...` for git clone. GitHub no longer supports
password-over-HTTPS auth; the token goes in the URL username position.

## Known Quirks

- The cron job runs from the user crontab (`crontab -l`), not a systemd timer.
- If the cron job stops, run `crontab -e` to re-add it.
- The sync is one-directional (conchai → repo). For bidirectional sync,
  each node needs its own sync script that pushes back.
- Config.yaml secrets are NOT synced — they live in `.env` which is in `.gitignore`.

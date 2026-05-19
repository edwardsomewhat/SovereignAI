# SovereignAI Repo Sync Pattern

The SovereignAI git repo (`github.com/edwardsomewhat/SovereignAI`) is the canonical source for Hermes config across all nodes. The sync script at `~/.hermes/scripts/sovereign-sync.sh` maintains this.

## How It Works

1. **Source → Repo**: rsyncs `~/.hermes/skills/`, `config.yaml`, `SOUL.md`, and systemd service files into the repo
2. **Detect changes**: compares files, checks for untracked files, tracks git diff
3. **Auto-commit**: `git add -A && git commit -m "auto-sync: YYYY-MM-DD HH:MM UTC"`
4. **Push**: to GitHub via SSH

## Target Node Sync

```bash
# Clone and sync
git clone git@github.com:edwardsomewhat/SovereignAI.git ~/repos/sovereign-ai
rsync -a ~/repos/sovereign-ai/hermes/skills/ ~/.hermes/skills/
```

## Files Tracked

| Source | Repo Path |
|--------|-----------|
| `~/.hermes/config.yaml` | `hermes/config.yaml` |
| `~/.hermes/SOUL.md` | `hermes/SOUL.md` |
| `~/.hermes/skills/` | `hermes/skills/` (rsync --delete) |
| systemd services | `systemd/` |

## Cron Schedule

Runs every hour via cron. On conchai, managed by the cronjob tool or crontab.

## Script Fix

The sync script originally only checked tracked file diffs, missing new/untracked files. Fixed by adding:

```bash
if [ -z "$(git ls-files --others --exclude-standard)" ]; then
    : # no untracked
else
    changed=1
fi
```

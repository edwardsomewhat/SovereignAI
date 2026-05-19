# Sovereign AI Multi-Node Sync

Pattern for keeping multiple Hermes nodes identical via a Git repository.

## Architecture

```
conchai (source) → git push → GitHub (SovereignAI repo) → git pull → sovereign (target)
```

## Sync Script (runs on source node)

```bash
#!/bin/bash
REPO_DIR="$HOME/repos/sovereign-ai"
HERMES_DIR="$HOME/.hermes"

cd "$REPO_DIR" || exit 1
git pull origin main --ff-only 2>/dev/null || true

changed=0

# Sync config
if ! diff -q "$HERMES_DIR/config.yaml" "hermes/config.yaml" 2>/dev/null; then
    cp "$HERMES_DIR/config.yaml" "hermes/config.yaml"
    changed=1
fi

# Sync SOUL.md
if [ -f "$HERMES_DIR/SOUL.md" ]; then
    if ! diff -q "$HERMES_DIR/SOUL.md" "hermes/SOUL.md" 2>/dev/null; then
        cp "$HERMES_DIR/SOUL.md" "hermes/SOUL.md"
        changed=1
    fi
fi

# Sync skills
rsync -a --delete --quiet "$HERMES_DIR/skills/" "hermes/skills/" 2>/dev/null
if ! git diff --quiet -- "hermes/skills/"; then
    changed=1
fi

# Detect untracked files (fixed — original script missed these)
if [ -z "$(git ls-files --others --exclude-standard)" ]; then
    : # no untracked
else
    changed=1
fi

if [ "$changed" -eq 1 ]; then
    git add -A
    git commit -m "auto-sync: $(date '+%Y-%m-%d %H:%M UTC')"
    git push origin main
fi
```

## Pitfalls

**Untracked file detection:** The original sync script only checked `git diff --quiet` which skips untracked files. New skills added to `~/.hermes/skills/` were rsynced to the repo dir but never committed because `changed` stayed 0. Fix: add `git ls-files --others --exclude-standard` check.

**GitHub PAT rejection:** Classic PATs (`ghp_*`) may be rejected for HTTPS git operations ("Password authentication is not supported"). Use SSH key auth instead:
```bash
ssh-keygen -t ed25519 -C "fated@<hostname>"
# Add pubkey to github.com/settings/keys
git clone git@github.com:edwardsomewhat/SovereignAI.git
```

**Target node pull:** On the target node, run after the source pushes:
```bash
cd ~/repos/sovereign-ai && git pull origin main
rsync -a ~/repos/sovereign-ai/hermes/skills/ ~/.hermes/skills/
```

## Cron (on source node)

```bash
# Run every hour
(crontab -l 2>/dev/null; echo "0 * * * * bash ~/.hermes/scripts/sovereign-sync.sh") | crontab -
```

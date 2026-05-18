#!/bin/bash
# Sync this Hermes node's config back to the SovereignAI repo
# Runs as a cron job to keep the repo up to date

REPO_DIR="$HOME/repos/sovereign-ai"
HERMES_DIR="$HOME/.hermes"

# Make sure repo exists
if [ ! -d "$REPO_DIR/.git" ]; then
    echo "Repo not found at $REPO_DIR.cloned"
    exit 1
fi

cd "$REPO_DIR" || exit 1

# Pull latest first to avoid rebase issues
git pull origin main --ff-only 2>/dev/null || true

changed=0

# Sync config (secrets are already empty in config.yaml)
if diff -q "$HERMES_DIR/config.yaml" "hermes/config.yaml" 2>/dev/null; then
    :
else
    cp "$HERMES_DIR/config.yaml" "hermes/config.yaml"
    changed=1
fi

# Sync SOUL.md
if [ -f "$HERMES_DIR/SOUL.md" ]; then
    if diff -q "$HERMES_DIR/SOUL.md" "hermes/SOUL.md" 2>/dev/null; then
        :
    else
        cp "$HERMES_DIR/SOUL.md" "hermes/SOUL.md"
        changed=1
    fi
fi

# Sync skills (rsync new/modified files)
rsync -a --delete --quiet "$HERMES_DIR/skills/" "hermes/skills/" 2>/dev/null
# Check if anything actually changed in skills
if ! git diff --quiet -- "hermes/skills/"; then
    changed=1
fi

# Pull systemd service files
if [ -f /etc/systemd/system/hermes-dashboard.service ]; then
    sudo cp /etc/systemd/system/hermes-dashboard.service systemd/hermes-dashboard.service 2>/dev/null
    if ! git diff --quiet -- "systemd/hermes-dashboard.service"; then
        changed=1
    fi
fi
if [ -f /etc/systemd/system/firecrawl.service ]; then
    sudo cp /etc/systemd/system/firecrawl.service systemd/firecrawl.service 2>/dev/null
    if ! git diff --quiet -- "systemd/firecrawl.service"; then
        changed=1
    fi
fi

if [ "$changed" -eq 1 ]; then
    git add -A
    git commit -m "auto-sync: $(date '+%Y-%m-%d %H:%M UTC')"
    git push origin main 2>&1
    echo "Synced and pushed."
else
    echo "No changes."
fi
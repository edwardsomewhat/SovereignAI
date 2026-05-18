#!/bin/bash
# This script sets up a Hermes Agent instance to match the SovereignAI node configuration.
# Run this on a fresh machine after cloning the repo.

set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== SovereignAI Node Setup ==="
echo ""

# 1. Install Hermes Agent
echo "[1/4] Installing Hermes Agent..."
if ! command -v hermes &>/dev/null; then
    pip install hermes-agent 2>/dev/null || {
        echo "Manual install needed: https://hermes-agent.nousresearch.com/docs"
        exit 1
    }
fi
echo "  ✓ hermes $(hermes --version 2>/dev/null | head -1)"

# 2. Apply configuration
echo "[2/4] Applying configuration..."
mkdir -p ~/.hermes
cp -r "$REPO_DIR/hermes/config.yaml" ~/.hermes/config.yaml
cp -r "$REPO_DIR/hermes/SOUL.md" ~/.hermes/SOUL.md 2>/dev/null || true
echo "  ✓ config applied"

# 3. Install skills
echo "[3/4] Installing skills..."
rm -rf ~/.hermes/skills
cp -r "$REPO_DIR/hermes/skills" ~/.hermes/skills
echo "  ✓ $(find ~/.hermes/skills -name 'SKILL.md' | wc -l) skills installed"

# 4. Set up systemd services
echo "[4/4] Setting up systemd services..."
if [ -d "$REPO_DIR/systemd" ]; then
    for svc in "$REPO_DIR/systemd/"*.service; do
        if [ -f "$svc" ]; then
            name=$(basename "$svc")
            sudo cp "$svc" "/etc/systemd/system/$name"
            sudo systemctl daemon-reload
            sudo systemctl enable "$name" 2>/dev/null || true
            echo "  ✓ $name installed"
        fi
    done
fi

echo ""
echo "=== Setup complete ==="
echo "Next steps:"
echo "  1. Configure secrets (edit ~/.hermes/.env)"
echo "  2. Set GITHUB_TOKEN in ~/.hermes/.env"
echo "  3. sudo systemctl start hermes-dashboard (if dashboard desired)"
echo "  4. hermes --help to verify"
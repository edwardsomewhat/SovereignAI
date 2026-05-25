#!/bin/bash
# deploy-llama.sh — push and configure llama.cpp on hq-ai
# Run from sovereign after Tailscale SSH re-auth

HQ="100.84.92.74"

echo "=== Deploying llama.cpp config to hq-ai ==="

# 1. Copy swap script
echo "1. Installing llama-swap..."
scp /home/fated/hermes-crew/scripts/llama-swap.sh $HQ:/home/fated/bin/llama-swap
ssh $HQ "chmod +x /home/fated/bin/llama-swap && mkdir -p /home/fated/bin"

# 2. Install systemd user service
echo "2. Installing systemd service..."
ssh $HQ "mkdir -p ~/.config/systemd/user"
scp /home/fated/hermes-crew/config/llama-server.service $HQ:/home/fated/.config/systemd/user/llama-server.service

# 3. Enable lingering (keep user services after logout)
echo "3. Enabling lingering..."
ssh $HQ "sudo loginctl enable-linger fated"

# 4. Reload and enable service
echo "4. Enabling service..."
ssh $HQ "systemctl --user daemon-reload && systemctl --user enable llama-server"

# 5. Stop current nohup server if running, start via systemd
echo "5. Starting via systemd..."
ssh $HQ "pkill -f 'llama-server.*8080' 2>/dev/null; sleep 2; systemctl --user start llama-server"

# 6. Verify
echo "6. Verifying..."
sleep 10
ssh $HQ "systemctl --user status llama-server --no-pager | head -10 && echo '' && curl -s http://localhost:8080/health"

echo ""
echo "=== Done ==="
echo "Commands on hq-ai:"
echo "  llama-swap coding       # Qwen3.5-9B-MTP (default)"
echo "  llama-swap supervisor   # Qwen3.6-27B-MTP"
echo "  llama-swap reasoning    # DeepSeek-R1-14B"
echo "  llama-swap creative     # Gemma4-E4B"
echo "  llama-swap status       # check what's running"
echo "  llama-swap stop         # stop server"
echo "  journalctl --user -u llama-server -f   # logs"

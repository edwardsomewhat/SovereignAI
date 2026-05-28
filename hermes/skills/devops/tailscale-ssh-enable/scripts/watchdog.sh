#!/bin/bash
# tailscale-watchdog.sh — monitor SSH to all nodes, alert on Telegram on state change
# Deploy: copy to ~/.hermes/scripts/, then cronjob create --no-agent --script tailscale-watchdog.sh
# Requires: Telegram bot token and chat_id (set inline)

BOT_TOKEN="YOUR_BOT_TOKEN"
CHAT_ID="YOUR_CHAT_ID"
STATE_FILE="$HOME/.hermes/tailscale_watchdog_state"

# Define your nodes: name → Tailscale IP
declare -A NODES=(
    [hq-ai]="100.84.92.74"
    [conchai]="100.69.153.16"
    [nano]="100.81.229.44"
)

alert() {
    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d "chat_id=${CHAT_ID}" -d "text=$1" > /dev/null 2>&1
}

mkdir -p "$(dirname "$STATE_FILE")"
touch "$STATE_FILE"

DOWN_LIST=""; UP_LIST=""; CHANGED=false

for name in "${!NODES[@]}"; do
    ip="${NODES[$name]}"
    if ssh -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=no "$ip" "echo ok" > /dev/null 2>&1; then
        UP_LIST+="$name ✅  "
        prev=$(grep "^$name " "$STATE_FILE" 2>/dev/null | awk '{print $2}' || echo "unknown")
        [ "$prev" = "DOWN" ] && CHANGED=true
        sed -i "/^$name /d" "$STATE_FILE"; echo "$name UP" >> "$STATE_FILE"
    else
        DOWN_LIST+="$name ❌  "
        prev=$(grep "^$name " "$STATE_FILE" 2>/dev/null | awk '{print $2}' || echo "unknown")
        [ "$prev" != "DOWN" ] && CHANGED=true
        sed -i "/^$name /d" "$STATE_FILE"; echo "$name DOWN" >> "$STATE_FILE"
    fi
done

if $CHANGED; then
    if [ -n "$DOWN_LIST" ]; then
        alert "⚠️ Nodes unreachable: $DOWN_LIST
Re-auth: https://login.tailscale.com/a"
    else
        alert "✅ All nodes back: $UP_LIST"
    fi
fi

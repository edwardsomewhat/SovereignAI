#!/bin/bash
# tailscale-watchdog.sh — monitor SSH to all SovereignAI nodes
# Run via cron every 15 min. Alerts @SovereignHQbot on Telegram if nodes go down.

BOT_TOKEN="8776705483:AAGEdy4IC-L8V-HONI5Ailr98eYd8VxkKDI"
CHAT_ID="6311989610"
STATE_FILE="/home/fated/.hermes/tailscale_watchdog_state"

# All SovereignAI nodes
declare -A NODES=(
    [hq-ai]="100.84.92.74"
    [conchai]="100.69.153.16"
    [nano]="100.81.229.44"
    [charlotte]="100.70.223.108"
    [omega]="100.84.226.78"
    [cs]="100.79.117.119"
    [csweb]="100.71.6.98"
)

alert() {
    local msg="$1"
    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d "chat_id=${CHAT_ID}" \
        -d "text=${msg}" > /dev/null 2>&1
}

mkdir -p "$(dirname "$STATE_FILE")"
touch "$STATE_FILE"

DOWN_LIST=""
UP_LIST=""
CHANGED=false

for name in "${!NODES[@]}"; do
    ip="${NODES[$name]}"
    if ssh -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=no "$ip" "echo ok" > /dev/null 2>&1; then
        UP_LIST+="$name ✅  "
        prev=$(grep "^$name " "$STATE_FILE" 2>/dev/null | awk '{print $2}' || echo "unknown")
        if [ "$prev" = "DOWN" ]; then
            CHANGED=true
        fi
    else
        DOWN_LIST+="$name ❌  "
        prev=$(grep "^$name " "$STATE_FILE" 2>/dev/null | awk '{print $2}' || echo "unknown")
        if [ "$prev" != "DOWN" ]; then
            CHANGED=true
        fi
    fi
done

# Update state
for name in "${!NODES[@]}"; do
    ip="${NODES[$name]}"
    if ssh -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=no "$ip" "echo ok" > /dev/null 2>&1; then
        sed -i "/^$name /d" "$STATE_FILE" 2>/dev/null
        echo "$name UP" >> "$STATE_FILE"
    else
        sed -i "/^$name /d" "$STATE_FILE" 2>/dev/null
        echo "$name DOWN" >> "$STATE_FILE"
    fi
done

# Alert only on state change
if $CHANGED; then
    if [ -n "$DOWN_LIST" ]; then
        alert "⚠️ Nodes unreachable: $DOWN_LIST
Re-auth at: https://login.tailscale.com/a"
    else
        alert "✅ All SovereignAI nodes back online: $UP_LIST"
    fi
fi

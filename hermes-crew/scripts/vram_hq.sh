#!/bin/bash
# hq-ai VRAM Manager — unload/load Ollama models for Editor sessions.
#
# Usage: bash vram_hq.sh [unload|load|status]
#
# The Editor (qwen3-vl:8b) needs ~10GB VRAM on hq-ai (P5000, 16GB total).
# This script manages the lifecycle: unload before non-Editor sessions,
# load when Editor is about to run.
#
# Add ~5-10s for model load on cold start.

HQ="fated@hq-ai"
MODEL="qwen3-vl:8b"

case "${1:-status}" in
    status)
        echo "=== hq-ai VRAM ==="
        ssh "$HQ" "nvidia-smi --query-gpu=memory.used,memory.total,memory.free --format=csv,noheader 2>/dev/null || echo 'nvidia-smi failed'"
        echo ""
        echo "=== Ollama loaded models ==="
        ssh "$HQ" "curl -s http://localhost:11434/api/ps | python3 -c \"
import sys, json
try:
    data = json.load(sys.stdin)
    models = data.get('models', [])
    for m in models:
        name = m.get('name','?')
        vram = m.get('size_vram',0)//1024//1024
        expires = m.get('expires_at','?')[:19]
        print(f'{name}: {vram}MB VRAM, expires {expires}')
    if not models:
        print('No models loaded')
except Exception as e:
    print(f'Parse error: {e}')
\"" 2>/dev/null
        ;;
    unload)
        echo "Unloading $MODEL from hq-ai..."
        ssh "$HQ" "curl -s http://localhost:11434/api/generate -d '{\"model\":\"$MODEL\",\"keep_alive\":0}' > /dev/null 2>&1"
        # Verify
        sleep 1
        REMAINING=$(ssh "$HQ" "curl -s http://localhost:11434/api/ps" 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(len(data.get('models', [])))
except:
    print('?')
")
        if [ "$REMAINING" = "0" ]; then
            echo "✓ Unloaded. VRAM freed."
        else
            echo "⚠ Model may still be loaded (timeout). Check status."
        fi
        ;;
    load)
        echo "Loading $MODEL on hq-ai (5-10s)..."
        ssh "$HQ" "curl -s http://localhost:11434/api/generate -d '{\"model\":\"$MODEL\",\"prompt\":\"Ready.\",\"stream\":false}' > /dev/null 2>&1"
        echo "✓ Model loaded and ready."
        ;;
    *)
        echo "Usage: bash vram_hq.sh [status|unload|load]"
        exit 1
        ;;
esac

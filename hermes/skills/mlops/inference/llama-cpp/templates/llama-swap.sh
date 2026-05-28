#!/bin/bash
# llama-swap — swap running llama-server to a different model
# Template: customize MODEL_DIR, LLAMA_DIR, and the case blocks below.
# Usage: llama-swap <role_name>

set -e

PORT=8080
LLAMA_DIR=/path/to/llama.cpp/build/bin
MODEL_DIR=/home/user/llama.cpp-models
LOG=/tmp/llama-server.log

SHARED_FLAGS="-ngl 99 -c 8192 -fa on -np 1 --host 0.0.0.0 --port $PORT"

kill_server() {
    local pid=$(pgrep -f "llama-server.*$PORT" 2>/dev/null || true)
    if [ -n "$pid" ]; then
        echo "Stopping llama-server (PID $pid)..."
        kill $pid 2>/dev/null || true
        sleep 3
        kill -9 $pid 2>/dev/null || true
        sleep 1
    fi
}

start_model() {
    local name="$1"; local model_path="$2"; local extra_flags="$3"
    echo "Starting $name on :$PORT..."
    nohup "$LLAMA_DIR/llama-server" -m "$model_path" $SHARED_FLAGS $extra_flags \
        > "$LOG" 2>&1 &
    local pid=$!
    echo -n "  Waiting for server..."
    for i in $(seq 1 60); do
        if curl -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
            echo " ready (PID $pid)"
            return 0
        fi
        sleep 2
        echo -n "."
    done
    echo " TIMEOUT"; return 1
}

case "${1:-}" in
    # --- Customize these blocks for your models ---
    coding)
        kill_server
        start_model "Qwen3.5-9B-MTP" \
            "$MODEL_DIR/model.gguf" \
            "--spec-type draft-mtp --spec-draft-n-max 6"
        ;;
    supervisor)
        kill_server
        start_model "Qwen3.6-27B-MTP" \
            "$MODEL_DIR/model.gguf" \
            "--spec-type draft-mtp --spec-draft-n-max 6"
        ;;
    stop)   kill_server; echo "Server stopped." ;;
    status) pgrep -f "llama-server.*$PORT" >/dev/null && echo "Running" || echo "Stopped" ;;
    *)
        echo "Usage: llama-swap {coding|supervisor|stop|status}"
        exit 1 ;;
esac

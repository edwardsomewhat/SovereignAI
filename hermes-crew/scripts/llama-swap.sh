#!/bin/bash
# llama-swap — swap the running llama-server to a different model
# Usage: llama-swap <model_name>
#   coding      → Qwen3.5-9B-MTP     (6GB, fast, MTP)
#   supervisor  → Qwen3.6-27B-MTP    (15GB, smart, MTP)
#   reasoning   → DeepSeek-R1-14B    (8GB, CoT, no MTP)
#   creative    → Gemma4-E4B         (5GB, multimodal)
#   stop        → kill server

set -e

PORT=8080
LLAMA_DIR=/tmp/llama-b9247
MODEL_DIR=/home/fated/llama.cpp-models
LOG=/tmp/llama-server.log
CACHE_DIR=/home/fated/llama.cpp-models

# Shared flags for all models
SHARED_FLAGS="-ngl 99 -c 8192 -fa on -np 1 --host 0.0.0.0 --port $PORT"

kill_server() {
    local pid=$(pgrep -f "llama-server.*$PORT" 2>/dev/null || true)
    if [ -n "$pid" ]; then
        echo "Stopping llama-server (PID $pid)..."
        kill $pid 2>/dev/null || true
        sleep 3
        # Force kill if still running
        kill -9 $pid 2>/dev/null || true
        sleep 1
    fi
}

start_model() {
    local name="$1"
    local model_path="$2"
    local extra_flags="$3"
    
    echo "Starting $name on :$PORT..."
    echo "  Model: $model_path"
    echo "  Flags: $extra_flags"
    
    nohup "$LLAMA_DIR/llama-server" \
        -m "$model_path" \
        $SHARED_FLAGS \
        $extra_flags \
        > "$LOG" 2>&1 &
    
    local pid=$!
    echo "  PID: $pid"
    
    # Wait for server to be ready
    echo -n "  Waiting for server..."
    for i in $(seq 1 60); do
        if curl -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
            echo " ready"
            return 0
        fi
        sleep 2
        echo -n "."
    done
    echo " TIMEOUT"
    return 1
}

case "${1:-}" in
    coding|qwen35)
        kill_server
        export LLAMA_CACHE="$CACHE_DIR"
        start_model "Qwen3.5-9B-MTP (coding)" \
            "" \
            "-hf unsloth/Qwen3.5-9B-MTP-GGUF:UD-Q4_K_XL --spec-type draft-mtp --spec-draft-n-max 6"
        ;;
    supervisor|qwen36)
        kill_server
        export LLAMA_CACHE="$CACHE_DIR"
        start_model "Qwen3.6-27B-MTP (supervisor)" \
            "$MODEL_DIR/Qwen3.6-27B-IQ4_XS.gguf" \
            "--spec-type draft-mtp --spec-draft-n-max 6"
        ;;
    reasoning|deepseek|r1)
        kill_server
        start_model "DeepSeek-R1-14B (reasoning)" \
            "$MODEL_DIR/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf" \
            ""
        ;;
    creative|gemma)
        kill_server
        start_model "Gemma4-E4B (creative)" \
            "$MODEL_DIR/gemma-4-E4B-it-Q4_K_M.gguf" \
            ""
        ;;
    stop)
        kill_server
        echo "Server stopped."
        ;;
    status)
        if pgrep -f "llama-server.*$PORT" > /dev/null 2>&1; then
            echo "llama-server running on :$PORT"
            ps aux | grep "[l]lama-server" | head -1
            curl -s "http://localhost:$PORT/health" 2>/dev/null && echo "Health: OK"
        else
            echo "llama-server NOT running"
        fi
        ;;
    *)
        echo "Usage: llama-swap {coding|supervisor|reasoning|creative|stop|status}"
        echo ""
        echo "Models:"
        echo "  coding       Qwen3.5-9B-MTP   6GB  MTP  fast general/coding"
        echo "  supervisor   Qwen3.6-27B-MTP  15GB  MTP  smart orchestration"
        echo "  reasoning    DeepSeek-R1-14B   8GB  CoT  deep reasoning"
        echo "  creative     Gemma4-E4B        5GB  vis  multimodal text+image"
        exit 1
        ;;
esac

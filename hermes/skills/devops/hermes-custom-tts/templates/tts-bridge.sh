#!/bin/bash
# Hermes TTS bridge: local → remote GPU TTS
# Usage: bridge.sh --text-file /tmp/text.txt --out /tmp/out.wav [--voice-ref /path/to/voice.wav]
# Hermes fills {input_path} and {output_path} automatically.
#
# REQUIRES: SSH key auth to GPU_NODE (no password prompt).

GPU_NODE="gpu-node"                    # CHANGE THIS to your GPU hostname/IP
TTS_VENV="~/qwen-tts-venv/bin/python"  # Python venv with qwen-tts installed
TTS_WRAPPER="~/qwen-tts-wrapper.py"    # Wrapper script on GPU node

INPUT=""
OUTPUT=""
VOICE_ARGS=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --text-file) INPUT="$2"; shift 2 ;;
        --out) OUTPUT="$2"; shift 2 ;;
        --voice-ref) VOICE_ARGS="--voice-ref $2"; shift 2 ;;
        *) shift ;;
    esac
done

if [[ -z "$INPUT" || -z "$OUTPUT" ]]; then
    echo "Usage: $0 --text-file <path> --out <path> [--voice-ref <path>]" >&2
    exit 1
fi

scp -q "$INPUT" "$GPU_NODE:/tmp/qwen-tts-input.txt" && \
ssh "$GPU_NODE" "$TTS_VENV $TTS_WRAPPER $VOICE_ARGS --text-file /tmp/qwen-tts-input.txt --out /tmp/qwen-tts-output.wav" && \
scp -q "$GPU_NODE:/tmp/qwen-tts-output.wav" "$OUTPUT" && \
echo "[qwen-bridge] Done: $OUTPUT ($(du -h "$OUTPUT" | cut -f1))" >&2

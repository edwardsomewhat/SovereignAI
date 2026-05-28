# Ollama CPU Thrashing Diagnosis

When an Ollama model is loaded but using massive CPU instead of GPU, or when
the training pipeline suddenly takes 60+ seconds per request, follow this
workflow to identify and fix the root cause.

## Quick Triage

```bash
# 1. Check models loaded and their processor split
ollama ps
# Look for: PROCESSOR column showing "50%/50% CPU/GPU" — that's the problem

# 2. Check GPU utilization vs VRAM
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv
# 0% util + high VRAM = model loaded but inference on CPU

# 3. Check CPU load
uptime
# 12+ load on a P5000 system = CPU inference, not GPU

# 4. Check who's hitting Ollama
journalctl -u ollama --since "5 min ago" | grep POST
# Look for repeated /api/generate from specific IPs
```

## Root Cause: 128K Context + Limited VRAM

The most common cause on hq-ai (P5000 16GB): `OLLAMA_CONTEXT_LENGTH=131072`
creates an ~8-10GB KV cache. Combined with ~4.7GB model weights (Q4_0 GGUF),
this exceeds 16GB VRAM. Ollama splits layers 50/50 between CPU and GPU —
resulting in 1248% CPU usage and near-zero GPU utilization.

Each `/api/generate` call takes 35-70 seconds instead of seconds.

## Fix: Per-Request Context Cap

Do NOT change the global `OLLAMA_CONTEXT_LENGTH` — other workloads may need 128K.
Instead, pass `num_ctx` per-request:

```python
"options": {
    "temperature": 0.3,
    "num_predict": 1024,
    "num_ctx": 32768,  # 32K is enough for summarization, 1/4 the KV cache
}
```

Ollama's `/api/generate` endpoint respects per-request `num_ctx` — it overrides
the server default for that call only. At 32K, the KV cache shrinks to ~2GB,
fitting all layers in GPU VRAM.

## Finding the Culprit Process

```bash
# On the node calling Ollama (e.g., sovereign):
ss -tnp | grep ':11434'              # find the connection PID
ps -p <PID> -o pid,ppid,cmd           # identify the process
tail ~/.hermes/training_data/pipeline.log  # check for errors or loops
```

## When to Kill vs Wait

If the pipeline is actively making progress (log shows new session IDs being
processed), let it finish — even at 60s/request, it'll complete. If the log
hasn't changed in 5+ minutes and Ollama is still being hit, the pipeline is
in a re-processing loop — kill it with `kill <PID>`.

## Restarting After Fix

After applying the `num_ctx` fix:
```bash
python /home/fated/training_pipeline.py all
```
Requests should now complete in 2-5 seconds each instead of 35-70 seconds.
Confirm with `ollama ps` — PROCESSOR should show "100% GPU".

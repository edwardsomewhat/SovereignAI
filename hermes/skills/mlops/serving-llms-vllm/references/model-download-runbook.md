# Model Download Runbook

## Quick command

```bash
HF_HUB_ENABLE_HF_TRANSFER=1 /home/fated/vLLMing/venv/bin/hf download <model-id> \
  --cache-dir /home/fated/vLLMing/qwen-stack/models/hub
```

## Gotchas (all hit in practice)

### 1. Deprecated CLI
`huggingface-cli download` is dead — exits immediately with warning. Use `hf download` (same package, different entry point).

### 2. Full venv path required in background shells
```bash
# WRONG — background subshell may not have venv on PATH:
hf download ...

# RIGHT:
/home/fated/vLLMing/venv/bin/hf download ...
```

### 3. Root-owned cache from Docker
Docker containers create model cache files as `root`. Before any `hf download`:
```bash
sudo chown -R $USER:$USER /home/fated/vLLMing/qwen-stack/models/hub
```

### 4. HF_TOKEN for rate limits
Without `HF_TOKEN`, downloads hit unauthenticated rate limits (~1-2 concurrent connections). With token, much faster. Token is in the user's `.env` — source it before downloading.

### 5. Check actual blob sizes, not estimates
Model card "8 GB AWQ" may be 17 GB in reality (30B params × 0.5 bytes = 15 GB, plus overhead and safetensor alignment). Always check `du -sh` on the blobs directory after download to get real VRAM requirements.

### 6. Duplicate weight formats inflate HF cache
GPT-OSS downloads 39 GB total but vLLM only uses 13 GB. The `original/` and `metal/` subdirectories contain full-format copies (BF16 single-file for original, Apple Metal format). These are symlinked in blobs but counted in `du -sh` of the model directory.

## Download time estimates
- ~8 GB model: ~5-8 minutes (with HF_TRANSFER, authenticated)
- ~16 GB model: ~15-20 minutes
- Always background with `notify_on_complete=true`

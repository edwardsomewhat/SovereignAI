# Model Swap Pattern for Single-GPU Nodes

When a GPU can only run one model at a time, use a swap script instead of
running multiple llama-server instances. This avoids VRAM contention and
provides a clean model-switching interface.

## Pattern

```bash
llama-swap coding       # Qwen3.5-9B-MTP (fast, general purpose)
llama-swap supervisor   # Qwen3.6-27B-MTP (smart, orchestration)
llama-swap reasoning    # DeepSeek-R1-14B (chain-of-thought reasoning)
llama-swap creative     # Gemma4-E4B (multimodal text+vision)
llama-swap status       # check what's running
llama-swap stop         # kill server
```

## Implementation

The script:
1. Kills the current llama-server on the target port
2. Starts a new llama-server with the selected model
3. Applies MTP flags (`--spec-type draft-mtp --spec-draft-n-max 6`) only for MTP-capable models
4. Waits for health check to confirm server is ready

## Key Constraints

- Only one model on the GPU at a time (user preference: don't run two simultaneously)
- MTP flags are model-specific — Qwen gets `draft-mtp`, DeepSeek and Gemma don't
- Models with mmproj (vision) can't use MTP simultaneously (llama.cpp limitation)
- MoE models like 35B-A3B have large GGUF files (all expert weights stored) despite low active params

## SovereignAI Deployment

Located at `/home/fated/hermes-crew/scripts/llama-swap.sh`.
Deployed to hq-ai at `~/bin/llama-swap`.

## Model Inventory (hq-ai, P5000 16GB)

| Alias      | Model                        | Size  | MTP | Role         |
|------------|------------------------------|-------|-----|--------------|
| coding     | Qwen3.5-9B-MTP UD-Q4_XL      | 6GB   | Yes | Fast general |
| supervisor | Qwen3.6-27B-MTP IQ4_XS       | 15GB  | Yes | Smart agent  |
| reasoning  | DeepSeek-R1-Distill-Qwen-14B | 8GB   | No  | Deep CoT     |
| creative   | Gemma4-E4B Q4_K_M            | 5GB   | No  | Multimodal   |

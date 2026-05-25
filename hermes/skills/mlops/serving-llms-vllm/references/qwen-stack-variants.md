# Qwen-Stack Compose Variant Matrix

Measured on 1× RTX 3090 24 GB with `vllm/vllm-openai:nightly-07351e088` + Genesis v7.54. Bench prompts: 1000-token narrative essay + 800-token quicksort code.

## Available Compose Files

All in `compose/`, all expose port 8020 (container 8000). Only ONE can run at a time on the same port.

| File | Model | Context | Narr TPS | Code TPS | Vision | Tools | KV type | MTP | Genesis | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| docker-compose.yml | Lorbus 27B AutoRound | 96K | 51 | 68 | no* | yes | TQ 3-bit | n=3 | v7.14 | *currently `--language-model-only` |
| docker-compose.fast-chat.yml | Lorbus 27B | 20K | 55 | 70 | yes | yes | fp8 | n=3 | v7.14 | Fastest TPS, chat-only |
| docker-compose.tools-text.yml | Lorbus 27B | 75K | 53 | 70 | no | yes | fp8 | n=3 | v7.14 | Long prompts, no vision |
| docker-compose.no-genesis-mtp.yml | Lorbus 27B | 20K | 55 | 68 | yes | yes | fp8 | n=3 | none | Diagnostic: isolate Genesis perf impact |
| docker-compose.minimal.yml | Lorbus 27B | 32K | 32 | 33 | yes | yes | fp8 | no | none | Simplest stack, no spec-decode |
| docker-compose.qwen36.yml | Lorbus 27B AutoRound | 128K | — | — | no | yes | TQ 3-bit | no | v7.14 | Text-only, enforce-eager |
| docker-compose.qwen36-awq.yml | hampsonw AWQ-BF16 | 128K | — | — | no | yes | TQ 3-bit | no | v7.14 | AWQ variant (stub) |
| docker-compose.qwen35.yml | Huihui abliterated | 128K | — | — | no | yes | TQ 3-bit | no | v7.14 | Qwen3.5 abliterated (stub) |
| docker-compose.hlwq.yml | Claude-Opus HLWQ Q5 | 128K | — | — | no | yes | TQ 3-bit | no | v7.14 | Claude Opus finetune |
| docker-compose.orchestrator.yml | Qwen3-14B-AWQ | 65K | — | — | no | yes | TQ 4-bit | no | none | Fast agentic tool-calling |

## Production Default (docker-compose.yml) Opt-In Tiers

All tiers use same model/engine, just bump `--max-model-len` and `--gpu-memory-utilization`.

| Context | mem_util | Safe single-prompt | Safe tool-prefill | Notes |
|---|---|---|---|---|
| **48K + 0.92** ⭐⭐ | 0.92 | up to 48K | up to 48K | All 10 verify-full.sh checks pass |
| 64K + 0.92 | 0.92 | up to ~50K | up to 40K | Common agent flows |
| 96K + 0.93 | 0.93 | up to ~50K | up to 30K | Long history, small prompts |
| 128K + 0.95 | 0.95 | up to ~50K | up to 40K | GPT-4 tier on paper |
| 192K + 0.98 | 0.98 | up to ~16K | up to 16K | Long-ctx recall only |
| 205K + 0.98 text-only | 0.98 | up to ~16K | up to 16K | Engine ceiling, vision off |

## Two Prefill-Activation Cliffs

### Cliff 1 — TurboQuant attention scratch + tool-response prefill
- **Trigger**: ≥25K total prompt with TQ3 KV at high mem_util
- **Site**: `turboquant_attn` forward — dequant scratch + mid_o/output buffers
- **Symptom**: CUDA OOM allocating ~138 MiB; engine dies mid-request
- **Why**: Tool response of 20K+ tokens stuffed back into conversation

### Cliff 2 — DeltaNet/GLA recurrent state buffer
- **Trigger**: Single prompt above ~50-60K tokens (regardless of tool use)
- **Site**: `fla.ops.chunk.chunk_gated_delta_rule_fwd_h.h.new_empty(B, NT, H, V, K)`
- **Symptom**: CUDA OOM allocating ~50-740 MiB during forward
- **Why**: Qwen3-Next is hybrid (16 attention + 48 GDN layers). GDN state sized by total seq_len — chunked-prefill doesn't help.

## Model Storage

Models are stored under `models/hub/` using HF cache format (`models--org--name/`). Docker mounts `models/` as `/root/.cache/huggingface`. Some models are also symlinked (e.g., `models/qwen3.6-27b-autoround-int4/` → full weights).

### Installed models (as of May 2026)

| Model ID | Size | Format | Status |
|---|---|---|---|
| Lorbus/Qwen3.6-27B-int4-AutoRound | 18 GB | AutoRound 4-bit | Primary, full weights |
| caiovicentino1/Qwen3.5-27B-Claude-Opus-HLWQ-Q5 | 17 GB | HLWQ Q5 | Full weights |
| Qwen/Qwen3-14B-AWQ | 9.4 GB | AWQ 4-bit | Orchestrator, full weights |
| drawais/Qwen3.6-27B-AWQ-INT4 | 20 MB | — | Metadata only, weights incomplete |

### Root-owned blobs

HF hub blobs downloaded inside Docker can be root-owned. Cleanup requires `sudo rm -rf`.

## HF Hub Token

Required for gated models. Set via `HF_TOKEN` env var (passed as `HUGGING_FACE_HUB_TOKEN` in container). Compose files reference `${HF_TOKEN:-}` — defaults to empty if unset.

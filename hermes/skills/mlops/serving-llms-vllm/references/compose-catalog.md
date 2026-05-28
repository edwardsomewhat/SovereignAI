# vLLM Compose File Catalog

All compose files in `qwen-stack/compose/`. All use pinned image `vllm/vllm-openai:nightly-07351e0883470724dd5a7e9730ed10e01fc99d08`.

## Active models

| # | Model | Compose File | HF ID | Format | VRAM | Ctx | Tool Parser | Speed | Known Issues |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Qwen3.6-27B | `docker-compose.yml` | Lorbus/Qwen3.6-27B-int4-AutoRound | AutoRound int4 | ~18G | 96K | qwen3_coder | ~51/68 t/s | Genesis patches required; TQ cliff at 50-60K |
| 2 | Qwen3-14B-AWQ | `docker-compose.orchestrator.yml` | Qwen/Qwen3-14B-AWQ | AWQ int4 | ~9G | 65K | qwen3_coder | — | Smaller model, good for orchestrator role |
| 3 | Nemotron-3 Nano | `docker-compose.nemotron-nano-awq.yml` | stelterlab/NVIDIA-Nemotron-3-Nano-30B-A3B-AWQ | AWQ int4 | **~17G** | 65K | hermes | ~52 t/s | KV cache: only 5.1 GB available; 128K won't fit. Hermes parser quirk — raw XML works for Hermes Agent. |
| 4 | GPT-OSS 20B | `docker-compose.gpt-oss-20b.yml` | openai/gpt-oss-20b | MXFP4 | ~13G | 128K | *none (Harmony)* | ~80 t/s | Tool calling limited; reasoning works great. Harmony separates `reasoning` and `content` automatically. |

## Qwen variants (same Lorbus AutoRound model)

| File | Context | Vision | Tools | KV | MTP | TPS |
|---|---|---|---|---|---|---|
| `docker-compose.yml` (default) | 96K | off | yes | TQ 3-bit | n=3 | ~51/68 |
| `docker-compose.fast-chat.yml` | 20K | yes | yes | fp8 | n=3 | ~55/70 |
| `docker-compose.tools-text.yml` | 75K | no | yes | fp8 | n=3 | ~53/70 |
| `docker-compose.minimal.yml` | 32K | yes | yes | fp8 | no | ~32/33 |
| `docker-compose.no-genesis-mtp.yml` | 20K | yes | yes | fp8 | n=3 | ~55/68 |

## Model download sizes (real, measured)

| Model | Expected | Actual Blobs | Notes |
|---|---|---|---|
| Nemotron-3 Nano AWQ | ~8 GB | **16.8 GB** (3×4.7 + 2.7) | AWQ of 30B params ≈ 15 GB; plus tokenizer/overhead |
| GPT-OSS 20B MXFP4 | ~16 GB | **12.9 GB shards** (4.5+4.5+3.9) + 26 GB dupes | `original/` and `metal/` dirs duplicate weights; vLLM only uses sharded MXFP4 |

## Ops

All models share port **8020** → only one runs at a time. Swap:
```bash
cd /home/fated/vLLMing/qwen-stack/compose
docker compose -f docker-compose.yml down
docker compose -f docker-compose.nemotron-nano-awq.yml up -d
```

Model cache: `qwen-stack/models/hub/` — mounted into containers at `/root/.cache/huggingface`.

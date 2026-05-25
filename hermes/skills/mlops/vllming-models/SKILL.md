---
name: vllming-models
description: Manage the local vLLM model stack on the 3090 — compose files, tool parsers, quirks, and boot procedures.
---

# vLLMing — Local Model Stack (Single RTX 3090 24GB)

Path: `/home/fated/vLLMing/qwen-stack/`
Compose dir: `compose/`
Patches dir: `patches/`
Model cache: `models/hub/` (mounted into Docker at `/root/.cache/huggingface`)
Cache size: ~99 GB total

## Active Models (all on port 8020, one at a time)

| Model | Compose File | HF ID | Format | VRAM | Context | Speed | Tools |
|---|---|---|---|---|---|---|---|
| Qwen3.6-27B | `docker-compose.yml` | Lorbus/Qwen3.6-27B-int4-AutoRound | AutoRound int4 | 18 GB | 96K | 51/68 t/s | ✅ qwen3_coder |
| Qwen3-14B-AWQ | `docker-compose.orchestrator.yml` | Qwen/Qwen3-14B-AWQ | AWQ int4 | 9.4 GB | 65K | — | ✅ qwen3_coder |
| Nemotron-3 Nano | `docker-compose.nemotron-nano-awq.yml` | stelterlab/NVIDIA-Nemotron-3-Nano-30B-A3B-AWQ | AWQ int4 | 17 GB | 65K | ~52 t/s | ✅ nemotron_xml plugin |
| GPT-OSS 20B | `docker-compose.gpt-oss-20b.yml` | openai/gpt-oss-20b | MXFP4 | 13 GB | 128K | ~80 t/s | ⚠️ prompt-level only |

## Boot / Swap Procedure

```bash
cd /home/fated/vLLMing/qwen-stack/compose
docker compose -f <current>.yml down
docker compose -f <target>.yml up -d
# Wait ~90s for model load, then test:
curl -s http://localhost:8020/health
```

## Tool Parser Plugins (critical — do not lose these)

### Nemotron XML parser: `patches/nemotron_xml_tool_parser.py`
- Registered as `nemotron_xml` via `ToolParserManager.register_module`
- Handles `<tool_call><function=name><parameter=key>val</parameter></function></tool_call>` XML format
- Must be mounted into Docker: `../patches/nemotron_xml_tool_parser.py:/patches/nemotron_xml_tool_parser.py:ro`
- Flags: `--tool-call-parser nemotron_xml --tool-parser-plugin /patches/nemotron_xml_tool_parser.py`
- Method signatures include `token_ids: Sequence[int] | None = None` (vLLM v0.19+ requirement)

### Harmony noop parser: `patches/harmony_noop_tool_parser.py`
- Registered as `harmony_noop` via `ToolParserManager.register_module`
- Satisfies `--tool-call-parser` validation without interfering with harmony_utils.py
- Flags: `--tool-call-parser harmony_noop --tool-parser-plugin /patches/harmony_noop_tool_parser.py`
- GPT-OSS tools need prompt-level Harmony injection (TypeScript declarations), not vLLM tool pipeline

## Known Quirks

1. **Nemotron + hermes parser**: vLLM's built-in hermes parser expects JSON between `<tool_call>` tags. Nemotron outputs XML (`<function=name><parameter=key>val</parameter>`). Our custom `nemotron_xml` parser fixes this.

2. **fp8_e5m2 KV cache**: Incompatible with compressed-tensors/AWQ models. Use `--kv-cache-dtype auto` instead.

3. **`--enable-auto-tool-choice` requires `--tool-call-parser`**: vLLM validates this. Always pair them.

4. **GPT-OSS Harmony tools**: Harmony uses TypeScript function declarations in the developer message. vLLM's tool pipeline doesn't route correctly. For tool use, prefer Nemotron. For reasoning, GPT-OSS excels (80 tok/s, clean reasoning/content separation).

5. **hf download**: `huggingface-cli` is deprecated. Use `hf download`. Docker creates root-owned files in cache — run `sudo chown -R fated:fated models/hub/` after Docker downloads.

6. **Docker image**: Pinned to `vllm/vllm-openai:nightly-07351e0883470724dd5a7e9730ed10e01fc99d08` (v0.19.2rc1.dev205+g07351e088). Do not bump without testing — tool parser APIs change.

## Downloading New Models

```bash
cd /home/fated/vLLMing
export HF_HUB_ENABLE_HF_TRANSFER=1
/home/fated/vLLMing/venv/bin/hf download <hf-model-id> --cache-dir qwen-stack/models/hub
```

## Nemotron Omni (pending)

- Model: `nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-NVFP4` (Ollama `nemotron3:33b`)
- Format: NVFP4 (`modelopt_fp4` quantization)
- Registered in vLLM model registry: `NemotronH_Nano_Omni_Reasoning_V3` → `nano_nemotron_vl.py`
- Not yet downloaded or tested. Risks: NVFP4 compute-capability, multimodal tower init, unknown VRAM footprint.
- Use `--language-model-only` for text-only agent use.

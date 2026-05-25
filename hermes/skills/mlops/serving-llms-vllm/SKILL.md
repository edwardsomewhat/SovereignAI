---
name: serving-llms-vllm
description: vLLM inference serving — Docker Compose stacks, MoE CPU offloading on consumer GPUs, Genesis patches, model quantization selection, compose variant matrices.
---

# vLLM Inference Serving

vLLM-based model serving with Docker Compose. Covers single-GPU setups (RTX 3090-class), quantized MoE models with CPU offloading, and the Genesis patch ecosystem.

## Quick reference

- **Default port**: 8000 (container) → 8020 (host), or custom per-model
- **Pinned image**: `vllm/vllm-openai:nightly-07351e0883470724dd5a7e9730ed10e01fc99d08` (dev205+g07351e088, Genesis v7.14 verified)
- **Docker GPU**: NVIDIA Container Toolkit required (`--gpus all`)
- **Shared memory**: `shm_size: "16gb"` for large models

## Trigger conditions

Load this skill when:
- Configuring a vLLM Docker Compose stack
- Adding a new model to an existing vLLM setup
- Running MoE models on limited VRAM (RTX 3090 / 24 GB class)
- Integrating Genesis patches for Qwen model families
- Choosing between quantization formats for vLLM (AutoRound vs AWQ vs fp8 vs TurboQuant KV)

## vLLM CPU Offloading for MoE Models

MoE models (GPT-OSS, Nemotron-3, Mixtral) have large total parameter counts but small active subsets per token. This makes them ideal for CPU offloading — expert MLP weights sit in system RAM and only active experts are pulled into VRAM.

### Key flags

```
--cpu-offload-gb <N>         # GB of weights to offload to CPU RAM
--enforce-eager              # REQUIRED with CPU offload (no CUDA graphs)
```

### How to calculate offload size

For a 30B MoE with 3B active:
- Shared weights (attention, embeddings, router): ~3B ≈ 6 GB FP16 — keep on GPU
- Expert MLP banks: ~27B ≈ 54 GB FP16 — offload to CPU
- Quantized (AWQ INT4): ~27B ≈ 13.5 GB — offload to CPU
- Set `--cpu-offload-gb` to the GB you want offloaded (e.g., `--cpu-offload-gb 14` for INT4 experts)

### vLLM behavior

vLLM's CPU offloading operates at weight-load time. The engine loads offloaded weights into pinned CPU memory and pages them in on demand. MoE router decisions trigger expert weight fetches. First-token latency increases (CPU→GPU transfer) but decode throughput is largely unaffected since expert weights are reused across tokens.

### Pitfalls

- CPU offload does NOT work with CUDA graphs — always pair with `--enforce-eager`
- System RAM must be large enough for offloaded weights + KV cache overhead
- Not all quantization formats work with CPU offload — AWQ and GPTQ are tested; AutoRound and compressed-tensors may work but verify
- First inference after boot is slow as weights page in; subsequent requests are faster

## Genesis Patches (Sandermage) for Qwen Models

Genesis v7.14+ patches fix critical upstream vLLM bugs for Qwen3.5/3.6 models. The patch package mounts as a Python module into vLLM's site-packages.

### Mount pattern (Docker Compose)

```yaml
volumes:
  - ../patches/genesis/vllm/_genesis:/usr/local/lib/python3.12/dist-packages/vllm/_genesis:ro
  - ../patches/patch_tolist_cudagraph.py:/patches/patch_tolist_cudagraph.py:ro
```

### Entrypoint pattern

```yaml
entrypoint:
  - /bin/bash
  - -c
  - |
    set -e
    pip install xxhash pandas scipy -q
    python3 -m vllm._genesis.patches.apply_all
    python3 /patches/patch_tolist_cudagraph.py
    exec vllm serve "$@"
  - --
```

### Critical env vars (Genesis v7.14 opt-in)

```yaml
- GENESIS_ENABLE_P65_TURBOQUANT_SPEC_CG_DOWNGRADE=1   # fixes silent tool-call cascade under MTP × TQ × cudagraph
- GENESIS_ENABLE_P66_CUDAGRAPH_SIZE_FILTER=1           # capture-size divisibility
- GENESIS_ENABLE_P64_QWEN3CODER_MTP_STREAMING=1        # streaming tool-call edge case
- GENESIS_ENABLE_P68_AUTO_FORCE_TOOL=1                 # long-ctx tool adherence
- GENESIS_ENABLE_P69_LONG_CTX_TOOL_REMINDER=1          # long-ctx tool reminder
```

### When NOT to use Genesis P65/P66

Skip P65 and P66 when using `fp8_e5m2` KV cache (not TurboQuant) — the cudagraph bug they fix is TurboQuant-specific. P64/P68/P69 are safe on all paths.

### Upstream bugs Genesis fixes

- vllm#40807 — CUDA graph crash
- vllm#40831 — TurboQuant × spec-decode corruption
- vllm#40880 — MTP × TurboQuant cudagraph silent tool-call cascade

## Quantization Selection for vLLM

| Quant | vLLM flag | VRAM (27B) | Notes |
|---|---|---|---|
| AutoRound INT4 | `--quantization auto_round` | ~18 GB | Good balance, works with TQ KV |
| AWQ INT4 | auto-detected | ~16 GB | Faster prefill on CUDA, good for MoE |
| FP8 KV | `--kv-cache-dtype fp8_e5m2` | varies | Sidesteps cudagraph bugs, smaller KV pool |
| TurboQuant 3-bit KV | `--kv-cache-dtype turboquant_3bit_nc` | smaller KV | Max context on 24 GB, but triggers #40880 with MTP |

## Common vLLM env vars

```yaml
- VLLM_WORKER_MULTIPROC_METHOD=spawn
- NCCL_CUMEM_ENABLE=0
- NCCL_P2P_DISABLE=1                    # single-GPU
- VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS=1
- PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True,max_split_size_mb:512
- VLLM_USE_FLASHINFER_SAMPLER=1
- OMP_NUM_THREADS=1
- VLLM_ALLOW_LONG_MAX_MODEL_LEN=1
```

## Model-Specific Notes

### Qwen3.6-27B (Lorbus AutoRound)

Primary single-3090 model. 48K-96K context with TQ3 KV. Two known activation cliffs:
- **Cliff 1**: TurboQuant attention scratch + tool prefill ≥25K at high mem_util
- **Cliff 2**: DeltaNet/GLA recurrent state buffer at single prompt ≥50-60K tokens

Production safe: 48K + 0.92 mem_util. Full variant matrix, cliff details, model storage layout, and compose file catalog in `references/qwen-stack-variants.md`.

### GPT-OSS 20B (OpenAI)

21B total / 3.6B active MoE (24 experts). Native MXFP4 (~16 GB VRAM). 128K native context. Apache 2.0. Tagged `vllm` on HF, 8M+ downloads.

**Harmony format is handled natively by vLLM** — no adapter needed. vLLM's `harmony_utils.py` (imports `openai-harmony` Rust library) translates between standard OpenAI API format and Harmony's TypeScript-style tool definitions internally. Standard OpenAI clients work. Tool calling, reasoning (CoT channels), and structured output are all native.

Compose pattern: `--dtype auto`, no `--quantization` flag (MXFP4 auto-detected), no `--tool-call-parser` (harmony handles it). Use `--trust-remote-code` (custom `GptOssForCausalLM` architecture). `--enforce-eager` recommended for MoE.

```yaml
command:
  - --model
  - openai/gpt-oss-20b
  - --served-model-name
  - gpt-oss-20b
  - --dtype
  - auto
  - --max-model-len
  - "131072"
  - --trust-remote-code
  - --enforce-eager
  - --enable-auto-tool-choice
  # No --tool-call-parser, no --reasoning-parser — harmony handles both
```

### Nemotron-3 Nano 30B-A3B

30B total / 3B active MoE (NemotronH architecture, `nemotron_h` in vLLM registry). AWQ INT4 quant at `stelterlab/NVIDIA-Nemotron-3-Nano-30B-A3B-AWQ` (~8 GB VRAM). 128K native context. NVIDIA Open Model License.

**Tool parser**: Hermes-style XML format — `--tool-call-parser hermes`. Chat template uses `<|im_start|>/<|im_end|>` format with `<tool_call><function=name><parameter=key>value</parameter></function></tool_call>`.

**Ollama naming**: Ollama's `nemotron3:33b` = `nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-NVFP4` (the multimodal Omni variant, not the text-only Nano). The "33b" tag is Ollama's compressed-size convention, not parameter count.

**NVFP4 / modelopt**: The Omni NVFP4 variant uses `quant_method: modelopt` (vLLM supports `modelopt_fp4`). Model type `NemotronH_Nano_Omni_Reasoning_V3` maps to `nano_nemotron_vl.py` in vLLM's registry. For text-only agent use, add `--language-model-only`.

Compose pattern for AWQ:
```yaml
command:
  - --model
  - stelterlab/NVIDIA-Nemotron-3-Nano-30B-A3B-AWQ
  - --served-model-name
  - nemotron-3-nano
  - --dtype
  - float16
  - --max-model-len
  - "131072"
  - --trust-remote-code
  - --enforce-eager
  - --enable-auto-tool-choice
  - --tool-call-parser
  - hermes
```

## Model Download Pattern

Use the `hf` CLI (NOT the deprecated `huggingface-cli`):

```bash
# From the vLLM project root:
hf download <model-id> --cache-dir <models-dir>/hub
```

Full example with HF transfer acceleration:
```bash
HF_HUB_ENABLE_HF_TRANSFER=1 hf download stelterlab/NVIDIA-Nemotron-3-Nano-30B-A3B-AWQ \
  --cache-dir /home/fated/vLLMing/qwen-stack/models/hub
```

**Pitfall — deprecated CLI**: `huggingface-cli download` is deprecated and exits immediately with a warning. Always use `hf download` instead. The `hf` command comes with `huggingface_hub` package (in the project venv).\n\n**Pitfall — permission denied on model cache**: Docker containers (which run as root inside) create model cache directories and files owned by `root` under the host-mounted hub directory. When you later try `hf download` as a regular user, you'll get `PermissionError: [Errno 13] Permission denied` on those directories. Fix before any new downloads:\n```bash\nsudo chown -R $USER:$USER <cache-dir>   # e.g. /home/fated/vLLMing/qwen-stack/models/hub\n```\nAlso use full path to `hf` in the project venv (`/home/fated/vLLMing/venv/bin/hf`) since `export` in background shell commands doesn't always propagate to child processes.

## Tool Parser Selection

vLLM needs a tool-call-parser to parse the model's tool call output back into structured JSON. Match the parser to the model's chat template format:

| Model family | Tool format in template | `--tool-call-parser` | Notes |
|---|---|---|---|
| Qwen3.5/3.6 | XML: `<tool_call>...` | `qwen3_coder` | Genesis P64/P68/P69 fix edge cases |
| Nemotron-3 (NemotronH) | XML: `<tool_call><function=name><parameter=key>` | `hermes` | Matches Hermes XML format |
| GPT-OSS 20B | Harmony: `functions.<name>` namespace | *none needed* | vLLM's harmony_utils.py handles parsing |
| Llama 3.x | JSON function call | `pythonic` or `json` | Standard OpenAI format |

**Reasoning parsers**: Qwen3 uses `--reasoning-parser qwen3` for `<think>...</think>` tags. GPT-OSS Harmony uses its own channel-based reasoning (`<|channel|>analysis`) handled by the harmony parser. Nemotron-3 uses `<think>...</think>` in its chat template Jinja — may work with `qwen3` reasoning parser or template-only handling.

## Model Type Registry Check

Before adding a new model, verify vLLM supports its architecture. Check vLLM's model registry:

```python
# In vllm/model_executor/models/registry.py — search for the model_type from config.json
```

Key entries:
- `NemotronHForCausalLM` → `nemotron_h.py`
- `NemotronH_Nano_Omni_Reasoning_V3` → `nano_nemotron_vl.py`
- `GptOssForCausalLM` → (supported via transformers auto-detection)
- `Qwen3_5ForConditionalGeneration` → (supported via transformers)
```bash
# Health check
curl http://localhost:8020/health

# Model list
curl http://localhost:8020/v1/models

# Quick inference test
curl http://localhost:8020/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3.6-27b","messages":[{"role":"user","content":"Say hello in one word."}],"max_tokens":10}'
```

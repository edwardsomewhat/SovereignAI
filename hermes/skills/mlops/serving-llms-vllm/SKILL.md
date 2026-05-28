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

## KV Cache Compatibility

**Critical**: `--kv-cache-dtype fp8_e5m2` is incompatible with compressed-tensors / FP8 checkpoints. vLLM will abort with:
```
ValueError: fp8_e5m2 kv-cache is not supported with fp8 checkpoints.
```

**Fix**: Use `--kv-cache-dtype auto` and let vLLM select the best compatible format. This is especially important for AWQ/compressed-tensors models (Nemotron-3, GPT-OSS, any `quantization=compressed-tensors` model).

The `auto` setting also avoids the silent tool-call cascade that can occur with TurboQuant KV caches under MTP speculative decoding.

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

21B total / 3.6B active MoE (24 experts). Native MXFP4 (~13 GB VRAM for shards, though HF downloads 39 GB with dupes). 128K native context. Apache 2.0. Tagged `vllm` on HF, 8M+ downloads.

**Harmony format is handled natively by vLLM** — no adapter needed. vLLM's `harmony_utils.py` (imports `openai-harmony` Rust library) translates between standard OpenAI API format and Harmony's TypeScript-style tool definitions internally. Standard OpenAI clients work. The `reasoning` field in responses contains the analysis channel (CoT), and `content` contains the final channel — auto-separated.

**Tool calling limitation**: Without `--enable-auto-tool-choice`, tools are rejected (HTTP 400). With it, a `--tool-call-parser` is required — but no standard parser works with Harmony's TypeScript-style tool format. **Partial fix**: a no-op parser plugin (`harmony_noop`) satisfies validation. However, the model still doesn't reliably emit tool calls through the vLLM pipeline because Harmony routes tools through channel output (`<|channel|>commentary`) rather than standard `<tool_call>` blocks. **Use GPT-OSS for reasoning/chat workloads; prefer Nemotron or Qwen for agentic tool-calling.** Reference plugin at `templates/harmony_noop_tool_parser.py`.

Compose pattern:
```yaml
command:
  - --model
  - openai/gpt-oss-20b
  - --served-model-name
  - gpt-oss-20b
  - --dtype
  - auto
  - --max-model-len
  - "131072"        # fits at 13 GB weights + 128K ctx
  - --kv-cache-dtype
  - auto            # fp8_e5m2 incompatible with MXFP4 checkpoints
  - --trust-remote-code
  - --enforce-eager
  # No --tool-call-parser, no --reasoning-parser — harmony handles both
  # No --enable-auto-tool-choice — would require a parser (none compatible)
```

**Performance**: ~80 tok/s decode on RTX 3090 (measured). Faster than Nemotron (~52 tok/s) due to smaller active params (3.6B vs 3B) and efficient MXFP4 kernels.

### Nemotron-3 Nano 30B-A3B

30B total / 3B active MoE (NemotronH architecture, `nemotron_h` in vLLM registry). AWQ INT4 quant at `stelterlab/NVIDIA-Nemotron-3-Nano-30B-A3B-AWQ` (**~17 GB** actual — 4 shards: 3×4.7GB + 2.7GB, NOT the ~8 GB many assume). On a 24 GB 3090, this leaves only ~5-6 GB for KV cache, capping realistic context at ~65K (at 0.95 util with auto KV dtype). 128K native context.

**Tool parser**: XML format — `<tool_call><function=name><parameter=key>value</parameter></function></tool_call>`. vLLM's built-in `hermes` parser expects JSON inside the tags and silently fails on this XML. Use the custom `nemotron_xml` parser plugin instead (see "Custom Tool Parser Plugins" below). Chat template uses `<|im_start|>/<|im_end|>` format. Working round-trip verified: tool call → result → final answer.

**Ollama naming**: Ollama's `nemotron3:33b` = `nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-NVFP4` (the multimodal Omni variant, not the text-only Nano). The "33b" tag is Ollama's compressed-size convention, not parameter count.

**NVFP4 / modelopt**: The Omni NVFP4 variant uses `quant_method: modelopt` (vLLM supports `modelopt_fp4`). Model type `NemotronH_Nano_Omni_Reasoning_V3` maps to `nano_nemotron_vl.py` in vLLM's registry. For text-only agent use, add `--language-model-only`.

Compose pattern for AWQ (tested and working on RTX 3090 24 GB):
```yaml
command:
  - --model
  - stelterlab/NVIDIA-Nemotron-3-Nano-30B-A3B-AWQ
  - --served-model-name
  - nemotron-3-nano
  - --dtype
  - float16
  # 65K context — safe for 17 GB weights (5.1 GB KV remaining).
  # 128K will OOM. Try 81920 or 98304 if adventurous.
  - --max-model-len
  - "65536"
  - --gpu-memory-utilization
  - "0.95"
  - --kv-cache-dtype
  - auto           # fp8_e5m2 incompatible with compressed-tensors
  - --trust-remote-code
  - --enforce-eager
  - --enable-auto-tool-choice
  - --tool-call-parser
  - nemotron_xml
  - --tool-parser-plugin
  - /patches/nemotron_xml_tool_parser.py
  # No --reasoning-parser — Nemotron template handles <think> natively
```

**Key config decisions**:
- `--kv-cache-dtype auto` (NOT `fp8_e5m2`) — compressed-tensors fp8 checkpoint incompatibility
- `--gpu-memory-utilization 0.95` — needs the headroom; 5.1 GB KV at 65K
- `--max-model-len 65536` — realistic ceiling on 24 GB with 17 GB weights
- No reasoning parser — template's `<think>...</think>` handled by Jinja template natively

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

vLLM needs a tool-call-parser to parse the model's tool call output back into structured JSON. Match the parser to the model's chat template format.

**Critical rule**: `--enable-auto-tool-choice` **requires** `--tool-call-parser` to be set — vLLM v0.19+ enforces this at validation. Without both, the server rejects any request containing a `tools` array with HTTP 400. You MUST provide both flags together or neither.

| Model family | Tool format in template | `--tool-call-parser` | Notes |
|---|---|---|---|
| Qwen3.5/3.6 | XML: `<tool_call>...` | `qwen3_coder` | Genesis P64/P68/P69 fix edge cases |
| Nemotron-3 (NemotronH) | XML: `<tool_call><function=name><parameter=key>` | `nemotron_xml` (plugin) | Built-in `hermes` parser expects JSON, fails on Nemotron XML. Use `nemotron_xml_tool_parser.py` plugin — registered via `ToolParserManager.register_module("nemotron_xml")`, loaded with `--tool-parser-plugin`. |
| GPT-OSS 20B | Harmony: `functions.<name>` namespace | *none works* | vLLM's harmony_utils.py handles format translation, but tool parsing through standard `--tool-call-parser` is not supported. Without `--enable-auto-tool-choice`, tools are rejected. With it, a parser is required but none match. **Workaround**: use for reasoning/chat; prefer Nemotron or Qwen for agentic tool-calling. |
| Llama 3.x | JSON function call | `pythonic` or `json` | Standard OpenAI format |

**Reasoning parsers**: Qwen3 uses `--reasoning-parser qwen3` for `<think>...</think>` tags. GPT-OSS Harmony uses its own channel-based reasoning (`<|channel|>analysis`) handled by the harmony parser — no explicit reasoning-parser needed. Nemotron-3 uses `<think>...</think>` in its chat template Jinja — template handles it natively; adding `--reasoning-parser deepseek_r1` strips think blocks but may interfere with tool call parsing.

## Custom Tool Parser Plugins

vLLM supports loading custom tool parsers via `--tool-parser-plugin <path>`. The plugin file must register itself using the `ToolParserManager.register_module("name")` decorator. The registered name becomes the value for `--tool-call-parser`.

### Plugin structure

```python
from vllm.tool_parsers import ToolParserManager
from vllm.tool_parsers.abstract_tool_parser import ToolParser

@ToolParserManager.register_module("my_parser_name")
class MyCustomParser(ToolParser):
    supports_required_and_named: bool = True  # or False for non-JSON formats

    def extract_tool_calls(self, model_output, request, token_ids=None):
        # Parse model_output string, return ExtractedToolCallInformation
        ...

    def extract_tool_calls_streaming(self, previous_text, current_text,
                                      delta_text, request, token_ids=None):
        # Return DeltaMessage with tool call deltas
        ...
```

### Key implementation notes

- **`token_ids` kwarg**: vLLM v0.19+ passes `token_ids: Sequence[int] | None = None` to both `extract_tool_calls` and `extract_tool_calls_streaming`. Always include it in your method signatures even if unused — otherwise you get `TypeError: got an unexpected keyword argument 'token_ids'`.
- **`supports_required_and_named`**: Set `False` for non-JSON formats (XML, custom templates). When `False`, vLLM falls back to your `extract_tool_calls` for required/named tool choice instead of using its built-in JSON parser.
- **Registration**: The `@ToolParserManager.register_module("name")` decorator registers your class. The name used in the decorator is what you pass to `--tool-call-parser`.
- **Mounting**: Mount the plugin file into the Docker container and pass both `--tool-call-parser <name>` and `--tool-parser-plugin <path>`.

### Docker Compose plugin mount

```yaml
volumes:
  - ../patches/my_parser.py:/patches/my_parser.py:ro

command:
  - --enable-auto-tool-choice
  - --tool-call-parser
  - my_parser_name
  - --tool-parser-plugin
  - /patches/my_parser.py
```

### Nemotron XML parser example

Nemotron-3 outputs XML tool calls that vLLM's built-in `hermes` parser can't handle (it expects JSON). The fix is a custom parser registered as `nemotron_xml`:

```python
@ToolParserManager.register_module("nemotron_xml")
class NemotronXMLToolParser(ToolParser):
    supports_required_and_named = False
    tool_call_start_token = "<tool_call>"
    tool_call_end_token = "</tool_call>"

    def extract_tool_calls(self, model_output, request, token_ids=None):
        # Parse <tool_call><function=name><parameter=key>val</parameter></function></tool_call>
        # into ToolCall objects with json.dumps(arguments)
        ...
```

Full reference implementation at `templates/nemotron_xml_tool_parser.py` and `templates/harmony_noop_tool_parser.py`.

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

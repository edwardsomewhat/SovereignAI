# Multi-Token Prediction (MTP) in llama.cpp & Ollama

Status as of May 2026. MTP allows models to predict multiple future tokens in a single
forward pass, reducing sequential decoding latency. It is a form of speculative decoding
where the drafting capability is built into the model architecture rather than requiring
a separate draft model.

## How MTP Differs from Standard Speculative Decoding

| Aspect | Draft-Model Speculative | MTP |
|--------|------------------------|-----|
| Draft source | Separate small model | Built into target model architecture |
| Overhead | Two models loaded | One model + lightweight assistant head |
| Deployment | `--model` + `--model-draft` | `--mtp-head` (custom fork) or native |
| Acceptance rate | Varies by draft model | 70–90% on conversational tasks |

## llama.cpp MTP Status

### Upstream (ggml-org/llama.cpp) — Qwen 3.5 MTP WORKS natively

As of b9247 (May 20, 2026), `--spec-type draft-mtp` is merged into upstream
llama.cpp. Qwen 3.5 models with MTP heads (e.g. `unsloth/Qwen3.5-9B-MTP-GGUF`)
work directly — no custom fork needed.

Launch command (proven on P5000 Vulkan, 27.3 tok/s, 64-79% draft acceptance):
```bash
llama-server \
    -hf unsloth/Qwen3.5-9B-MTP-GGUF:UD-Q4_K_XL \
    -ngl 99 -c 8192 -fa on -np 1 \
    --spec-type draft-mtp --spec-draft-n-max 6 \
    --host 0.0.0.0 --port 8080
```

Note: `-np > 1` and `--mmproj` are not yet supported with MTP.
The flag was renamed from `--spec-type mtp` to `--spec-type draft-mtp` on May 13, 2026.

- PR #20533: Qwen MTP support — merged
- PR #12130 (discussion): General speculative decoding / MTP tracking
- Gemma 4 MTP: NOT in upstream yet. Requires the `gemma4_assistant` architecture
  which is only in forks as of May 2026.

### AtomicBot Fork (Working Gemma 4 MTP on Linux CUDA)

```
github.com/AtomicBot-ai/atomic-llama-cpp-turboquant
```

Features:
- `gemma4_assistant` MTP architecture
- TurboQuant KV-cache compression (`-ctk turbo3 -ctv turbo3`)
- `--mtp-head` flag for loading assistant GGUF
- `--spec-type mtp` speculative decoding mode

Launch command:
```bash
llama-server \
    -m         gemma-4-E4B-it-Q4_K_M.gguf \
    --mtp-head gemma-4-E4B-it-assistant.Q4_K_M.gguf \
    --spec-type mtp \
    --draft-block-size 3 --draft-max 8 --draft-min 0 \
    -ngl 99 -ngld 99 \
    -ctk turbo3 -ctv turbo3 -ctkd turbo3 -ctvd turbo3 \
    -fa on -c 16384 --host 127.0.0.1 --port 8080
```

Draft parameters: `--draft-block-size 2-3`, `--draft-max 6-8`.
Presets available: `MTP_PRESET=throughput|lift|balanced|quality`.

## Ollama MTP Status

### Gemma 4 MTP — Mac-Only

`gemma4:31b-coding-mtp-bf16` requires macOS (MLX runner).
Pulling on Linux/NVIDIA returns: `Error: pull model manifest: 412: this model requires macOS`
(GitHub issue #16019, closed as completed — MLX Linux port in progress, not yet production-ready).

### Qwen 3.6 MLX — Experimental Linux Support

A maintainer demonstrated `qwen3.6:35b-a3b-mlx-bf16` working on Linux:
- 126.98 tok/s (MLX) vs 105.47 tok/s (standard) on NVIDIA GB10
- 69 GB VRAM (MLX) vs 82 GB (standard)
- Not officially supported — requires v0.30.0-rc series

### v0.30.0-rc (May 2026)

Architectural rewrite: "Directly supports llama.cpp (replaces GGML)."
This may bring broader MTP support to Linux as llama.cpp MTP PRs land.
Install: `curl -fsSL https://ollama.com/install.sh | OLLAMA_VERSION=0.30.0-rc21 sh`

## MTP-Capable Model Families

| Family | MTP Status | Backend | Notes |
|--------|-----------|---------|-------|
| Qwen3.5 (9B) | **Working in upstream llama.cpp** | `--spec-type draft-mtp` | `unsloth/Qwen3.5-9B-MTP-GGUF`, UD-Q4_K_XL ~5GB, ~27 tok/s on P5000 Vulkan, 64-79% acceptance |
| Qwen3.6 (27B) | **Working in upstream llama.cpp** | `--spec-type draft-mtp` | `unsloth/Qwen3.6-27B-MTP-GGUF`, Q4_K_XL ~17GB, spills 1-2 layers on 16GB GPUs |
| Qwen3.6 (35B-A3B MoE) | **Working in upstream llama.cpp** | `--spec-type draft-mtp` | `unsloth/Qwen3.6-35B-A3B-MTP-GGUF`, ~15GB Q4 — 3B active, better fit for 16GB than 27B dense |
| Qwopus3.5-9B-Coder | **Working** | `--spec-type draft-mtp` | Coding fine-tune of Qwen3.5-9B, `Jackrong/Qwopus3.5-9B-Coder-MTP-GGUF` |
| Gemma 4 (E2B/E4B/26B/31B) | Mac-only in Ollama; Linux via AtomicBot fork | MLX or custom llama.cpp | Assistant ~75MB GGUF, target ~4.5GB Q4_K_M for E4B |
| Qwen 3-Next | Native MTP architecture | llama.cpp (upstream PR) | `qwen3-next:latest` on Ollama |
| GLM-4/5 | MTP strings in Ollama binary | Ollama | `glm5:latest` |
| DeepSeek-V3/R1 | **NOT supported** for draft-mtp | Standard only | MTP heads exist in architecture but llama.cpp has no draft-mtp backend for DeepSeek's tensor layout. Standard speculative decoding with separate draft model works but adds complexity. |

## Finding MTP Models on Hugging Face

Better than searching "mtp" as a keyword:

1. **Unsloth's org** — all MTP GGUFs live here:
   `https://huggingface.co/unsloth` — look for "-MTP-GGUF" repos

2. **HF filtered search**:
   `https://huggingface.co/models?apps=llama.cpp&search=mtp&sort=trending`

3. **Any Qwen3.5/3.6 GGUF supports MTP**. The MTP heads are baked into the base
   architecture — even GGUFs without "MTP" in the name work with
   `--spec-type draft-mtp`. The dedicated "-MTP-GGUF" repos just guarantee
   the MTP tensors were included during conversion.

## GPU VRAM Spillover

When a model doesn't fully fit in VRAM with `-ngl 99`:

- llama.cpp uses **mmap** to map the model file into system RAM
- Layers that don't fit in VRAM are offloaded to CPU RAM automatically
- **No crash** — just slower for the spilled layers
- Performance hit: ~30-50% slower for spilled layers vs all-GPU
- The `-ngl N` flag controls how many layers stay on GPU (e.g., `-ngl 40` puts first 40 layers on GPU, rest on CPU)
- For MoE models, `-ncmoe N` offloads MoE expert tensors to CPU separately
- Example: Qwen3.6-27B Q4_K_XL (~17GB) on P5000 (16GB) spills ~1-2 layers to CPU RAM, still runs fine with 62GB system RAM available
| GLM-4/5 | MTP strings in Ollama v0.24 binary | Ollama | `glm5:latest` |

## MTP Drafter GGUF Repos (Hugging Face)

- `AtomicChat/gemma-4-E4B-it-assistant-GGUF` — E4B drafter, Q4_K_M ~75MB
- `AtomicChat/gemma-4-31B-it-assistant-GGUF` — 31B drafter
- `AtomicChat/gemma-4-26B-A4B-it-assistant-GGUF` — 26B MoE drafter
- `cafkafk/gemma-4-31B-it-assistant-GGUF-noimatrix` — 31B drafter (no imatrix)

Target model GGUFs: `unsloth/gemma-4-E4B-it-GGUF`, `unsloth/gemma-4-31B-it-GGUF`

## Real-World Benchmark Numbers

| Model | Hardware | Speedup | Source |
|-------|----------|---------|--------|
| Gemma 4 26B MoE | RTX PRO 6000 | up to 3x | Google |
| Gemma 4 31B Dense | H100 | ~1.9x (14→27 t/s) | Google |
| Consumer GPU | RTX 4090 class | 1.8–2.5x | Google |
| Apple Silicon | M3/M4 Max 32GB+ | 1.6–2.2x | Google |
| Gemma 4 E4B | Custom fork, CUDA | up to 60% throughput | Reddit r/LocalLLaMA |
| Qwen 3.5 9B MTP | P5000 Vulkan | ~27 tok/s, 64-79% draft acceptance | Session test, May 2026 |
| Qwen 3.6 35B MLX | NVIDIA GB10 | ~20% (105→127 t/s) | Ollama maintainer |

## Key Pitfalls

### Gemma 4 MTP requires custom fork
The `gemma4_assistant` architecture is NOT in upstream llama.cpp.
Do NOT attempt to load assistant GGUFs with stock `llama-server` — they will fail.
Use AtomicBot fork or wait for upstream merge.

### Ollama MTP models are Mac-only
`gemma4:31b-coding-mtp-bf16` and similar tags only work on macOS.
They will fail with "requires macOS" on Linux, regardless of GPU.

### Assistant GGUF is tiny but critical
The drafter is ~75MB (Q4_K_M) for E4B — don't skip it.
Without the assistant, there is no speedup; the target model runs in standard mode.

### MLX runner is not production-ready on Linux
The Linux MLX port exists but is experimental. Performance gains are real
but stability is not guaranteed. For production Linux MTP, use upstream
llama.cpp with `--spec-type draft-mtp` (Qwen 3.5) or the AtomicBot fork (Gemma 4).

### No CUDA Linux binaries in official releases
Official llama.cpp releases provide pre-built CUDA binaries for Windows only.
For Linux, the pre-built options are: CPU, Vulkan, ROCm, OpenVINO, SYCL.
For CUDA on Linux, you MUST build from source with `-DGGML_CUDA=ON`.

### Older NVIDIA GPUs (CC < 7.5): use Vulkan, not CUDA
GPUs like Quadro P5000 (CC 6.1) with older drivers (535.x) cannot use
ai-dock's pre-built CUDA 12.8 binaries (require CC 7.5+ and driver ≥570).
The official Vulkan pre-built binaries work with these GPUs and support
`--spec-type draft-mtp` — performance is within ~5% of CUDA on this class.

### GPU VRAM spillover behavior

When a model doesn't fit entirely in GPU VRAM, llama.cpp spills overflow
layers to system RAM automatically. It won't crash — just gets slower.

- `-ngl 99` = try everything on GPU. Overflow layers auto-spill to RAM via mmap
- `-ngl 20` = manual: first 20 layers GPU, rest CPU RAM
- Performance hit: ~30-50% slower for spilled layers vs all-GPU
- For 16GB GPUs: 15GB models (Qwen3.6-27B IQ4_XS) fit. 22GB+ models
  (Qwen3.6-35B-A3B Q4_K_M) need partial offload
- MoE note: GGUF file size = ALL experts. Choose IQ quants or smaller
  dense models for tight VRAM budgets
- System RAM headroom matters: 62GB RAM on hq-ai means even a 23GB
  spill fits easily in system memory

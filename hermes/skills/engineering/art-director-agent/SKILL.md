---
name: art-director-agent
description: Architecture and design for the sovereign-based Art Director agent that controls ConchAI ComfyUI. Covers the full pipeline from orchestrator delegation through local image/video generation, vision-based evaluation, iteration, and QC.
version: 1.0.0
---

# Art Director Agent Architecture

## Pipeline

```
User → Orchestrator (sovereign) → Art Director Agent (sovereign) → ComfyUI (conchai, Tailscale)
```

All image/video generation stays local. External APIs only for final QC pass if needed.

## Agent Flow

1. Orchestrator receives task, reasons about it, defines scope
2. Delegates to Art Director Agent with a clear task definition
3. Art Agent (vision-capable, Qwen3+ 9B minimum via llama.cpp):
   a. Evaluates task — identifies scope, constraints, required outputs
   b. Compares to available tools (skills, ComfyUI toolkit, models on ConchAI)
   c. Develops plan of attack (workflow selection or creation)
   d. Engages ConchAI ComfyUI over Tailscale (100% local)
   e. Generates → evaluates output with vision → iterates if needed
   f. Internal QC (Florence model for aesthetic judgment)
   g. Optional: external API QC for final pass
   h. Returns completed work to orchestrator

## Infrastructure

- **Orchestrator**: sovereign, Hermes Agent (deepseek-v4-pro or similar for heavy reasoning)
- **Art Director Agent**: sovereign, Hermes Agent subagent with vision-capable model
- **ComfyUI**: conchai, RTX 3090 24GB, systemd on :8188, Tailscale IP 100.69.153.16
- **Model server**: Ollama on hq-ai (100.84.92.74:11434/v1, Tailscale). llama.cpp available on sovereign for future use.
- **File access**: File Browser at conchai:8190 (fated/Strange112263!)
- **Models available**: 584GB — Flux Dev fp8, SDXL + 5 fine-tunes (epicrealism, dreamshaper, etc.), Qwen Image Edit 2509/2511/Lightning (GGUF + safetensors), z-image turbo, Wan2.1 FLF2V/I2V/T2V fp8, LTX-Video 13B/2B distilled fp8, 6× Qwen LoRAs (Relight, Multiple-angles, Fusion, Anything2Real, Light-Migration, White-to-Scene)
- **Workflows**: Combustion-Edit-Qwen, Combustion-Edit, Glass_Crop_Flo_v1, glass_production, Qwen 2509 V2, qwen_editing_workflow (all in user/default/workflows/)
- **Custom nodes**: 30 installed including Qwen-specific (PainterQwen, lenML adv, QwenVL, TextEncodeAdvanced) and video (WanWrapper, HunyuanVideoWrapper, LTXVideo, VideoHelperSuite)

## Qwen Mastery Goals

- Master Qwen Image Edit 2509/2511 pipeline (canonical: GGUF → lenML TextEncodeAdv + built-in TextEncode → CFGNorm → KSampler Efficient, 4 steps with Lightning LoRA)
- Research and integrate future Qwen image models
- Master Qwen TTS and STT models for voice interaction
- Florence2 already on ConchAI for aesthetic QC; consider Florence on nano when available

## Hermes Memory & Config

- Memory char limit configurable in ~/.hermes/config.yaml: `memory.memory_char_limit` (default 2200, bumped to 5000)
- User profile limit: `memory.user_char_limit` (default 1375, bumped to 2500)
- Memory = persistent facts (IPs, passwords, model paths, preferences). Skills = procedures and architectures.
- Clean memory periodically — move stale infrastructure notes to skills, keep memory for active operational facts

## Vision Pipeline (ACTIVE)

Vision is configured via Ollama on hq-ai (100.84.92.74:11434/v1). Model: `qwen3-vl:8b` (6.1GB). Hermes `auxiliary.vision` config routes `vision_analyze()` calls to this endpoint. The agent can now see generated images by passing the file path + a question to vision_analyze — description text is injected into context for reasoning. All local, no external API.

## Ollama Models on hq-ai (100.84.92.74)

Accessible over Tailscale at http://100.84.92.74:11434/v1. SSH requires Tailscale browser re-auth — use the HTTP API directly for model queries.

- `qwen3-vl:8b` — 6.1GB, vision
- `hermes3:8b` — 4.7GB, general
- `deepseek-r1:14b` — 9.0GB, reasoning
- `mannix/gemma4-98e-v5-coder:Q4_K_S` — 12.2GB

## Vision Model

Configured via `auxiliary.vision` in config.yaml:
- **Provider**: ollama
- **Model**: qwen3-vl:8b (6.1GB)
- **Base URL**: http://100.84.92.74:11434/v1 (HQ-AI over Tailscale)
- **Usage**: `vision_analyze` tool routes image+question to qwen3-vl, returns text description, main model continues reasoning.

**Limitation**: qwen3-vl:8b has no pop-culture knowledge. It will describe images accurately in terms of visual elements (colors, clothing, composition) but cannot identify specific celebrities, wrestlers, or characters by name. For identity verification, the agent must compare against reference images rather than relying on the VL model to recognize individuals.

## Key URLs

- ComfyUI: http://100.69.153.16:8188 (conchai)
- File Browser: http://100.69.153.16:8190 (login: fated/Strange112263!)
- COMFY_HOST env var on sovereign: http://100.69.153.16:8188
- Ollama API (HQ-AI): http://100.84.92.74:11434/v1

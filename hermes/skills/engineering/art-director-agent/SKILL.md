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
- **Model server**: llama.cpp on sovereign (turboQuant/MTP), switched from Ollama for larger context windows
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

## Vision Models

- Florence2 for aesthetic QC (already on ConchAI)
- Qwen VL for agent vision (need to deploy)
- Qwen3+ 9B+ for main agent reasoning

## Key URLs

- ComfyUI: http://100.69.153.16:8188
- File Browser: http://100.69.153.16:8190
- COMFY_HOST env var on sovereign: http://100.69.153.16:8188

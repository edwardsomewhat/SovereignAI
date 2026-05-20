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

- **Orchestrator**: sovereign, Hermes Agent
- **Art Director Agent**: sovereign, Hermes Agent subagent with vision model
- **ComfyUI**: conchai, RTX 3090 24GB, systemd on :8188
- **Model server**: llama.cpp on sovereign (turboQuant/MTP), switched from Ollama
- **File access**: File Browser at conchai:8190 (fated/Strange112263!)
- **Models available**: 584GB — Flux Dev, SDXL fine-tunes, Qwen 2509/2511/Lightning, z-image turbo, Wan2.1 FLF2V/I2V/T2V, LTX 13B/2B, 6 Qwen LoRAs

## Vision Models

- Florence2 for aesthetic QC (already on ConchAI)
- Qwen VL for agent vision (need to deploy)
- Qwen3+ 9B+ for main agent reasoning

## Key URLs

- ComfyUI: http://100.69.153.16:8188
- File Browser: http://100.69.153.16:8190
- COMFY_HOST env var on sovereign: http://100.69.153.16:8188

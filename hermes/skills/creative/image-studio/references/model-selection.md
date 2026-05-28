# Image Studio — Model Selection Logic

Concrete routing rules for choosing the right ComfyUI model and node per task.

## Primary Routing Table (Conchai 3090)

| Task Quality | Model | Workflow | VRAM | Speed | Best For |
|-------------|-------|----------|------|-------|----------|
| **maximum** | flux1-dev-fp8 | Flux txt2img | ~18 GB | ~3 min | Hero images, concept art, brand assets |
| **high** | juggernautXL_ragnarokBy | SDXL txt2img | ~8 GB | ~30 sec | Photoreal product shots, portraits |
| **standard** | sd_xl_base_1.0 | SDXL txt2img | ~8 GB | ~30 sec | General purpose, illustrations |
| **stylized** | photon_v1 | SD1.5 txt2img | ~4 GB | ~15 sec | Stylized, artistic, fast drafts |
| **editing** | Qwen Image Edit | Qwen img2img | ~20 GB | ~2 min | Text-guided image manipulation |
| **inpainting** | flux1-fill-dev | Flux inpaint | ~23 GB | ~4 min | Object removal, region fill |

## Flux 1 txt2img Workflow (programmatic construction)

```
Node chain:
  DualCLIPLoader → CLIPTextEncode (prompt) + CLIPTextEncode (negative)
  UNETLoader → BasicScheduler (model input, outputs ONLY SIGMAS)
  UNETLoader → CFGGuider (model + positive + negative, cfg=1.0)
  KSamplerSelect → SamplerCustomAdvanced (sampler_name="euler")
  EmptySD3LatentImage → SamplerCustomAdvanced (Flux 1 uses SD3 latent format)
  RandomNoise → SamplerCustomAdvanced (noise_seed=42 for reproducible)
  VAELoader → VAEDecode
  SamplerCustomAdvanced → VAEDecode → SaveImage
```

Critical: `BasicScheduler` outputs only SIGMAS. Do NOT try to use its outputs
as guider/sampler — use separate `CFGGuider` and `KSamplerSelect` nodes.

## SDXL txt2img Workflow (simpler)

```
Node chain:
  CheckpointLoaderSimple → CLIPTextEncode (prompt) + CLIPTextEncode (negative)
  EmptyLatentImage → KSampler
  VAEDecode → SaveImage
```

## Dimension Constraints

| Model | Width/Height Step | Min | Max |
|-------|-------------------|-----|-----|
| Flux 1 | multiples of 16 | 16 | 16384 |
| SDXL | multiples of 8 | 16 | 16384 |
| SD 1.5 | multiples of 8 | 16 | 16384 |

## Fallback Routing

If Conchai 3090 is busy or low VRAM:
- **hq-ai P5000 (16 GB):** Can run SDXL/Juggernaut workflows (~8 GB VRAM).
  ComfyUI must be running and upgraded from v0.8.2 to current.
- **photon_v1 on Conchai:** Even with limited VRAM (8+ GB), photon fits easily.
- **Comfy Cloud:** External overflow for batch jobs, requires API key + paid tier.

## Seed Convention

- `seed: -1` → random seed (fresh each run)
- `seed: <fixed_number>` → reproducible output
- For batch variations: use `run_batch.py --randomize-seed` or loop with random seeds

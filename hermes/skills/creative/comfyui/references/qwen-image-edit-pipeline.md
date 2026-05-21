# Qwen Image Edit — Canonical ComfyUI Pipeline

Discovered through iterative testing against the lenML demo workflow and NextDiffusion tutorial. Getting Qwen Image Edit working requires exact component matching — nearly every attempt without the full pipeline produced wrong output (8-bit pixelation, identity loss, or silent failure).

## Model Placement (ComfyUI directory structure)

```
models/
  diffusion_models/
    qwen_image_edit_2511_fp8_e4m3fn.safetensors   ← FP8 safetensors (primary)
    qwen_image_edit_2509_fp8_e4m3fn.safetensors
  clip/
    qwen_2.5_vl_7b_fp8_scaled.safetensors         ← CLIP type: qwen_image
  vae/
    qwen_image_vae.safetensors                     ← Qwen-specific VAE
  loras/
    Qwen-Image-Edit-Lightning-8steps-V1.0.safetensors   ← 8-step Lightning LoRA
    Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors  ← 4-step
```

FP8 safetensors with UNETLoader is the primary recommended path (tutorial source). GGUF with UnetLoaderGGUF is the fallback for lower VRAM. Q5_1 and Q6_K GGUF variants were tested; both produced passable results but FP8 safetensors with UNETLoader gave noticeably better quality.

## Canonical Workflow Structure

The lenML demo workflow (`comfyui_qwen_image_edit_adv/workflows/demo_simple.json`) is the reference implementation. Key nodes and wiring:

```
UnetLoaderGGUF (or UNETLoader for FP8) → model
    → LoraLoaderModelOnly → model+Lora → CFGNorm → KSampler (Efficient)

CLIPLoader (type: qwen_image) → clip → TextEncodeQwenImageEditAdv
                                       → TextEncodeQwenImageEdit

VAELoader → vae → TextEncodeQwenImageEditAdv
                → TextEncodeQwenImageEdit  
                → KSampler (Efficient) optional_vae

LoadImage → QwenImageEditSimpleScale (1024, 32) → image → both encoders

TextEncodeQwenImageEditAdv → POSITIVE (output 0) + LATENT (output 1)
TextEncodeQwenImageEdit    → NEGATIVE (output 0)

KSampler (Efficient):
  model ← CFGNorm output 0
  positive ← TextEncodeQwenImageEditAdv output 0
  negative ← TextEncodeQwenImageEdit output 0
  latent_image ← TextEncodeQwenImageEditAdv output 1
  optional_vae ← VAELoader output 0
  vae_decode: true (outputs IMAGE at slot 5)
  steps: 8 (with 8-step Lightning) or 4 (with 4-step Lightning)
  cfg: 1.0–2.0
```

SaveImage takes KSampler (Efficient) output slot 5 (IMAGE).

## Critical Pitfalls

1. **QwenImageEditSimpleScale is MANDATORY.** Without it, Qwen generates at mismatched resolution producing 8-bit/pixelated output. Set resolution=1024, alignment=32.

2. **CLIP type MUST be `qwen_image`** — using `stable_diffusion` produces wrong conditioning. The built-in ComfyUI CLIPLoader supports this type natively.

3. **TextEncodeQwenImageEditAdv does NOT accept `model` input** — only `clip`, `prompt`, `vae` (optional), `image` (optional). The model goes directly to the sampler via CFGNorm.

4. **KSampler (Efficient) required inputs:** model, positive, negative, latent_image, seed, steps, cfg, sampler_name, scheduler, denoise, preview_method, vae_decode. All must be provided or validation fails.

5. **KSampler (Efficient) outputs 6 slots:** MODEL(0), CONDITIONING+(1), CONDITIONING-(2), LATENT(3), VAE(4), IMAGE(5). Use slot 5 for direct decoded output when vae_decode=true.

6. **Dual encoder pattern:** TextEncodeQwenImageEditAdv (lenML) handles POSITIVE + LATENT encoding with fixed offset. Built-in TextEncodeQwenImageEdit handles NEGATIVE. Both are needed — single encoder fails validation.

7. **FP8 > GGUF for quality.** GGUF works but produces softer results. Use FP8 safetensors with UNETLoader and `weight_dtype: fp8_e4m3fn` for best quality on 24GB cards.

8. **Git-lfs pull with `-I` glob patterns fails on Comfy-Org split repos.** Must use `git lfs checkout` with explicit file paths, or wget direct file URLs from HuggingFace.

## Model Sources

- Qwen Image Edit models: `Comfy-Org/Qwen-Image-Edit_ComfyUI` (open, split repo)
- CLIP: `qwen_2.5_vl_7b_fp8_scaled.safetensors` from community repos or `comfyanonymous/flux_text_encoders` style mirrors
- VAE: `Remudl/qwen-image-vae` (open, single file)
- Lightning LoRAs: `lightx2v/Qwen-Image-Edit-2511-Lightning` (open)
- z-image turbo: `Comfy-Org/z_image_turbo_ComfyUI` (open, split repo, git clone with LFS works)

## Custom Node Dependencies

- `ComfyUI-GGUF` — UnetLoaderGGUF for GGUF format
- `comfyui_qwen_image_edit_adv` (lenML) — TextEncodeQwenImageEditAdv, QwenImageEditSimpleScale
- `ComfyUI-PainterQwenImageEdit` (princepainter) — PainterQwenImageEditPlus
- `Comfyui-QwenEditUtils` — QwenEditConfigParser, etc.
- `ComfyUi-TextEncodeQwenImageEditAdvanced` — TextEncodeQwenImageEditEnhanced
- Built-in ComfyUI: TextEncodeQwenImageEdit, CLIPLoader (supports qwen_image type), UNETLoader
- `efficiency-nodes-comfyui` — KSampler (Efficient), CFGNorm

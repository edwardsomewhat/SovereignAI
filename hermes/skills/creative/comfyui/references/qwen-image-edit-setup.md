# Qwen Image Edit Pipeline — Canonical Setup (May 2026)

> Researched from community sources: princepainter/ComfyUI-PainterQwenImageEdit,
> lenML/comfyui_qwen_image_edit_adv, Comfy-Org/HuggingFace model repos, and
> user field experience (Windows → Linux migration).

## Required Custom Nodes

| Node | Source | Purpose |
|------|--------|---------|
| ComfyUI-PainterQwenImageEdit | princepainter GitHub | Base editing node (PainterQwenImageEditPlus) |
| comfyui_qwen_image_edit_adv | lenML GitHub | Fixes pixel offset, provides TextEncodeQwenImageEditAdv, scaling nodes |
| ComfyUI-GGUF | Manager registry | GGUF model loading (preferred for Qwen) |
| Comfyui-QwenEditUtils | Manager registry | Text encoding utilities |
| ComfyUI_QwenVL | GitHub clone | Vision-language integration |
| ComfyUi-TextEncodeQwenImageEditAdvanced | GitHub clone | Advanced text encoding |
| Comfyui-CustomizeTextEncoder-Qwen-image | GitHub clone | Custom text encoder |

## Required Models

### Primary (GGUF — preferred path)
- `Qwen-Image-Edit-2511-Q4_K_M.gguf` or `Q5_1.gguf` → `models/unet/`
- Source: community GGUF conversions or Windows build (ComfyUI works with GGUF via LoaderGGUF node)

### Alternative (safetensors — flatter path)
- `qwen_image_edit_2511_fp8mixed.safetensors` → `models/checkpoints/`
- Source: Comfy-Org/Qwen-Image-Edit_ComfyUI (split repo) or flat copies from Windows build

### Support models (required regardless of format)
- `qwen_2.5_vl_7b_fp8_scaled.safetensors` → `models/clip/`
  - Source: Windows build or community repos. NOT in Comfy-Org Qwen repo.
- `qwen_image_vae.safetensors` → `models/vae/`
  - Source: remudl/qwen-image-vae (HF) or Windows build

### Lightning LoRA (enables 4-step generation)
- `Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors` → `models/loras/`
  - Source: lightx2v/Qwen-Image-Edit-2511-Lightning (HF, 252k downloads)
  - Without this: use 20+ sampling steps. With it: 4 steps.

## Canonical Workflow

```
1. LoaderGGUF
   └─ unet_name: "Qwen-Image-Edit-2511-Q5_1.gguf"
        ↓ MODEL
2. LoraLoaderModelOnly
   └─ lora_name: "Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors"
   └─ strength_model: 1
        ↓ MODEL+LORA
3. CLIPLoader
   └─ clip_name: "qwen_2.5_vl_7b_fp8_scaled.safetensors"
   └─ type: "qwen_image"  ← CRITICAL: NOT "stable_diffusion"
        ↓ CLIP
4. VAELoader
   └─ vae_name: "qwen_image_vae.safetensors"
        ↓ VAE
5. LoadImage → input image(s)
6. QwenImageEditSimpleScale (lenML)
   └─ resolution: 1024, alignment: 32
7a. TextEncodeQwenImageEditAdv (lenML) — for POSITIVE + LATENT
   └─ image, clip, model, prompt
   └─ Outputs: CONDITIONING (index 0), LATENT (index 1)
   └─ NOTE: only 2 outputs — NO negative conditioning!
7b. TextEncodeQwenImageEdit (built-in) — for NEGATIVE only
   └─ Same image, clip, model; prompt = what to AVOID
   └─ Output: CONDITIONING (index 0)
8. CFGNorm
   └─ model ("4", 0), strength: 1
        ↓ normalized MODEL
9. KSampler (Efficient) — NOT standard KSampler
   └─ model: CFGNorm output, positive: node 7a[0], negative: node 7b[0], latent: node 7a[1]
   └─ steps: 4, cfg: 1, sampler: euler, scheduler: simple
   └─ denoise: 1, preview_method: "none", vae_decode: "false"
   └─ REQUIRED inputs that standard KSampler lacks: denoise, preview_method, vae_decode
        ↓ LATENT
10. VAEDecode → SaveImage
```

## Critical Pitfalls

1. **CLIP type MUST be `qwen_image`** — Using `stable_diffusion` silently produces wrong results. The model loads fine but the text/vision encoding is completely wrong. This is the #1 cause of "workflow runs but output is garbage."

2. **Resolution alignment** — Width and height must be multiples of 32. Optimal around 1024px. The lenML QwenImageEditSimpleScale handles this automatically.

3. **Lightning LoRA is essential** — Without it, you need 20+ steps and results may still be inconsistent. The Lightning LoRA distills the model to 4-step generation while maintaining quality.

4. **Pixel offset without lenML** — The built-in ComfyUI TextEncodeQwenImageEdit applies forced scaling that shifts pixel positions. lenML's TextEncodeQwenImageEditAdv separates scaling from encoding and fixes this.

5. **GGUF over safetensors** — Qwen models load faster and use less VRAM in GGUF format. The UnetLoaderGGUF node loads them directly. If using safetensors, CheckpointLoaderSimple works but loads the full precision weights.

6. **Multi-image reference** — The node supports image1 through image10 inputs. More reference images improve editing accuracy. For identity transfer (e.g., making someone look like Macho Man), include 1-3 reference portraits.

7. **Workflow compatibility** — Workflows built for Qwen 2509 may not work with 2511 and vice versa. The CLIP type and model architecture differ. 2511 is the recommended version (better consistency, integrated LoRA support).

8. **Dual text-encoder pattern** — TextEncodeQwenImageEditAdv (lenML) provides POSITIVE + LATENT (2 outputs). A separate built-in TextEncodeQwenImageEdit provides NEGATIVE conditioning. Using only the lenML node with a 3-output assumption causes `tuple index out of range` in KSampler validation. The negative text encoder prompt should DESCRIBE what to remove/avoid.

9. **KSampler (Efficient) required inputs** — Standard KSampler lacks `denoise`, `preview_method`, and `vae_decode` inputs that KSampler (Efficient) requires. Set denoise=1, preview_method="none", vae_decode="false" when doing VAE decode separately. The lenML demo workflow uses KSampler (Efficient), not standard KSampler.

10. **CFGNorm required** — The model output must pass through a CFGNorm node (strength=1) before reaching the sampler. Without it, the GGUF-loaded model's conditioning format doesn't match what KSampler (Efficient) expects.

11. **ComfyUI restart required for new nodes** — After installing custom nodes via git clone, ComfyUI must be restarted (`systemctl --user restart comfyui.service`) for them to appear in the object_info registry. Verify with `curl http://localhost:8188/object_info | python3 -c "import sys,json; d=json.load(sys.stdin); print([k for k in d if 'TextEncodeQwen' in k])"`.

12. **Node name mismatch** — The lenML demo uses `LoaderGGUF` but the ComfyUI-GGUF node registers as `UnetLoaderGGUF`. Always verify node class_type against the server's `/api/object_info` before building workflows.

## Model Source URLs

All models available from HuggingFace. Key repos:
- `Comfy-Org/Qwen-Image-Edit_ComfyUI` (split repo, not gated) — diffusion models + LoRAs
- `lightx2v/Qwen-Image-Edit-2511-Lightning` (not gated, 252k downloads) — Lightning models
- `remudl/qwen-image-vae` (not gated) — VAE
- Community GGUF conversions for the GGUF format

The Comfy-Org repo is split-model — use wget for individual files (git-lfs glob patterns don't work).

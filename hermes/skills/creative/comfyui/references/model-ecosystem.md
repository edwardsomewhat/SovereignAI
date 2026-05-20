# ComfyUI Model Ecosystem — Canonical URLs

This doc maps every model family to its correct HuggingFace repo and
filename. Use this instead of searching — many models are in
non-obvious repos (Comfy-Org repacks, community mirrors) and the
official repos are sometimes gated or incomplete.

---

## Flux.1 Dev (Stills — best quality on 24 GB)

| File | Repo | URL Notes |
|------|------|-----------|
| `flux1-dev-fp8.safetensors` | `Comfy-Org/flux1-dev` | Diffusion model only. **Use wget**, comfy-cli hangs on >1GB files. `wget -c -O models/checkpoints/flux1-dev-fp8.safetensors "https://huggingface.co/Comfy-Org/flux1-dev/resolve/main/flux1-dev-fp8.safetensors"` |
| `clip_l.safetensors` | `comfyanonymous/flux_text_encoders` | **Not in flux1-dev repo.** `comfy --skip-prompt model download --url "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors" --relative-path models/clip` |
| `t5xxl_fp8_e4m3fn.safetensors` | `comfyanonymous/flux_text_encoders` | ~4.56 GB fp8. Also available as `t5xxl_fp8_e4m3fn_scaled.safetensors` (smaller). **Use wget** for reliability. |
| `ae.safetensors` (VAE) | **Not `black-forest-labs`** — all BFL repos are gated now. Use `Kijai/flux-fp8` mirror: `flux-vae-bf16.safetensors` (~160 MB). `wget -c -O models/vae/ae.safetensors "https://huggingface.co/Kijai/flux-fp8/resolve/main/flux-vae-bf16.safetensors"` |

---

## Qwen Image Edit (Image Editing — pixel-accurate)

**Custom node:** `ComfyUI-PainterQwenImageEdit` (princepainter/ComfyUI-PainterQwenImageEdit on GitHub).
Includes a bundled workflow at `qwen_image_edit-2511.json`.

### Core models — `Comfy-Org/Qwen-Image-Edit_ComfyUI` (open, split-repo)

Clone with selective LFS:
```bash
cd models/
GIT_LFS_SKIP_SMUDGE=1 git clone https://huggingface.co/Comfy-Org/Qwen-Image-Edit_ComfyUI Qwen-Image-Edit
cd Qwen-Image-Edit
git lfs pull -I "split_files/diffusion_models/*2509*" -I "split_files/diffusion_models/*2511*" -I "split_files/loras/*2509*"
```

| Variant | Path |
|---------|------|
| Qwen 2509 bf16 | `split_files/diffusion_models/qwen_image_edit_2509_bf16.safetensors` |
| Qwen 2509 fp8 | `split_files/diffusion_models/qwen_image_edit_2509_fp8_e4m3fn.safetensors` |
| Qwen 2509 fp8 mixed | `split_files/diffusion_models/qwen_image_edit_2509_fp8mixed.safetensors` |
| Qwen 2511 bf16 | `split_files/diffusion_models/qwen_image_edit_2511_bf16.safetensors` |
| Qwen 2511 fp8 mixed | `split_files/diffusion_models/qwen_image_edit_2511_fp8mixed.safetensors` |

### 2511 LoRAs (all in same repo under `split_files/loras/`)

- `Qwen-Edit-2509-Multiple-angles.safetensors` — multi-angle product shots
- `Qwen-Image-Edit-2509-Anything2RealAlpha.safetensors` — realism boost
- `Qwen-Image-Edit-2509-Fusion.safetensors` — style blending
- `Qwen-Image-Edit-2509-Light-Migration.safetensors` — lighting transfer (key for product photos)
- `Qwen-Image-Edit-2509-Relight.safetensors` — relighting
- `Qwen-Image-Edit-2509-White_to_Scene.safetensors` — white bg → scene

### Qwen 2511 Lightning (distilled, 4-step) — `lightx2v/Qwen-Image-Edit-2511-Lightning` (open, split-repo)

```bash
cd models/
GIT_LFS_SKIP_SMUDGE=1 git clone https://huggingface.co/lightx2v/Qwen-Image-Edit-2511-Lightning Qwen-2511-Lightning
cd Qwen-2511-Lightning
git lfs pull -I "*Lightning-4steps-V1.0-bf16*" -I "*lightning_comfyui_4steps*"
```

Key files:
- `Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors` — what PainterQwen workflow expects
- `qwen_image_edit_2511_fp8_e4m3fn_scaled_lightning_comfyui_4steps_v1.0.safetensors` — ComfyUI-optimized fp8

### z_image_turbo — `Comfy-Org/z_image_turbo_ComfyUI` (split-repo)

Already installed if PainterQwen is working. Contains: diffusion model (bf16 + nvfp4), VAE, T5 text encoder (bf16/fp4/fp8), LoRA.

---

## Wan2.1 (Video — first/last-frame chaining)

**Custom nodes:** `ComfyUI-WanVideoWrapper`, `ComfyUI-WanVideoKsampler`, `ComfyUI-VideoHelperSuite`

**Models:** `Comfy-Org/Wan_2.1_ComfyUI_repackaged` (open, split-repo, 3.5M downloads)

```bash
cd models/
GIT_LFS_SKIP_SMUDGE=1 git clone https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged Wan2.1
cd Wan2.1
git lfs pull \
  -I "split_files/diffusion_models/*flf2v*fp8*" \
  -I "split_files/diffusion_models/*i2v*720p*fp8*" \
  -I "split_files/diffusion_models/*t2v*14B*fp8*" \
  -I "split_files/vae/*" \
  -I "split_files/text_encoders/umt5*fp8*"
```

**Key models for 24 GB (fp8):**

| Model | File | Use |
|-------|------|-----|
| **FLF2V 720p fp8** | `wan2.1_flf2v_720p_14B_fp8_e4m3fn.safetensors` | **First+Last frame → video** (CHAINING) |
| I2V 720p fp8 | `wan2.1_i2v_720p_14B_fp8_e4m3fn.safetensors` | Image → video |
| I2V 480p fp8 scaled | `wan2.1_i2v_480p_14B_fp8_scaled.safetensors` | Lighter I2V |
| T2V 14B fp8 | `wan2.1_t2v_14B_fp8_e4m3fn.safetensors` | Text → video |

**Video chaining workflow (FLF2V):**
1. Generate clip 1 with T2V
2. Extract last frame of clip 1
3. Generate clip 2 with FLF2V: first_frame=clip1_last, last_frame=desired_end
4. Concatenate with VideoHelperSuite
5. Repeat for clips 3+

Also includes: camera control (fun_camera), inpainting (fun_inp), VACE, alpha channel LoRA, InfiniteTalk model patches.

---

## LTX-Video (Fast Video — Lightricks)

**Custom node:** `ComfyUI-LTXVideo` (Lightricks/ComfyUI-LTXVideo, ⭐3.6k, in Manager registry)

**Models:** `Lightricks/LTX-Video` (open, non-split — single safetensors files)

```bash
cd models/
GIT_LFS_SKIP_SMUDGE=1 git clone https://huggingface.co/Lightricks/LTX-Video LTX-Video
cd LTX-Video
git lfs pull -I "*13b*0.9.8*distilled*fp8*" -I "*2b*0.9.8*distilled*fp8*"
```

**Key models for 24 GB:**

| Model | VRAM | Speed |
|-------|------|-------|
| `ltxv-13b-0.9.8-distilled-fp8.safetensors` | ~16 GB | Medium |
| `ltxv-2b-0.9.8-distilled-fp8.safetensors` | ~5 GB | Fast |

Also includes spatial/temporal upscalers (`ltxv-spatial-upscaler-0.9.8.safetensors`, `ltxv-temporal-upscaler-0.9.8.safetensors`).

---

## HunyuanVideo (Tencent)

**Custom node:** `ComfyUI-HunyuanVideoWrapper` (in Manager registry)

Models not covered yet — the Comfy-Org ecosystem is thinner for Hunyuan. The official Tencent repos may require auth. Wan2.1 and LTX cover the video use cases more fully.

---

## Gallery: All Custom Nodes by Category

**Video:** WanVideoWrapper, WanVideoKsampler, HunyuanVideoWrapper, LTXVideo, VideoHelperSuite

**Image editing:** PainterQwenImageEdit, Florence2, IPAdapter Plus, Essentials (rembg)

**Utility:** ControlNet Aux, Efficiency Nodes, rgthree-comfy, Manager

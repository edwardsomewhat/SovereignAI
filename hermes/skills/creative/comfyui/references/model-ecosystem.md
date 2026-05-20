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

**git-lfs is unreliable for HF split repos.** Clone for structure, then wget individual files:
```bash
cd models/
GIT_LFS_SKIP_SMUDGE=1 git clone https://huggingface.co/Comfy-Org/Qwen-Image-Edit_ComfyUI Qwen-Image-Edit
# wget each model you need — reliable and resumable
cd Qwen-Image-Edit
wget -c -O split_files/diffusion_models/qwen_image_edit_2509_fp8_e4m3fn.safetensors \
  "https://huggingface.co/Comfy-Org/Qwen-Image-Edit_ComfyUI/resolve/main/split_files/diffusion_models/qwen_image_edit_2509_fp8_e4m3fn.safetensors"
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

Clone for structure, then wget:
```bash
cd models/
GIT_LFS_SKIP_SMUDGE=1 git clone https://huggingface.co/lightx2v/Qwen-Image-Edit-2511-Lightning Qwen-2511-Lightning
cd Qwen-2511-Lightning
wget -c -O Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors \
  "https://huggingface.co/lightx2v/Qwen-Image-Edit-2511-Lightning/resolve/main/Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors"
```

Key files:
- `Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors` — what PainterQwen workflow expects
- `qwen_image_edit_2511_fp8_e4m3fn_scaled_lightning_comfyui_4steps_v1.0.safetensors` — ComfyUI-optimized fp8

### Qwen Image Edit support models (NOT in Comfy-Org repo)

The PainterQwen workflow (bundled in the custom node) references two support models that
are **NOT** in the `Comfy-Org/Qwen-Image-Edit_ComfyUI` repo. You need these for the full
Qwen Image Edit pipeline:

| File | Role | Source (TBD) |
|------|------|--------------|
| `qwen_2.5_vl_7b.safetensors` | CLIP/vision encoder (type: `qwen_image`) | Not yet located — may be in `Comfy-Org/z_image_turbo_ComfyUI` or Qwen official repos |
| `qwen_image_vae.safetensors` | VAE for Qwen Image Edit | Not yet located — z_image_turbo has a VAE but may differ |

The full Qwen Image Edit workflow node chain discovered from the bundled workflow:
1. `LoadImage` — input image(s), reference images
2. `CLIPLoader` — `qwen_2.5_vl_7b.safetensors`, type `qwen_image`
3. `UNETLoader` — `qwen_image_edit_2511_FP8.safetensors`, dtype `fp8_e4m3fn`
4. `VAELoader` — `qwen_image_vae.safetensors`
5. `LoraLoaderModelOnly` — Lightning LoRA (strength 1.0)
6. `ModelSamplingAuraFlow` — shift value 3
7. `PainterQwenImageEditPlus` — prompt, mode, images → conditioning + latent
8. `KSampler` — 4 steps (Lightning), 20-30 steps (non-Lightning)
9. `VAEDecode` — decode latent → image

The workflow bundles reference subfolder paths like `2025-12-23/qwen_image_edit_2511_FP8.safetensors`
and `2025-12-24/Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors` — these are
arbitrary date-based subfolders in the original author's setup. Create symlinks or place
models in the expected paths.

### Qwen utility nodes

- **Comfyui-QwenEditUtils** (in Manager registry) — additional Qwen Image Edit utilities
- The PainterQwenImageEditPlus node handles Qwen 2509/2511/Lightning models directly

### z_image_turbo — `Comfy-Org/z_image_turbo_ComfyUI` (split-repo)

Already installed if PainterQwen is working. Contains: diffusion model (bf16 + nvfp4), VAE, T5 text encoder (bf16/fp4/fp8), LoRA.

---

## Wan2.1 (Video — first/last-frame chaining)

**Custom nodes:** `ComfyUI-WanVideoWrapper`, `ComfyUI-WanVideoKsampler`, `ComfyUI-VideoHelperSuite`

**Models:** `Comfy-Org/Wan_2.1_ComfyUI_repackaged` (open, split-repo, 3.5M downloads)

Clone for structure, then wget individual files:
```bash
cd models/
GIT_LFS_SKIP_SMUDGE=1 git clone https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged Wan2.1
cd Wan2.1
# FLF2V — the key model for frame chaining
wget -c -O split_files/diffusion_models/wan2.1_flf2v_720p_14B_fp8_e4m3fn.safetensors \
  "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_flf2v_720p_14B_fp8_e4m3fn.safetensors"
# I2V 720p fp8
wget -c -O split_files/diffusion_models/wan2.1_i2v_720p_14B_fp8_e4m3fn.safetensors \
  "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_i2v_720p_14B_fp8_e4m3fn.safetensors"
# T2V 14B fp8
wget -c -O split_files/diffusion_models/wan2.1_t2v_14B_fp8_e4m3fn.safetensors \
  "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_t2v_14B_fp8_e4m3fn.safetensors"
# VAE
wget -c -O split_files/vae/wan_2.1_vae.safetensors \
  "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors"
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
# 13B distilled fp8 — best quality for 24 GB
wget -c -O ltxv-13b-0.9.8-distilled-fp8.safetensors \
  "https://huggingface.co/Lightricks/LTX-Video/resolve/main/ltxv-13b-0.9.8-distilled-fp8.safetensors"
# 2B distilled fp8 — ultrafast
wget -c -O ltxv-2b-0.9.8-distilled-fp8.safetensors \
  "https://huggingface.co/Lightricks/LTX-Video/resolve/main/ltxv-2b-0.9.8-distilled-fp8.safetensors"
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

**Audio:** comfyui-sound-lab, DJ_VideoAudioMixer, Jags_Audiotools (in Manager registry). For music generation (text-to-music), use the `audiocraft-audio-generation` skill (MusicGen). For TTS voiceovers, use Hermes' built-in text_to_speech tool (edge-TTS). Video models (Wan, LTX, Hunyuan) produce silent video; audio must be generated separately and mixed in.

**Post-download cleanup:** After wget downloads complete, remove git-lfs scaffolding from cloned repos to save disk and avoid confusion:

```bash
# Remove .git directories (no longer needed, wget files are alongside)
rm -rf models/Wan2.1/.git models/Qwen-Image-Edit/.git models/LTX-Video/.git models/Qwen-2511-Lightning/.git
# Remove LFS pointer files (tiny placeholders git-lfs left behind)
find models/ -name "*.safetensors" -size -1000c -delete
# Remove incomplete downloads
find models/ -name "*.part" -o -name "*.tmp" -delete
```

Then verify only real model files remain: `find models/ -name "*.safetensors" -size -1000c` should return nothing.

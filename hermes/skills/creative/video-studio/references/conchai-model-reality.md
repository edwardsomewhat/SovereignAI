# Conchai Model Reality Check

Verified May 27, 2026. Check with: `xxd MODEL.safetensors | head -1`

## Real Files (binary safetensors)

| Model | Path | Size | Used In |
|-------|------|------|---------|
| Kandinsky5 Lite I2V | `diffusion_models/kandinsky5lite_i2v_5s.safetensors` | 4.3 GB | I2V (proven) |
| Wan 2.2 I2V High Noise | `diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors` | 14 GB | I2V |
| Wan 2.2 I2V Low Noise | `diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors` | 14 GB | I2V |
| HunyuanVideo 1.5 I2V | `diffusion_models/hunyuanvideo1.5_720p_i2v_fp16.safetensors` | 16 GB | I2V |
| HunyuanVideo 1.5 SR | `diffusion_models/hunyuanvideo1.5_1080p_sr_distilled_fp16.safetensors` | 16 GB | Upscale |
| LTX-Video 2B | `LTX-Video/ltxv-2b-0.9.8-distilled-fp8.safetensors` | 4.2 GB | T2V draft |
| LTX-Video 13B | `LTX-Video/ltxv-13b-0.9.8-distilled-fp8.safetensors` | 15.7 GB | T2V |
| umt5 text encoder | `text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors` | — | Wan 2.1 T2V/I2V/FLF2V |
| Wan VAE | `vae/wan_2.1_vae.safetensors` | 243 MB | Wan decode |
| SDXL base | `checkpoints/sd_xl_base_1.0.safetensors` | 6.5 GB | Image generation |
| Flux Dev fp8 | `checkpoints/flux1-dev-fp8.safetensors` | 12 GB | Image generation |
| Juggernaut XL | `checkpoints/juggernautXL_ragnarokBy.safetensors` | 6.5 GB | Image generation |

## Git LFS Pointers (NOT real — need re-download)

| Model | Path | Expected | Fix |
|-------|------|----------|-----|
| Wan 2.1 T2V 14B | `Wan2.1/split_files/diffusion_models/wan2.1_t2v_14B_fp8_e4m3fn.safetensors` | 14 GB | Delete, `wget -c 'URL?download=1'` |
| Wan 2.1 I2V 720p 14B | `Wan2.1/split_files/diffusion_models/wan2.1_i2v_720p_14B_fp8_e4m3fn.safetensors` | 16 GB | Same |
| Wan 2.1 FLF2V 720p 14B | `Wan2.1/split_files/diffusion_models/wan2.1_flf2v_720p_14B_fp8_e4m3fn.safetensors` | 16 GB | Same |
| Wan split VAE | `Wan2.1/split_files/vae/wan_2.1_vae.safetensors` | 243 MB | Use the real one at `vae/wan_2.1_vae.safetensors` instead |
| Clip vision (split) | `Wan2.1/split_files/clip_vision/` | Empty dir | Use `clip_vision/CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors` |

## Symlinks Created

- `diffusion_models/wan2.1_t2v_14B_fp8_e4m3fn.safetensors` → split_files version (needed for UNETLoader)
- `diffusion_models/wan2.1_flf2v_720p_14B_fp8_e4m3fn.safetensors` → split_files version
- `clip_vision/clip_vision_h.safetensors` → `CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors` (for WanVideoWrapper)

## HuggingFace Source

Base URL: `https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/`

Fix command template:
```bash
rm MODEL.safetensors
wget -c 'https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/MODEL.safetensors?download=1' -O MODEL.safetensors
```

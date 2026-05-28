# Conchai ComfyUI Model Inventory

**Node:** conchai (100.69.153.16) — RTX 3090 24GB
**ComfyUI path:** `/mnt/hermes_data/comfy/`
**Snapshot date:** 2026-05-26
**Note:** This is a point-in-time snapshot. Models may have been added/removed since. If a model is missing, re-scan with the command below.

## Refresh Command

```bash
ssh conchai "cd /mnt/hermes_data/comfy && python3 -c \"
import os
for root, dirs, files in os.walk('models'):
    for f in files:
        if f.endswith(('.safetensors', '.ckpt', '.pt')):
            path = os.path.join(root, f)
            size = os.path.getsize(path)
            print(f'{os.path.relpath(root, \"models\"):40s} {size/(1024**3):5.1f}GB  {f}')
\"" | sort -t'/' -k1
```

## Full Inventory (as of snapshot)

### Checkpoints (txt2img base models)
| Model | Size | Notes |
|-------|------|-------|
| `flux1-dev-fp8.safetensors` | 16.1 GB | Flux Dev fp8, best quality |
| `juggernautXL_ragnarokBy.safetensors` | 6.6 GB | SDXL photorealism fine-tune |
| `sd_xl_base_1.0.safetensors` | 6.5 GB | SDXL base, general purpose |
| `photon_v1.safetensors` | 2.0 GB | SD 1.5, lightweight |
| `dreamshaper_8.safetensors` | 2.0 GB | SD 1.5, artistic |
| `epiCPhotoGasm_v2.safetensors` | 2.0 GB | SD 1.5, photo style |
| `epicrealism_naturalSinRC1VAE.safetensors` | 2.0 GB | SD 1.5, realism |

### UNET (diffusion backbones — Flux/video)
| Model | Size | Notes |
|-------|------|-------|
| `flux2_dev_fp8mixed.safetensors` | 33.0 GB | Flux 2 dev |
| `flux1-fill-dev.safetensors` | 22.2 GB | Flux Fill (inpainting) |
| `flux1-dev.safetensors` | 16.1 GB | Flux Dev fp16 |
| `fluxFillFP8_v10.safetensors` | 11.1 GB | Flux Fill fp8 |
| `qwen_image_edit_2511_fp8_e4m3fn.safetensors` | 19.1 GB | Qwen Image Edit |
| `qwen_image_edit_2511_fp8mixed.safetensors` | 19.1 GB | Qwen Image Edit (split) |
| `qwen_image_edit_2509_fp8_e4m3fn.safetensors` | 19.0 GB | Qwen Image Edit v1 |
| `z_image_bf16.safetensors` | 11.5 GB | Z Image |
| `z_image_turbo_bf16.safetensors` | 11.5 GB | Z Image Turbo |
| `z_image_turbo_nvfp4.safetensors` | 4.2 GB | Z Image Turbo nvfp4 |
| `iclight_sd15_fbc.safetensors` | 1.6 GB | IC-Light (background) |
| `iclight_sd15_fc.safetensors` | 1.6 GB | IC-Light (foreground) |
| `iclight_sd15_fcon.safetensors` | 1.6 GB | IC-Light (combined) |

### Video Models
| Model | Size | Notes |
|-------|------|-------|
| `hunyuanvideo1.5_1080p_sr_distilled_fp16.safetensors` | 15.5 GB | HunyuanVideo SR |
| `hunyuanvideo1.5_720p_i2v_fp16.safetensors` | 15.5 GB | HunyuanVideo I2V |
| `wan2.1_flf2v_720p_14B_fp8_e4m3fn.safetensors` | 15.3 GB | Wan 2.1 FLF2V |
| `wan2.1_i2v_720p_14B_fp8_e4m3fn.safetensors` | 15.3 GB | Wan 2.1 I2V |
| `wan2.1_t2v_14B_fp8_e4m3fn.safetensors` | 13.3 GB | Wan 2.1 T2V |
| `wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors` | 13.3 GB | Wan 2.2 I2V (low noise) |
| `wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors` | 13.3 GB | Wan 2.2 I2V (high noise) |
| `ltxv-13b-0.9.8-distilled-fp8.safetensors` | 14.6 GB | LTX-Video 13B |
| `ltxv-2b-0.9.8-distilled-fp8.safetensors` | 4.2 GB | LTX-Video 2B (light) |
| `kandinsky5lite_i2v_5s.safetensors` | 4.3 GB | Kandinsky Video (light) |

### CLIP / Text Encoders
| Model | Size | Notes |
|-------|------|-------|
| `t5xxl_fp16.safetensors` | 4.6 GB | T5 XXL (SDXL/Flux) |
| `t5xxl_fp8_e4m3fn.safetensors` | 4.6 GB | T5 XXL fp8 |
| `clip_l.safetensors` | 0.2 GB | CLIP-L (SDXL/Flux) |
| `mistral_3_small_flux2_fp8.safetensors` | 16.8 GB | Mistral 3 for Flux 2 |
| `qwen_2.5_vl_7b_fp8_scaled.safetensors` | 8.7 GB | Qwen 2.5 VL (vision LLM) |
| `qwen_3_4b.safetensors` | 7.5 GB | Qwen 3 4B |
| `qwen_3_4b_fp8_mixed.safetensors` | 5.2 GB | Qwen 3 4B fp8 |
| `qwen_3_4b_fp4_mixed.safetensors` | 3.2 GB | Qwen 3 4B fp4 |
| `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | 6.3 GB | UMT5 XXL |
| `byt5_small_glyphxl_fp16.safetensors` | 0.4 GB | ByT5 for Glyph |

### VAE
| Model | Size | Notes |
|-------|------|-------|
| `ae.safetensors` | 0.3 GB | Standard Flux VAE |
| `ae (1).safetensors` | 0.3 GB | Duplicate |
| `flux2-vae.safetensors` | 0.3 GB | Flux 2 VAE |
| `hunyuanvideo15_vae_fp16.safetensors` | 2.3 GB | HunyuanVideo VAE |
| `hunyuan_video_vae_bf16.safetensors` | 0.5 GB | HunyuanVideo VAE (bf16) |
| `wan_2.1_vae.safetensors` | 0.2 GB | Wan 2.1 VAE |
| `qwen_image_vae.safetensors` | 0.2 GB | Qwen Image VAE |

### ControlNet
| Model | Size | Notes |
|-------|------|-------|
| `Qwen-Image-InstantX-ControlNet-Inpainting.safetensors` | 3.9 GB | Qwen Inpainting CN |
| `Qwen-Image-InstantX-ControlNet-Union.safetensors` | 3.3 GB | Qwen Union CN |

### IP-Adapter / Style
| Model | Size | Notes |
|-------|------|-------|
| `ip-adapter.pt` | 4.9 GB | Flux IP-Adapter |
| `flux1-redux-dev.safetensors` | 0.1 GB | Flux Redux style |

### LoRAs
| Model | Size | Notes |
|-------|------|-------|
| `Qwen-Image-Edit-Lightning-8steps-V1.0.safetensors` | 1.6 GB | Qwen Edit fast |
| `Qwen-Image-Lightning-4steps-V1.0.safetensors` | 1.6 GB | Qwen Image fast |
| `Qwen-Image-Edit-2509-Lightning-8steps-V1.0-fp32.safetensors` | 1.6 GB | Qwen Edit v1 fast |
| `Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors` | 0.8 GB | Qwen Edit v2 fast |
| `Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors` | 0.8 GB | Qwen Edit v1 4-step |
| `wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors` | 1.1 GB | Wan 2.2 fast (high noise) |
| `wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors` | 1.1 GB | Wan 2.2 fast (low noise) |
| `Qwen-Image-Edit-2509-Anything2RealAlpha.safetensors` | 0.6 GB | Qwen realism |
| `Qwen-Image-Edit-2509-Fusion.safetensors` | 0.2 GB | Qwen fusion |
| `Qwen-Image-Edit-2509-Light-Migration.safetensors` | 0.2 GB | Qwen light migration |
| `Qwen-Edit-2509-Multiple-angles.safetensors` | 0.2 GB | Qwen multi-angle |
| `Qwen-Image-Edit-2509-Relight.safetensors` | 0.2 GB | Qwen relight |
| `Qwen-Image-Edit-2509-White_to_Scene.safetensors` | 0.2 GB | Qwen white→scene |
| `white_to_scene.safetensors` | 0.2 GB | Duplicate of above |
| `z_image_turbo_distill_patch_lora_bf16.safetensors` | 0.1 GB | Z Image Turbo LoRA |

### Vision / Detection
| Model | Size | Notes |
|-------|------|-------|
| `CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors` | 2.4 GB | CLIP ViT-H |
| `sigclip_vision_patch14_384.safetensors` | 0.8 GB | SigCLIP |
| `model.safetensors` (Florence-2-large) | 1.4 GB | Florence 2 vision |
| `sam2_hiera_large.pt` | 0.8 GB | SAM 2 large |
| `sam2_hiera_large.safetensors` | 0.8 GB | SAM 2 large (safetensors) |
| `sam2_hiera_small.safetensors` | 0.2 GB | SAM 2 small |

### Other
| Model | Size | Notes |
|-------|------|-------|
| `hunyuanvideo15_latent_upsampler_1080p.safetensors` | 0.2 GB | Hunyuan upscaler |

## VRAM Budget (3090 24GB)

| Workflow | Approximate VRAM | Fits? |
|----------|-----------------|-------|
| SD 1.5 (photon, dreamshaper) | ~4 GB | ✅ |
| SDXL base | ~8 GB | ✅ |
| Flux Dev fp8 + T5 fp8 | ~18 GB | ✅ (tight) |
| Flux Dev fp16 + T5 fp16 | ~22 GB | ✅ (very tight) |
| Flux 2 fp8mixed | ~24 GB | ⚠️ borderline |
| Wan 2.1 video | ~22 GB | ✅ (tight) |
| HunyuanVideo | ~22 GB | ✅ (tight) |
| Video + upscale | ~24 GB | ⚠️ borderline |

**Rule of thumb:** For video/Flux workflows, stop vLLM first. ComfyUI needs every GB.

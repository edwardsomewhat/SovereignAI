# Wan 2.1 FLF2V — Pipeline Reference

First-Last-Frame-to-Video using WanVideoWrapper nodes. As of May 2026, FLF2V requires the WanVideoWrapper custom node pack — native ComfyUI doesn't have a built-in FLF2V node.

## Model Verification

Before use, verify the model is NOT a Git LFS pointer:
```bash
xxd wan2.1_flf2v_720p_14B_fp8_e4m3fn.safetensors | head -1
# Binary hex = real, ASCII "version https://git-lfs..." = pointer
```

## Proven Minimal Pipeline (10 nodes)

```json
{
  "1": {"class_type": "WanVideoModelLoader", "inputs": {"model": "wan2.1_flf2v_720p_14B_fp8_e4m3fn.safetensors", "base_precision": "bf16", "quantization": "fp8_e4m3fn", "load_device": "offload_device"}},
  "2": {"class_type": "WanVideoVAELoader", "inputs": {"model_name": "wan_2.1_vae.safetensors", "precision": "bf16"}},
  "3": {"class_type": "LoadImage", "inputs": {"image": "start_frame.png"}},
  "4": {"class_type": "LoadImage", "inputs": {"image": "end_frame.png"}},
  "5": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "clip_vision_h.safetensors"}},
  "6": {"class_type": "WanVideoClipVisionEncode", "inputs": {"clip_vision": ["5", 0], "image_1": ["3", 0], "strength_1": 1.0, "image_2": ["4", 0], "strength_2": 1.0, "crop": "center", "combine_embeds": "concat", "force_offload": true}},
  "7": {"class_type": "WanVideoImageToVideoEncode", "inputs": {"width": 832, "height": 480, "num_frames": 41, "noise_aug_strength": 0.0, "start_latent_strength": 1.0, "end_latent_strength": 1.0, "force_offload": true, "vae": ["2", 0], "clip_embeds": ["6", 0], "start_image": ["3", 0], "end_image": ["4", 0], "fun_or_fl2v_model": true}},
  "8": {"class_type": "WanVideoSampler", "inputs": {"model": ["1", 0], "image_embeds": ["7", 0], "steps": 15, "cfg": 5.0, "shift": 5.0, "seed": 42, "force_offload": true, "scheduler": "unipc", "riflex_freq_index": 0}},
  "9": {"class_type": "WanVideoDecode", "inputs": {"vae": ["2", 0], "samples": ["8", 0], "enable_vae_tiling": false}},
  "10": {"class_type": "VHS_VideoCombine", "inputs": {"images": ["9", 0], "frame_rate": 24.0, "filename_prefix": "flf2v_out", "format": "video/h264-mp4"}}
}
```

## Node Notes

### WanVideoModelLoader
- `model`: must be the exact filename. The loader scans `models/diffusion_models/` — symlink if the file is in a subdirectory.
- `base_precision`: "bf16" recommended
- `quantization`: use "fp8_e4m3fn" for 14B fp8 models
- `load_device`: "offload_device" saves VRAM

### WanVideoVAELoader
- **CRITICAL**: must include `precision` parameter even though object_info says it's optional. Without it: `loadmodel() missing 1 required positional argument: 'precision'`
- Use `"precision": "bf16"`

### WanVideoClipVisionEncode
- Takes `image_1` and `image_2` (start and end frames)
- `combine_embeds`: "concat" for FLF2V (both frames needed)
- `strength_1/2`: 1.0 for full frame influence
- Outputs a single `WANVIDIMAGE_CLIPEMBEDS` containing both image embeddings

### WanVideoImageToVideoEncode
- `fun_or_fl2v_model: true` — tells the node this is an FLF2V model
- Takes `start_image` and `end_image` as OPTIONAL inputs (no SetNode/GetNode needed)
- Takes `clip_embeds` from WanVideoClipVisionEncode
- `num_frames`: 41 for ~1.7 seconds at 24fps (faster for testing). Increase to 81 for ~3.4 seconds.

### WanVideoSampler
- `image_embeds` from WanVideoImageToVideoEncode
- `text_embeds` is OPTIONAL — skip for faster generation unless quality needs text guidance
- 15-20 steps at cfg 5.0 is a good starting point for FLF2V

### CLIP Vision Model
On Conchai: `CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors` is symlinked to `clip_vision_h.safetensors` in `models/clip_vision/`.

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `loadmodel() missing precision` | VAE loader needs explicit precision | Add `"precision": "bf16"` to WanVideoVAELoader |
| `invalid tokenizer` | Wrong CLIP loader or wrong text encoder | Check CLIPLoader `type` and `clip_name` |
| `return_type_mismatch: LATENT ≠ WANVIDIMAGE_EMBEDS` | Wrong node output connected to sampler | Connect image_embeds from WanVideoImageToVideoEncode output[0], not the latent output |
| Model not loading / UTF-8 error | LFS pointer file | See model verification section above |
| Job hangs >15 min | FLF2V is slow with high frame counts | Reduce num_frames (41 for testing) and steps (15) |

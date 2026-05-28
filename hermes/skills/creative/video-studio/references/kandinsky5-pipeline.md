# Kandinsky5 Lite I2V — Proven Pipeline

Proven May 27, 2026 on Conchai RTX 3090, ComfyUI 0.21.1.

## Performance
- **Model:** `kandinsky5lite_i2v_5s.safetensors` (4.3 GB, real file)
- **Generation time:** ~3 minutes for 61 frames at 768×512
- **Output:** MP4 via VHS_VideoCombine, ~100 KB

## API-Format Workflow

```json
{
  "1": {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": "clip_l.safetensors", "clip_name2": "qwen_2.5_vl_7b_fp8_scaled.safetensors", "type": "kandinsky5_image"}},
  "2": {"class_type": "UNETLoader", "inputs": {"unet_name": "kandinsky5lite_i2v_5s.safetensors", "weight_dtype": "default"}},
  "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
  "4": {"class_type": "LoadImage", "inputs": {"image": "YOUR_IMAGE.png"}},
  "5": {"class_type": "CLIPTextEncodeKandinsky5", "inputs": {"clip": ["1", 0], "clip_l": "cinematic panning shot, smooth motion", "qwen25_7b": "Generate video with gentle camera movement"}},
  "6": {"class_type": "CLIPTextEncodeKandinsky5", "inputs": {"clip": ["1", 0], "clip_l": "blurry, static, ugly", "qwen25_7b": "blurry, low quality"}},
  "7": {"class_type": "Kandinsky5ImageToVideo", "inputs": {"positive": ["5", 0], "negative": ["6", 0], "vae": ["3", 0], "width": 768, "height": 512, "length": 61, "batch_size": 1, "start_image": ["4", 0]}},
  "8": {"class_type": "KSampler", "inputs": {"seed": 42, "steps": 20, "cfg": 5.0, "sampler_name": "uni_pc", "scheduler": "simple", "denoise": 1.0, "model": ["2", 0], "positive": ["7", 0], "negative": ["7", 1], "latent_image": ["7", 2]}},
  "9": {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}},
  "10": {"class_type": "VHS_VideoCombine", "inputs": {"images": ["9", 0], "frame_rate": 25.0, "loop_count": 0, "filename_prefix": "k5_out", "format": "video/h264-mp4"}}
}
```

## Critical Constraints

### Frame count (length)
Kandinsky5 latent constraint: the model expects exactly 16 latent frames.
Formula: `latent_frames = (length - 1) / 4 + 1`

| length | latent_frames | Works? |
|--------|---------------|--------|
| 61 | 16 | ✅ CORRECT |
| 121 | 31 | ❌ Tensor mismatch error |
| 49 | 13 | ❌ Wrong frame count |

**Always use `length: 61`** for standard Kandinsky5 I2V generation.

### Resolution
Default 768×512 works. Other tested resolutions: 832×480 (needs matching image dimensions).

### CLIP loader
Uses `DualCLIPLoader` with `type: "kandinsky5_image"` and two CLIP models:
- `clip_l.safetensors` — standard CLIP-L
- `qwen_2.5_vl_7b_fp8_scaled.safetensors` — Qwen 2.5 VL 7B

### VAE
Uses standard SDXL VAE (`ae.safetensors`), not the Wan VAE.

## Error Recovery

| Error | Cause | Fix |
|-------|-------|-----|
| `expanded size of tensor (31) must match (16)` | Wrong `length` parameter | Use `length: 61` |
| Node not found | Missing custom node | All Kandinsky5 nodes are built-in to ComfyUI >= 0.21 |
| Model not found | LFS pointer | Verify with `xxd` — file is real on Conchai |

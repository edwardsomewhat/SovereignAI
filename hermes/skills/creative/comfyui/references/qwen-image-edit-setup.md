# Qwen Image Edit — Working Pipeline (May 2026)

## The Pipeline That Works

After 10+ failed attempts with GGUF, Lightning LoRA, lenML nodes, and KSampler (Efficient), the simple pipeline is what produces photorealistic results:

### Models Required
- `qwen_image_edit_2511_fp8mixed.safetensors` — in `models/checkpoints/` (flat safetensors, NOT split_files)
- `qwen_2.5_vl_7b_fp8_scaled.safetensors` — in `models/clip/` (8.8GB)
- `qwen_image_vae.safetensors` — in `models/vae/` (243MB)

### Custom Nodes Required
- `ComfyUi-TextEncodeQwenImageEditAdvanced` — provides `TextEncodeEditAdvancedDual` node
- `ComfyUI_QwenVL` — Qwen VL integration

### Canonical Workflow (API Format)
```json
{
  "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "qwen_image_edit_2511_fp8mixed.safetensors"}},
  "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors", "type": "qwen_image"}},
  "3": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
  "4": {"class_type": "LoadImage", "inputs": {"image": "input_image.png"}},
  "5": {"class_type": "TextEncodeEditAdvancedDual", "inputs": {
    "image1": ["4", 0],
    "clip": ["2", 0],
    "positive": "edit description here",
    "negative": "what to avoid",
    "vl_megapixels": 1.0,
    "max_images_allowed": "1"
  }},
  "6": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
  "7": {"class_type": "KSampler", "inputs": {
    "model": ["1", 0],
    "positive": ["5", 0],
    "negative": ["5", 1],
    "latent_image": ["6", 0],
    "seed": 42, "steps": 15, "cfg": 6,
    "sampler_name": "euler", "scheduler": "normal",
    "denoise": 0.5
  }},
  "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
  "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "qwen_edit", "images": ["8", 0]}}
}
```

## Key Settings
- **Loader**: `CheckpointLoaderSimple` (NOT UNETLoader, NOT UnetLoaderGGUF)
- **CLIP type**: `qwen_image` (NOT `stable_diffusion`)
- **denoise**: 0.4–0.5 for edits that preserve original composition. Higher values (0.85) give the model too much freedom and can produce completely unrelated outputs.
- **Steps**: 15. Higher steps don't improve quality meaningfully.
- **CFG**: 6. Standard value, works well.
- **Latent source**: `EmptyLatentImage` (NOT VAE-encoded input image). Qwen generates its own latent from the prompt + reference image via TextEncodeEditAdvancedDual.

## What DOESN'T Work (Tested and Failed)

| Approach | Result | Why |
|----------|--------|-----|
| GGUF model (UnetLoaderGGUF) | 8-bit retro pixel art | Quantization degrades Qwen's output to pixelation |
| Lightning LoRA (4-step) | Pixelated output | LoRA incompatible with some Qwen model versions |
| lenML TextEncodeQwenImageEditAdv | Wrong wiring | Needs model input that doesn't exist; different output indices |
| KSampler (Efficient) | Validation errors | Needs CFGNorm, optional_vae, vae_decode, preview_method |
| UNETLoader with fp8 safetensors | Pixelated output | UNETLoader doesn't handle Qwen's conditioning the same way |
| denoise > 0.7 | Unrelated output | Too much freedom; model generates new scenes instead of editing |

## Multi-Image Reference Editing\n\nTextEncodeEditAdvancedDual supports up to 3 reference images via `image1`, `image2`, `image3` inputs. This is the recommended way to transfer identity — provide the actual person/object photo as a second image:\n\n```json\n\"5\": {\"class_type\": \"TextEncodeEditAdvancedDual\", \"inputs\": {\n  \"image1\": [\"4\", 0],   // the image to edit\n  \"image2\": [\"5\", 0],   // the reference photo to match\n  \"max_images_allowed\": \"2\",\n  \"vl_megapixels\": 1.0,\n  ...\n}}\n```\n\nThen prompt: \"make image1 look exactly like the person in image2. match their face, hair, and features precisely.\"\n\n**Important**: `max_images_allowed` must match the number of images wired. Available values: \"0\", \"1\", \"2\", \"3\". The image input names are `image1`, `image2`, `image3` (NOT `image`).\n\n## Qwen VL Limitations
The Qwen vision-language model interprets text literally. It has NO pop-culture knowledge. Examples:
- "macho man" → Spanish "masculine man" → sombreros and mariachi
- "wizard" is understood generically
- Celebrity names are not recognized

**Solution**: Use reference images (IPAdapter) for identity transfer rather than text descriptions of specific people.

## Model Source
- All three models (checkpoint, CLIP, VAE) can be found in existing Windows ComfyUI builds under `models/checkpoints/`, `models/clip/`, and `models/vae/`
- The Comfy-Org split repo (`Comfy-Org/Qwen-Image-Edit_ComfyUI`) contains the diffusion models and LoRAs in split_files format, but NOT the CLIP or VAE

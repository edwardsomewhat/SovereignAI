# Birefnet Auto-Masking + Inpainting Pipeline

Proven workflow for product compositing on Conchai ComfyUI v0.21.1.

## Pipeline Steps

```
LoadImage → BiRefNet_Loader → BiRefNet_Remove_Background → SplitImageWithAlpha → InvertMask → VAEEncodeForInpaint → KSampler → VAEDecode → SaveImage
```

## Node Details

| Node | Class Type | Key Inputs | Notes |
|------|-----------|------------|-------|
| LoadImage | LoadImage | `image: "filename.jpg"` | Must be uploaded first via `/upload/image` |
| Birefnet loader | BiRefNet_Loader | `model_version: "BiRefNet_lite"`, `device: "cuda"` | Use "BiRefNet_lite" for speed, "BiRefNet" for quality. NOT "General" — doesn't exist. |
| Background removal | BiRefNet_Remove_Background | `model`, `image`, `background_color: "black"`, `use_refine: True` | Outputs RGBA image |
| Split alpha | SplitImageWithAlpha | `image` (from BiRefNet output) | Outputs `[0]`=RGB image, `[1]`=alpha mask |
| Invert mask | InvertMask | `mask` (from SplitImageWithAlpha[1]) | NOT "MaskInvert" — that node doesn't exist |
| Encode for inpaint | VAEEncodeForInpaint | `pixels` (original image), `vae`, `mask` (inverted), `grow_mask_by: 2` | Grow by 2px to prevent edge artifacts |
| Checkpoint | CheckpointLoaderSimple | `ckpt_name: "juggernautXL_ragnarokBy.safetensors"` | SDXL for inpainting |
| Prompt encode x2 | CLIPTextEncode | Positive + negative prompts | Describe the NEW background, not the product |
| Sample | KSampler | `denoise: 1.0`, `steps: 30`, `cfg: 7.5`, `dpmpp_2m`/`karras` | denoise 1.0 = full background regeneration |
| Decode | VAEDecode | Samples → vae | |
| Save | SaveImage | Prefix for output files | |

## Critical Pitfalls

1. **InvertMask vs MaskInvert** — `InvertMask` is the correct node name. `MaskInvert` returns "node not found".
2. **BiRefNet model_version** — Must be an exact string from: `BiRefNet`, `BiRefNet_HR`, `BiRefNet_lite`, `BiRefNet_lite-2K`, `BiRefNet_512x512`, `BiRefNet-matting`, `BiRefNet_HR-Matting`, `BiRefNet-portrait`, `BiRefNet-DIS5K`, `BiRefNet-HRSOD`, `BiRefNet-COD`, `BiRefNet-DIS5K-TR_TEs`, `BiRefNet-legacy`. "General" is not valid.
3. **Mask direction** — Birefnet outputs white=product, black=background. Inpainting expects white=regenerate, black=keep. ALWAYS invert.
4. **grow_mask_by** — Set to 2-4px to avoid edge artifacts where old background bleeds through.
5. **Small products on textured backgrounds** — Birefnet may fail to cleanly segment small or translucent objects against textured backgrounds (e.g., glass on foam). For these cases, use Florence 2 on Nano-box (Coral TPU) for more accurate object-specific segmentation masks.

## Testing Notes

- Tested successfully on Conchai ComfyUI v0.21.1 with JuggernautXL
- Pipeline submission accepted, monitored, and downloaded in ~15 seconds
- Use `denoise: 1.0` for complete background replacement
- Lower denoise (0.5-0.7) blends old and new — useful for gradual transitions

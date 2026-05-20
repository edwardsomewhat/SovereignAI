# Split/Sharded Model Download

Some Comfy-Org HuggingFace models ship as split/sharded safetensors files
rather than single files. These cannot be downloaded via `comfy model download --url`.

## Detection

Check the repo's file list:
```bash
curl -s "https://huggingface.co/api/models/Comfy-Org/REPO_NAME" | python3 -c "
import sys,json
for s in json.load(sys.stdin).get('siblings',[]):
    if '.safetensors' in s.get('rfilename',''):
        print(s['rfilename'])"
```

If files are under `split_files/` directories, it's a split model.

## Download Recipe

```bash
cd ComfyUI/models

# 1. Clone WITHOUT pulling LFS blobs (repo structure only, seconds)
GIT_LFS_SKIP_SMUDGE=1 git clone https://huggingface.co/Comfy-Org/REPO_NAME local_name

# 2. Selectively pull only the variants you need (saves 30-80 GB)
cd local_name
git lfs pull \
  -I "split_files/diffusion_models/*fp8*" \
  -I "split_files/vae/*" \
  -I "split_files/text_encoders/umt5*fp8*"

# 3. Verify weights are real (not 136-byte LFS pointers)
python3 -c "
import os
for f in os.listdir('split_files/diffusion_models'):
    sz = os.path.getsize(f'split_files/diffusion_models/{f}')
    print(f'{\"REAL\" if sz > 1e6 else \"LFS_PTR\"} {sz/1e9:.1f}GB {f}')
"
```

**Why selective pull?** Many Comfy-Org repos ship bf16, fp16, fp8, fp4, nvfp4,
and GGUF variants of the same model as separate LFS objects. Pulling
everything wastes 50-150 GB. Target only the precision your GPU can run.

The `-I` flag accepts glob patterns. Multiple `-I` flags pull disjoint
subsets. Skip `git lfs pull` entirely if you only need JSON workflow files
(e.g., Qwen-Image-Edit's bundled workflow lives in the git tree, not LFS).

## Known Split Repos

- `Comfy-Org/z_image_turbo` — Z-Image Turbo (~12 GB, bf16 + nvfp4 variants)
- `Comfy-Org/Qwen-Image-Edit_ComfyUI` — Qwen Image Edit 2509/2511 + 6 LoRAs
- `Comfy-Org/Wan_2.1_ComfyUI_repackaged` — Wan2.1 video (FLF2V, I2V, T2V, 14 models)
- `Lightricks/LTX-Video` — LTX-Video 2B + 13B (also split, multiple precision variants)
- `lightx2v/Qwen-Image-Edit-2511-Lightning` — Qwen 2511 Lightning 4/8-step
- `comfyanonymous/flux_text_encoders` — Flux CLIP-L + T5 (NOT split, single files — but NOT in Comfy-Org/flux1-dev)

## Workflow Integration

Split models are loaded via the standard `CheckpointLoaderSimple` node
using the path to the diffusion model safetensors file, e.g.:
`z_image_turbo/split_files/diffusion_models/z_image_turbo_bf16.safetensors`

Text encoders and VAE are in sibling `split_files/` directories and may
need separate loader nodes depending on the workflow.

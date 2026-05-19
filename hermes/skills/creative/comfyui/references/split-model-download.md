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

# 1. Clone the repo (git LFS pointers only)
git clone https://huggingface.co/Comfy-Org/REPO_NAME local_name

# 2. Install git-lfs if not present
sudo apt-get install -y git-lfs
git lfs install

# 3. Pull actual weights (10-20 GB, slow)
cd local_name && git lfs pull

# 4. Verify weights are real (not 136-byte LFS pointers)
ls -lh split_files/diffusion_models/*.safetensors
```

## Known Split Repos

- `Comfy-Org/z_image_turbo` — Z-Image Turbo (~12 GB, bf16 + fp4 variants)
- `Comfy-Org/Qwen-Image-Edit_ComfyUI` — Qwen Image Edit 2509 + 2511 (~16 GB, plus LoRAs)

## Workflow Integration

Split models are loaded via the standard `CheckpointLoaderSimple` node
using the path to the diffusion model safetensors file, e.g.:
`z_image_turbo/split_files/diffusion_models/z_image_turbo_bf16.safetensors`

Text encoders and VAE are in sibling `split_files/` directories and may
need separate loader nodes depending on the workflow.

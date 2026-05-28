---
name: jetson-vision-pipeline
description: Set up PyTorch, torchvision, and vision models (Florence 2, etc.) on NVIDIA Jetson Orin / JetPack 6. Covers CUDA torch compatibility, dependency resolution, and model-specific workarounds. Use when deploying vision models to Jetson edge devices, troubleshooting torch/torchvision import errors, or setting up a vision inference server on Orin Nano.
---

# Jetson Vision Pipeline

Set up CUDA-accelerated PyTorch + torchvision + vision models on NVIDIA Jetson Orin (JetPack 6.x). This is the recipe that works — the ecosystem is fragile; follow the exact versions.

## Quick Reference

| Component | Working Version | Notes |
|-----------|----------------|-------|
| JetPack | 6.0/6.1 (R36.x) | CUDA 12.6 |
| PyTorch | 2.5.0 nv24.08 | NVIDIA wheel, NOT PyPI |
| Torchvision | 0.19.1 | Build from source with setuptools==69.5.1 |
| Transformers | 4.48.3 | 5.0 breaks; 4.44 has flash_attn check |
| NumPy | <2.0 (1.26.4) | torch 2.5 compiled against NumPy 1.x |
| setuptools | 69.5.1 | Required to build torchvision from source |

## Bundled Files

- `references/error-transcripts.md` — every error hit during setup, exact messages, and the fix for each
- `scripts/test_florence.py` — runnable Florence 2 inference test script (includes monkey-patches)

## Step 1: Install CUDA PyTorch

Use the NVIDIA-provided wheel for JetPack 6. The PyPI torch is CPU-only — skip it.

```bash
# Uninstall any existing torch/torchvision first
pip3 uninstall -y torch torchvision

# Install NVIDIA CUDA torch for JetPack 6
pip3 install --user --no-cache \
  'https://developer.download.nvidia.com/compute/redist/jp/v61/pytorch/torch-2.5.0a0+872d972e41.nv24.08.17622132-cp310-cp310-linux_aarch64.whl'
```

The `libcusparseLt.so.0` library must be present. If missing, install cusparselt:

```bash
# Download and install cusparselt (requires sudo for cp/ldconfig)
CUSPARSELT_URL="https://developer.download.nvidia.com/compute/cusparselt/redist/libcusparse_lt/linux-aarch64"
CUSPARSELT_VERSION="0.7.1.0"
CUSPARSELT_NAME="libcusparse_lt-linux-aarch64-${CUSPARSELT_VERSION}-archive"
cd /tmp
curl -OLs "${CUSPARSELT_URL}/${CUSPARSELT_NAME}.tar.xz"
tar xf "${CUSPARSELT_NAME}.tar.xz"
sudo cp -a "${CUSPARSELT_NAME}/include/"* /usr/local/cuda/include/
sudo cp -a "${CUSPARSELT_NAME}/lib/"* /usr/local/cuda/lib64/
sudo ldconfig
```

Verify CUDA works:
```python
import torch
print(torch.cuda.is_available())  # Must be True
```

## Step 2: Build Torchvision from Source

**Do NOT install torchvision from PyPI** — the manylinux aarch64 wheel is compiled against a different torch ABI and will fail with `operator torchvision::nms does not exist`.

The fix: pin setuptools to 69.5.1, then build torchvision 0.19.1 from source.

```bash
pip3 install --user 'setuptools==69.5.1' cython wheel

# Clone and build torchvision 0.19.1
cd /tmp
git clone --branch v0.19.1 --depth 1 https://github.com/pytorch/vision vision
cd vision
pip3 install --user --no-build-isolation .

# Verify
python3 -c 'import torchvision; print(torchvision.__version__)'
```

Pitfall: setuptools ≥70 or ≤68 will fail with `canonicalize_version() got an unexpected keyword argument 'strip_trailing_zero'`. Do not vary the setuptools version.

## Step 3: NumPy Pin

The NVIDIA torch 2.5 wheel is compiled against NumPy 1.x. PyPI torchvision pulls NumPy 2.x as a dependency. Pin it:

```bash
pip3 install --user 'numpy<2'
```

## Step 4: Install Transformers

Pin to 4.48.3 — the exact version matters:
- **5.0+**: breaks Florence 2's `trust_remote_code` (forced_bos_token_id AttributeError)
- **4.44.x**: has rigid `check_imports` that blocks on `flash_attn` even in conditional blocks
- **4.48.3**: works with monkey-patches (see Step 5)

```bash
pip3 install --user transformers==4.48.3
```

After switching transformers versions, ALWAYS clear the HF cache to avoid stale model code:
```bash
rm -rf ~/.cache/huggingface/modules/transformers_modules/microsoft/Florence*
```

## Step 5: FSDP/DeepSpeed Monkey-Patches

The NVIDIA Jetson torch wheel does NOT include `torch.distributed`. HuggingFace `generate()` calls `is_fsdp_managed_module()` and `is_deepspeed_zero3_enabled()` which import `torch.distributed.fsdp`. Patch them BEFORE importing transformers:

```python
import transformers.integrations.deepspeed as _ds
_ds.is_deepspeed_zero3_enabled = lambda: False

import transformers.integrations.fsdp as _fsdp
_fsdp.is_fsdp_managed_module = lambda m: False

# Now safe to import transformers
from transformers import AutoProcessor, AutoModelForCausalLM
```

Put these patches at the top of your inference script, before ANY transformers import.

## Step 6: Florence 2 — Known Working Recipe

```python
import torch
import transformers.integrations.deepspeed as _ds
_ds.is_deepspeed_zero3_enabled = lambda: False
import transformers.integrations.fsdp as _fsdp
_fsdp.is_fsdp_managed_module = lambda m: False

from transformers import AutoProcessor, AutoModelForCausalLM
from PIL import Image

model = AutoModelForCausalLM.from_pretrained(
    "microsoft/Florence-2-base",
    torch_dtype=torch.float16,
    trust_remote_code=True,
).to("cuda")

processor = AutoProcessor.from_pretrained(
    "microsoft/Florence-2-base",
    trust_remote_code=True,
)

# Inference
img = Image.open("image.jpg")
inputs = processor(text="<DETAILED_CAPTION>", images=img, return_tensors="pt").to("cuda", torch.float16)
ids = model.generate(
    input_ids=inputs["input_ids"],
    pixel_values=inputs["pixel_values"],
    max_new_tokens=256,
    num_beams=3,
)
text = processor.batch_decode(ids, skip_special_tokens=False)[0]
result = processor.post_process_generation(text, task="<DETAILED_CAPTION>", image_size=(img.width, img.height))
```

### Performance (Orin Nano 8GB)
| Metric | Value |
|--------|-------|
| Load time | ~3.7s |
| VRAM used | ~2.4GB |
| CAPTION | ~1.7s |
| DETAILED_CAPTION | ~1.3s |
| MORE_DETAILED_CAPTION | ~2.2s |

### Task Prompts
- `<CAPTION>` — short, single-sentence caption
- `<DETAILED_CAPTION>` — paragraph-level description
- `<MORE_DETAILED_CAPTION>` — exhaustive description
- `<OD>` — object detection with bounding boxes
- `<OCR>` — optical character recognition
- `<REGION_TO_DESCRIPTION>` — describe a specific region

## Package Index DNS Quirks

NVIDIA Jetson community wheels are hosted across domains that don't all resolve from Jetson devices:

| Domain | Resolves? | Notes |
|--------|-----------|-------|
| `pypi.jetson-ai-lab.io` | ✅ Yes | JetPack 6 pip index |
| `pypi.jetson-ai-lab.dev` | ❌ NXDOMAIN | Dead domain |
| `jetson.webredirect.org` | ✅ Yes | Redirects to .dev (dead) |
| `pypi.jetson-ai-lab.com` | ❌ NXDOMAIN | Dead domain |

Use `.io` for pip `--extra-index-url`. Do not rely on `jetson.webredirect.org` — it chains to non-resolving domains.

## Coral TPU Setup (WIP)

The Coral TPU appears at `/dev/apex_0` on Jetson Orin via PCIe/M.2. `libedgetpu1-std` is installed via apt but `pycoral` Python bindings are NOT yet installed. Full Coral setup TBD — see `references/coral-notes.md` when available.

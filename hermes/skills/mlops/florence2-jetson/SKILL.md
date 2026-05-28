---
name: florence2-jetson
description: "Deploy Florence-2-base on NVIDIA Jetson Orin (JetPack 6 / R36) with CUDA. Handles the notorious torch+torchvision compatibility matrix, monkey-patches for missing distributed modules, and provides a working inference script."
version: 1.0.0
compatibility: "Jetson Orin Nano/NX/AGX, JetPack 6.x (R36), Python 3.10, CUDA 12.6"
---

# Florence 2 on Jetson Orin (JetPack 6)

Deploy Microsoft Florence-2-base vision model on Jetson Orin with CUDA acceleration.

## The Dependency Hell (Why This Skill Exists)

Jetson's NVIDIA PyTorch build is ABI-incompatible with every PyPI torchvision wheel. The
`torchvision::nms does not exist` error is the signature of this mismatch. This skill
captures the exact working combination discovered through hours of trial and error.

## Working Version Matrix

| Component | Version | Source |
|-----------|---------|--------|
| JetPack | 6.x (R36) | NVIDIA SDK Manager |
| CUDA | 12.6 | Included in JetPack |
| PyTorch | 2.5.0a0+872d972e41.nv24.08 | NVIDIA redist wheel |
| Torchvision | 0.19.1a0+6194369 | Built from source (v0.19.1 tag) |
| Transformers | 4.48.3 | PyPI |
| NumPy | <2.0 (1.26.4 tested) | PyPI |
| setuptools | 69.5.1 | PyPI (CRITICAL for torchvision build) |
| PIL/Pillow | >=10.0 | PyPI |

## Step 1: Install System Dependencies

```bash
# cusparselt (required by NVIDIA torch)
cd /tmp
curl -OLs https://developer.download.nvidia.com/compute/cusparselt/redist/libcusparse_lt/linux-aarch64/libcusparse_lt-linux-aarch64-0.7.1.0-archive.tar.xz
tar xf libcusparse_lt-linux-aarch64-0.7.1.0-archive.tar.xz
sudo cp -a libcusparse_lt-linux-aarch64-0.7.1.0-archive/include/* /usr/local/cuda/include/
sudo cp -a libcusparse_lt-linux-aarch64-0.7.1.0-archive/lib/* /usr/local/cuda/lib64/
sudo ldconfig
```

## Step 2: Install NVIDIA CUDA PyTorch

```bash
pip3 install --user --no-cache \
  'https://developer.download.nvidia.com/compute/redist/jp/v61/pytorch/torch-2.5.0a0+872d972e41.nv24.08.17622132-cp310-cp310-linux_aarch64.whl'
```

Verify: `python3 -c "import torch; print(torch.cuda.is_available())"` → must be `True`

## Step 3: Build Torchvision from Source

```bash
# MUST use setuptools 69.5.1 (newer versions break the build)
pip3 install --user 'setuptools==69.5.1' cython 'numpy<2'

cd /tmp
git clone --branch v0.19.1 --depth 1 https://github.com/pytorch/vision vision
cd vision
pip3 install --user --no-build-isolation .
```

## Step 4: Install Transformers + Pillow

```bash
pip3 install --user 'transformers==4.48.3' 'Pillow>=10.0' 'numpy<2'
```

## Step 5: Inference Script (with required monkey-patches)

The NVIDIA torch wheel does not ship `torch.distributed`. Transformers'
`generate()` tries to import it. Two monkey-patches are required:

```python
import transformers.integrations.deepspeed as _ds
_ds.is_deepspeed_zero3_enabled = lambda: False

import transformers.integrations.fsdp as _fsdp
_fsdp.is_fsdp_managed_module = lambda m: False
```

Full working inference:

```python
import torch, time
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
processor = AutoProcessor.from_pretrained("microsoft/Florence-2-base", trust_remote_code=True)

img = Image.open("image.jpg").convert("RGB")

for task in ["<CAPTION>", "<DETAILED_CAPTION>", "<MORE_DETAILED_CAPTION>"]:
    inputs = processor(text=task, images=img, return_tensors="pt").to("cuda", torch.float16)
    ids = model.generate(input_ids=inputs["input_ids"], pixel_values=inputs["pixel_values"],
                         max_new_tokens=256, num_beams=3)
    text = processor.batch_decode(ids, skip_special_tokens=False)[0]
    result = processor.post_process_generation(text, task=task, image_size=(img.width, img.height))
    print(f"{task}: {result[task]}")
```

## Performance (Orin Nano Super, 8GB)

- Model load: 3.7s
- VRAM usage: 2.4 GB
- `<CAPTION>`: 1.7s, `<DETAILED_CAPTION>`: 1.3s, `<MORE_DETAILED_CAPTION>`: 4.3s

## Companion: Coral TPU

The same Jetson Orin has a Google Coral Edge TPU at `/dev/apex_0`. See
`references/coral-tpu.md` for setup, model downloads, and the reboot-required
pitfalls. Use Coral for sub-10ms pre-filtering (is there a person? what kind of
scene?) and Florence for deep captioning/OCR/grounded detection.

## Pitfalls

1. **torchvision::nms error** = wrong torchvision version. Must be 0.19.1 built from source.
2. **setuptools canonicalize_version error** = setuptools too new. Must be 69.5.1.
3. **flash_attn required** = transformers too new or too old. Must be 4.48.3.
4. **torch._C._distributed_c10d missing** = monkey-patches not applied before import.
5. **NumPy ABI mismatch** = numpy 2.x installed. Must be <2.0.
6. **Reinstalling any PyPI package may overwrite NVIDIA torch with CPU torch** — always verify `torch.cuda.is_available()` after any pip operation.

## Related: Coral TPU on Jetson

For the Google Coral Edge TPU (object detection, classification, pose estimation
at sub-10ms latency), see `references/coral-tpu-docker.md` — Docker-based deployment
that works around Python 3.10 / JetPack 6 incompatibility with the archived Coral stack.

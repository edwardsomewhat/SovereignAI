---
name: jetson-vision
description: "Run vision models (Florence 2, Coral TPU) on Jetson Orin Nano — install CUDA PyTorch, resolve torchvision dependency hell, serve as stateless vision processor for agent crews."
version: 1.0.0
tags: [jetson, orin-nano, florence-2, coral-tpu, vision, edge-ai, pytorch, torchvision]
platforms: [linux]
compatibility: "Jetson Orin Nano Super with JetPack 6 (R36), Coral TPU via PCIe, Docker available."
prerequisites:
  commands: [python3, ssh, docker]
metadata:
  hermes:
    category: mlops
---

# Jetson Vision

Deploy vision models on a Jetson Orin Nano Super (JetPack 6 / R36) —
Florence 2 for deep vision-language tasks, Coral TPU for fast object
detection. The Jetson acts as a **stateless vision processing server**
receiving images from the SovereignAI crew via SSH/scp and returning
structured captions/detections.

## Hardware Target

- **Device**: NVIDIA Jetson Orin Nano Super Developer Kit
- **GPU**: Orin Ampere (1024 CUDA cores), 8GB shared VRAM
- **TPU**: Google Coral via PCIe (`/dev/apex_0`, `libedgetpu1-std`)
- **OS**: JetPack 36.4.7 (Ubuntu 22.04, aarch64, CUDA 12.6)
- **RAM**: 7.4 GB (shared CPU/GPU)

## When to Use

- User wants to set up Florence 2, Coral TPU, or any vision model on a Jetson Orin Nano
- User asks about vision agent, "eyes" for an AI, or image analysis pipeline
- Vision model inference on edge hardware for SovereignAI or similar crew systems
- Dependency issues with PyTorch/torchvision on Jetson arm64

## Architecture: Stateless Vision Server

```
CAMERA / CREW AGENT (any network node)
        │
        │ scp image file or URL
        ▼
┌──────────────────────────────┐
│  NANO-BOX (Orin Nano Super)  │
│                              │
│  Tier 1: Coral TPU           │
│    Fast detect (<10ms)       │
│    "person at door"          │
│                              │
│  Tier 2: Florence 2 on GPU   │
│    Deep analysis             │
│    "man in red jacket        │
│     holding a package"       │
└──────────┬───────────────────┘
           │ returns structured JSON
           ▼
       CREW AGENT (decides action)
```

The nano-box never initiates — it receives images, processes them, returns
results. No cameras need to be directly connected. Any network camera, browser
screenshot, or file can be routed here.

## Known Working Stack (JetPack 6 / R36.4.7)

This exact combination was discovered after extensive trial and error.
**Deviating from any of these versions will break.**

### PyTorch + Torchvision

```bash
# 1. Install cusparselt (sudo required, one-time)
wget https://developer.download.nvidia.com/compute/cusparselt/redist/libcusparse_lt/linux-aarch64/libcusparse_lt-linux-aarch64-0.7.1.0-archive.tar.xz
tar xf libcusparse_lt-linux-aarch64-0.7.1.0-archive.tar.xz
sudo cp -a libcusparse_lt-linux-aarch64-0.7.1.0-archive/include/* /usr/local/cuda/include/
sudo cp -a libcusparse_lt-linux-aarch64-0.7.1.0-archive/lib/* /usr/local/cuda/lib64/
sudo ldconfig

# 2. CUDA PyTorch from NVIDIA JetPack 6 wheel
pip3 install --user \
  'https://developer.download.nvidia.com/compute/redist/jp/v61/pytorch/torch-2.5.0a0+872d972e41.nv24.08.17622132-cp310-cp310-linux_aarch64.whl'

# 3. Build torchvision 0.19.1 from source (MUST use setuptools 69.5.1)
pip3 install --user 'setuptools==69.5.1' cython
git clone --branch v0.19.1 --depth 1 https://github.com/pytorch/vision /tmp/vision
cd /tmp/vision
pip3 install --user --no-build-isolation .

# 4. Pin numpy <2 (CUDA torch crashes with numpy 2.x)
pip3 install --user 'numpy<2'

# 5. Verify
python3 -c '
import torch; import torchvision
print(f"Torch: {torch.__version__}  CUDA: {torch.cuda.is_available()}")
print(f"Torchvision: {torchvision.__version__}")
'
# Expected: Torch 2.5.0a0+..., CUDA: True, Torchvision 0.19.1a0+..., NO "nms does not exist" error
```

### Python ML Stack

```bash
pip3 install --user 'transformers==4.48.3' einops timm Pillow
```

### Florence 2 Inference

The NVIDIA CUDA torch wheel doesn't ship `torch.distributed`. Florence 2's
`generate()` calls into `transformers` FSDP/deepspeed checks which try to
import `torch.distributed.fsdp` → crash. The fix is a monkey-patch BEFORE
any transformers imports:

```python
import transformers.integrations.deepspeed as _ds
_ds.is_deepspeed_zero3_enabled = lambda: False

import transformers.integrations.fsdp as _fsdp
_fsdp.is_fsdp_managed_module = lambda m: False

# NOW safe to import
from transformers import AutoProcessor, AutoModelForCausalLM
```

Full working inference script at `references/florence2_inference.py`.

### Florence 2 Performance on Orin Nano

| Metric | Value |
|--------|-------|
| Model load time | ~4s |
| VRAM used by model | ~2.4 GB |
| `<CAPTION>` | ~1.7s |
| `<DETAILED_CAPTION>` | ~1.5s |
| `<MORE_DETAILED_CAPTION>` | ~4.3s |

Three detail levels available:
- `<CAPTION>` — short, one sentence
- `<DETAILED_CAPTION>` — paragraph with spatial details
- `<MORE_DETAILED_CAPTION>` — very verbose, multiple paragraphs

Also supports: `<OD>` (object detection), `<OCR>`, `<REGION_TO_DESCRIPTION>`,
`<REFERRING_EXPRESSION_SEGMENTATION>`, and more.

## Pitfalls

1. **Never install torchvision from PyPI** — it will replace the NVIDIA CUDA
   torch with CPU torch. Always use `--no-deps` or build from source.

2. **torchvision::nms does not exist** — the universal symptom of version
   mismatch. The ONLY working pair for JetPack 6 is torch 2.5.0 (NVIDIA wheel)
   + torchvision 0.19.1 (built from source). All other combinations fail.

3. **pypi.jetson-ai-lab.dev does not resolve** from some JetPack installs.
   Use `pypi.jetson-ai-lab.io` instead (the `.io` domain resolves).

4. **transformers 5.x breaks Florence 2** — the cached `modeling_florence2.py`
   uses APIs removed in 5.x. Pin to `transformers==4.48.3`.

5. **flash_attn requirement** — newer Florence 2 revisions on HuggingFace
   require `flash_attn`. Use the default revision and the monkey-patch
   approach rather than installing flash_attn on arm64.

6. **NVIDIA torch has no distributed** — the JetPack torch wheel omits
   `torch.distributed`. Always apply the FSDP/deepspeed monkey-patches
   before importing transformers.

Full working inference script at `references/florence2_inference.py`.

## Vision Agent Integration

The nano-box is called by the SovereignAI crew's vision agent:

```python
# On the nano-box: a simple script that receives image, runs Florence, returns JSON
# Invoked by crew via: ssh nano-box "python3 /path/to/vision_worker.py" < image.png
```

The crew's vision agent (`hermes_crew/agents/vision.py`) handles:
- Routing images to nano-box
- Selecting Coral vs Florence based on task
- Parsing Florence output into crew-usable format

## Coral TPU (Operational via Docker)

The Coral TPU is operational via Docker at `/dev/apex_0`:
- **Container**: `coral-tpu:latest` (~238MB, Python 3.9 + tflite-runtime 2.5.0.post1)
- **Model**: MobileNet V1 quantized (4.7MB) at `/home/fated/models/`
- **Inference**: 3-15ms, 335 FPS peak
- **Script**: `/home/fated/vision-server/coral_infer.py` (runs inside Docker)
- **Dual TPU**: Pass `--device /dev/apex_0 --device /dev/apex_1`, target with `options={'device': 'pci:0'}`

User must be in `apex` group. Docker is the solution (host Python 3.10 incompatible with pycoral).

Coral serves as Tier 1 — quick classification before invoking Florence.

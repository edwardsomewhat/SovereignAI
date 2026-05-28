# Coral TPU on Jetson Orin (JetPack 6) via Docker

## Problem

The Google Coral TPU ecosystem is archived and was built for Python 3.7–3.9
with tflite-runtime 2.5.x. JetPack 6 uses Python 3.10 and only has
tflite-runtime 2.13+ on PyPI (which is ABI-incompatible with libedgetpu 16.0).
All pre-compiled Edge TPU models crash with:

```
RuntimeError: Internal: Unsupported data type in custom op handler
```

Or: `OSError: libusb-1.0.so.0: cannot open shared object file`

## Solution: Docker with exact version pinning

Build a minimal Docker image (~150 MB) with Python 3.9, Coral's tflite-runtime
2.5.0, and the prebuilt libedgetpu copied from the pycoral repo.

### Dockerfile

```dockerfile
FROM python:3.9-slim
RUN apt-get update -qq && apt-get install -y --no-install-recommends libusb-1.0-0 && rm -rf /var/lib/apt/lists/*
COPY libedgetpu/ /usr/lib/aarch64-linux-gnu/
RUN ldconfig
RUN pip install --no-cache-dir "numpy<2"
RUN pip install --no-cache-dir \
    https://github.com/google-coral/pycoral/releases/download/v2.0.0/tflite_runtime-2.5.0.post1-cp39-cp39-linux_aarch64.whl \
    pillow
WORKDIR /app
```

### Prebuilt libraries source

Clone pycoral (shallow, no submodules needed just for the binaries):

```bash
git clone --depth 1 https://github.com/google-coral/pycoral /tmp/pycoral
mkdir -p build-context/libedgetpu
cp /tmp/pycoral/libedgetpu_bin/direct/aarch64/libedgetpu.so.1* build-context/libedgetpu/
```

### Build and run

```bash
docker build -t coral-tpu .
docker run --rm --device /dev/apex_0 \
  -v $(pwd)/models:/models \
  coral-tpu python3 infer.py
```

### Inference script template

```python
import numpy as np, time
from PIL import Image
import tflite_runtime.interpreter as tflite

delegate = tflite.load_delegate("/usr/lib/aarch64-linux-gnu/libedgetpu.so.1")
interpreter = tflite.Interpreter(
    model_path="/models/mobilenet_v1_1.0_224_quant_edgetpu.tflite",
    experimental_delegates=[delegate]
)
interpreter.allocate_tensors()

img = Image.open("input.jpg").resize((224, 224)).convert("RGB")
inp = interpreter.get_input_details()[0]
interpreter.set_tensor(inp["index"], np.expand_dims(np.array(img).astype(np.uint8), axis=0))

interpreter.invoke()  # ~3ms on Coral TPU
output = interpreter.get_tensor(interpreter.get_output_details()[0]["index"])
```

## Model Sources

Pre-compiled Edge TPU models are hosted at:

```
https://raw.githubusercontent.com/google-coral/test_data/master/<model>.tflite
```

Verified working:
- `mobilenet_v1_1.0_224_quant_edgetpu.tflite` (4.7 MB, classification)
- `mobilenet_v2_1.0_224_quant_edgetpu.tflite` (4.1 MB, classification)
- EfficientDet/SSD detection models may have different URL patterns

Labels:
- `https://raw.githubusercontent.com/google-coral/test_data/master/imagenet_labels.txt`
- `https://raw.githubusercontent.com/google-coral/test_data/master/coco_labels.txt`

## Performance (Orin Nano Super, Coral TPU via PCIe)

| Metric | Value |
|--------|-------|
| Classification (MobileNet V1, 224×224) | 3.0 ms |
| Throughput | 335 FPS |
| VRAM used | 0 (Coral has dedicated RAM) |
| Docker image size | ~150 MB |

## Dual TPU Adapter

For dual-Coral adapters (like Magic Blue Smoke), pass both devices:

```bash
docker run --rm --device /dev/apex_0 --device /dev/apex_1 coral-tpu ...
```

Target specific TPUs in code with `options={'device': 'pci:0'}` or `'pci:1'}`.

## System Requirements

- `libedgetpu1-std` or `libedgetpu1-max` installed on host (for `/dev/apex_0`)
- User must be in `apex` group: `sudo usermod -a -G apex $USER` (requires relog)
- Passwordless sudo optional — Docker uses `--device` without sudo on some setups

## Pitfalls

1. **"Device or resource busy"** — Coral DMA buffers locked from prior crash. Reboot or `sudo rmmod apex && sudo modprobe apex`.
2. **Permission denied on /dev/apex_0** — User not in apex group, or added post-login. Relog or reboot.
3. **numpy 2.x incompatibility** — tflite-runtime 2.5 needs `numpy<2`. Always pin.
4. **Host libs clobbered by pycoral clone** — The pycoral repo checkout can overwrite system libedgetpu. Use the bundled binaries from `libedgetpu_bin/direct/aarch64/` instead.
5. **Model runs on CPU but not TPU** — Edge TPU models contain `edgetpu-custom-op` that ONLY works with the delegate. They will crash on plain tflite CPU interpreter.

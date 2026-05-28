# Coral TPU on Jetson Orin (Same Machine)

The Coral Edge TPU at `/dev/apex_0` lives on the same Jetson Orin Nano as
Florence 2. It provides sub-10ms inference for TFLite models (classification,
detection, segmentation) — use it as a fast pre-filter before invoking Florence
for deep analysis.

## Hardware

- **Device**: `/dev/apex_0` (PCIe/M.2 interface, not USB)
- **Permissions**: `crw-rw---- root apex` — user must be in `apex` group
- **Kernel module**: `apex` (can't unload while in use)
- **Library**: `libedgetpu1-std` v16.0 (`/lib/aarch64-linux-gnu/libedgetpu.so.1`)

## Group Setup

```bash
sudo usermod -a -G apex $USER
# MUST reboot for group to take effect AND to clean DMA buffers
sudo reboot
```

## Python Setup

```bash
# System tflite-runtime (matches system libedgetpu version)
# DO NOT use pip tflite-runtime >=2.14 — ABI mismatch with libedgetpu v16
sudo pip3 install 'tflite-runtime==2.13.0'

# For user-level access (after reboot + group effect):
pip3 install --user 'tflite-runtime==2.13.0'
```

## Pre-compiled Models

Models are at `raw.githubusercontent.com/google-coral/test_data/master/`:

```bash
# Classification (1,000 ImageNet classes)
curl -sLO https://raw.githubusercontent.com/google-coral/test_data/master/mobilenet_v2_1.0_224_quant_edgetpu.tflite
curl -sLO https://raw.githubusercontent.com/google-coral/test_data/master/imagenet_labels.txt

# Object Detection (90 COCO classes)
curl -sLO https://raw.githubusercontent.com/google-coral/test_data/master/ssd_mobilenet_v2_coco_quant_edgetpu.tflite
curl -sLO https://raw.githubusercontent.com/google-coral/test_data/master/coco_labels.txt
```

## Verification Script

```python
import numpy as np, time
from PIL import Image
import tflite_runtime.interpreter as tflite

delegate = tflite.load_delegate('/lib/aarch64-linux-gnu/libedgetpu.so.1')
interpreter = tflite.Interpreter(
    model_path='mobilenet_v2_1.0_224_quant_edgetpu.tflite',
    experimental_delegates=[delegate]
)
interpreter.allocate_tensors()

inp = interpreter.get_input_details()[0]
img = Image.new('RGB', (224, 224), color='red')
interpreter.set_tensor(inp['index'], np.expand_dims(np.array(img).astype(np.uint8), axis=0))

t0 = time.time(); interpreter.invoke()
print(f'{((time.time()-t0)*1000):.1f}ms')  # expect <10ms
```

## Pitfalls

1. **"Could not map pages : Device or resource busy"** — Coral DMA buffers locked
   from a prior crashed process. Only fix: `sudo reboot`. The kernel module `apex`
   cannot be unloaded while processes have ever touched it.
2. **Permission denied on /dev/apex_0** — user not in `apex` group OR group add
   hasn't taken effect (requires relog/reboot).
3. **Delegate fails to load** — tflite-runtime version incompatible with libedgetpu.
   Must use 2.13.0 with libedgetpu1-std v16.0. Newer tflite-runtime has ABI mismatch.
4. **apt python3-pycoral fails** — requires Python <3.10; JetPack 6 ships Python 3.10.
   Use raw tflite-runtime + Edge TPU delegate instead.

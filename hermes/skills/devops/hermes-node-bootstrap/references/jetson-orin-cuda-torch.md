# Jetson Orin Nano — CUDA PyTorch Setup (JetPack 6 / R36)

When bootstrapping a Jetson Orin Nano as a compute node (vision, TTS, or ML inference),
the system Python's `torch` is frequently CPU-only. The NVIDIA-provided CUDA wheel is
required — standard `pip install torch` won't give GPU support on Jetson.

## Environment

| Component | Value |
|-----------|-------|
| Board | Jetson Orin Nano Super (aarch64) |
| JetPack | R36.4.7 (JetPack 6.1/6.2 compatible) |
| CUDA | 12.6 |
| Python | 3.10 |
| RAM | 7.4 GB (shared CPU/GPU) |
| GPU | Orin Ampere (1024 CUDA cores) |

## Step 1: Install cusparselt (required for torch ≥24.06)

NVIDIA's PyTorch for JetPack 6 needs `libcusparseLt.so.0`. Without it, `import torch` fails with:
`ImportError: libcusparseLt.so.0: cannot open shared object file`

```bash
CUSPARSELT_URL="https://developer.download.nvidia.com/compute/cusparselt/redist/libcusparse_lt/linux-aarch64"
CUSPARSELT_VERSION="0.7.1.0"
CUSPARSELT_NAME="libcusparse_lt-linux-aarch64-${CUSPARSELT_VERSION}-archive"

cd /tmp
curl -OLs "${CUSPARSELT_URL}/${CUSPARSELT_NAME}.tar.xz"
tar xf "${CUSPARSELT_NAME}.tar.xz"
sudo cp -a "${CUSPARSELT_NAME}/include/"* /usr/local/cuda/include/
sudo cp -a "${CUSPARSELT_NAME}/lib/"* /usr/local/cuda/lib64/
sudo ldconfig
rm -rf "${CUSPARSELT_NAME}" "${CUSPARSELT_NAME}.tar.xz"
```

## Step 2: Install NVIDIA CUDA PyTorch wheel

Uninstall any CPU-only torch first, then install the JetPack 6 wheel:

```bash
pip3 uninstall -y torch torchvision   # if CPU version present
pip3 install --user --no-cache \
  'https://developer.download.nvidia.com/compute/redist/jp/v61/pytorch/torch-2.5.0a0+872d972e41.nv24.08.17622132-cp310-cp310-linux_aarch64.whl'
```

**Verification:**
```python
import torch
print(torch.__version__)                          # 2.5.0a0+872d972e41
print(torch.cuda.is_available())                  # Must be True
print(torch.cuda.get_device_name(0))              # Orin (nvgpu)
free, total = torch.cuda.mem_get_info()
print(f"VRAM: {free/1e9:.1f}GB free / {total/1e9:.1f}GB total")
```

## Step 3: Install torchvision

The `jetson.webredirect.org` and `pypi.jetson-ai-lab.com` mirrors may be unreachable
from some networks. If DNS resolves, use:

```bash
pip3 install --user --no-cache \
  'http://jetson.webredirect.org/jp6/cu126/+f/5f9/67f920de3953f/torchvision-0.20.0-cp310-cp310-linux_aarch64.whl'
```

If DNS fails for those domains, build torchvision from source:

```bash
sudo apt-get install -y libjpeg-dev zlib1g-dev libpython3-dev \
  libopenblas-dev libavcodec-dev libavformat-dev libswscale-dev

git clone --branch release/0.20 https://github.com/pytorch/vision torchvision
cd torchvision
export BUILD_VERSION=0.20.0
python3 setup.py install --user
```

## Step 4: Fix numpy BLAS conflicts

JetPack 36 sometimes ships numpy 1.21.5 which conflicts with pip-installed torch.
Upgrade to avoid `RuntimeError: The current Numpy installation fails to pass simple sanity checks`:

```bash
pip3 install --user --upgrade --force-reinstall numpy
```

## Step 5: Upgrade Pillow (for transformers vision models)

JetPack's system Pillow may be 9.0.1, which lacks `Image.Resampling` needed by
transformers ≥5.0:

```bash
pip3 install --user --upgrade 'pillow>=10.0'
```

## Common Pitfalls

- **`torch.cuda.is_available()` is False.** The installed torch is CPU-only. Check `torch.__config__.show()` — if `USE_CUDA=0`, reinstall with the NVIDIA wheel.
- **`libcusparseLt.so.0: cannot open shared object file`.** Step 1 wasn't run — cusparselt libraries missing from `/usr/local/cuda/lib64/`.
- **`RuntimeError: numpy sanity check failed`.** Old system numpy conflicts. Upgrade with `--force-reinstall` (Step 4).
- **`module 'PIL.Image' has no attribute 'Resampling'`.** System Pillow too old. Upgrade (Step 5).
- **DNS cannot resolve `pypi.jetson-ai-lab.com` or `jetson.webredirect.org`.** These mirrors use non-standard DNS. Fall back to building torchvision from source or use the NVIDIA CDN (`developer.download.nvidia.com`) for torch itself.
- **NVCC not found but CUDA works.** JetPack 36 uses the `nvidia-l4t-cuda` package — `nvcc` may not be on PATH even though CUDA libs are present. This is normal; torch uses the libs directly.

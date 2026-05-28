# hq-ai llama.cpp Rebuild

When the llama.cpp binary is lost (e.g., /tmp wiped on reboot), rebuild from source. Pre-built release binaries fail on hq-ai because it runs a QEMU VM without AVX support.

## Prerequisites (one-time)

```bash
sudo apt-get install -y cmake build-essential libvulkan-dev libvulkan1 vulkan-tools
```

## Build

```bash
cd /home/fated
git clone --depth 1 https://github.com/ggerganov/llama.cpp.git llama.cpp-build
cd llama.cpp-build
mkdir build && cd build
cmake .. -DGGML_CUDA=OFF -DGGML_VULKAN=ON
cmake --build . --config Release -j$(nproc)
```

Binary lands at `build/bin/llama-server`.

## Post-Build

Update llama-swap to point at the new build:

```bash
sed -i 's|LLAMA_DIR=.*|LLAMA_DIR=/home/fated/llama.cpp-build/build/bin|' /home/fated/bin/llama-swap
```

Ensure the binary and libs are accessible:

```bash
chmod +x /home/fated/llama.cpp-build/build/bin/llama-server
```

The llama-swap script already sets `LD_LIBRARY_PATH` to include the build directory so shared libs resolve.

## Model Files

Models live permanently at `/home/fated/llama.cpp-models/` and survived the reboot. They do not need re-downloading.

## Why Not Pre-Built Binaries

- GitHub release b4824 binary crashed with `Illegal instruction` — compiled with AVX instructions not available on the QEMU Virtual CPU.
- The `/tmp` directory is wiped on reboot, so binaries placed there are lost.
- Building from source on the machine compiles for the actual host CPU features.

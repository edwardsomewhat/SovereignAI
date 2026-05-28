# Running llama.cpp Alongside Ollama

Tested on Quadro P5000 (16GB VRAM), Ubuntu 24.04, May 2026.

## Port Layout

```
Ollama:      :11434  (Open WebUI on :3000 proxies here)
llama.cpp:   :8080   (default llama-server port)
ComfyUI:     :8188   (if installed, separate concern)
```

No conflicts. Each server binds its own port. Both use the same GPU.

## VRAM Sharing

- Both servers occupy VRAM when models are loaded
- When idle, models sit in VRAM but don't consume compute
- On the P5000 (16GB): Qwen3.5-9B-Q4 (6GB) + Ollama models (4-10GB) = 8-12GB typical
- Simultaneous inference calls compete for GPU compute — they serialize, don't crash
- Only risk: loading a model that doesn't fit. Ollama's 23GB Nemotron + llama.cpp's 15GB Qwen 27B = 38GB into 16GB = OOM

## Storage

Ollama and llama.cpp model files are NOT shared:
- Ollama: `~/.ollama/models/` — blob store with manifests
- llama.cpp: raw `.gguf` files, typically in `~/llama.cpp-models/`

You CAN import a GGUF into Ollama to avoid re-download:
```bash
ollama create my-model -f - << 'EOF'
FROM /path/to/model.gguf
EOF
```
But this duplicates the file (~5GB each). Prefer keeping models in one place.

## Systemd Service Template

For llama.cpp to survive reboots alongside Ollama's system service:

```ini
# ~/.config/systemd/user/llama-server.service
[Unit]
Description=llama.cpp Inference Server
After=network-online.target

[Service]
Type=simple
ExecStart=/path/to/llama-server -m /path/to/model.gguf -ngl 99 -c 8192 -fa on \
    --host 0.0.0.0 --port 8080
Environment=LLAMA_CACHE=%h/llama.cpp-models
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

Enable with: `systemctl --user enable --now llama-server`
For persistence after logout: `sudo loginctl enable-linger $USER`

## Model Swap Pattern

When running a single GPU with multiple roles (coding, supervisor, reasoning, creative),
swap models on the same port rather than running parallel servers:

```bash
# Kill current, start new
pkill -f "llama-server.*8080"
llama-server -m /path/to/new-model.gguf -ngl 99 --port 8080 ...
```

A swap script with named aliases (`llama-swap coding|supervisor|reasoning|creative|stop|status`)
avoids remembering model paths and flags. See `templates/llama-swap.sh` for a reusable template.

---
name: hq-ai-model-routing
description: When to use hq-ai's llama.cpp (:8080) vs Ollama (:11434) — routing rules, model availability, and swap mechanics for the P5000 node.
---

# hq-ai Model Routing

hq-ai (100.84.92.74, P5000 16GB) runs two inference stacks side-by-side. They serve different purposes.

## llama.cpp — :8080 (STASHED — currently offline)

llama.cpp is stashed (May 2026). Not running. Systemd service disabled. The models
and swap scripts are preserved on disk but the Docker containers are stopped.

**If reactivated:** the Docker-based deployment with `full-cuda` image and
`/home/fated/bin/llama-swap` script is preserved. See references for build details.

## Both Running Simultaneously

llama.cpp is currently offline — only Ollama is active. The P5000 has 16GB VRAM.
Current Ollama config: nemotron3:33b (27GB on disk, ~11GB spill to system RAM)
is the largest active model. Multiple Ollama models can be loaded concurrently
but only active layers occupy VRAM.
**OLLAMA_CONTEXT_LENGTH=131072** set in systemd service (was 4096 default — coding
agents need 128K).

### Current Models (May 2026)

| Model | Size | Context | Tools | Notes |
|-------|------|---------|-------|-------|
| nemotron3:33b | 27GB | 128K | ✅ JSON | **Default coding model.** Spills 11GB to system RAM — fine for think-hard-output-once. |
| laguna-xs.2:q4_K_M | 23GB | 128K | ⚠️ XML | Tool calls formatted as XML in content, not JSON. Needs parser or tool-less mode. |
| deepseek-coder-v2:16b | 8.9GB | 128K | ❌ | "does not support tools" — usable for single-shot code gen only. |
| granite4.1:8b | 5.3GB | 128K | ✅ JSON | Fast fallback for simple coding tasks. |
| gemma4:e4b | 9.6GB | 128K | ⚠️ | Reasoning tokens flood context. Not for tool-calling. |
| gemma4:e2b | 7.2GB | 128K | ⚠️ | Same reasoning issue as e4b. |
| glm-4.7-flash:q4_K_M | 19GB | 128K | Untested | |
| qwen3.5:9b | 6.6GB | 128K | ✅ | General purpose. |
| hermes3:8b | 4.7GB | 128K | ✅ | **WARNING: 128K context forces 50/50 CPU/GPU split on P5000.** With 128K ctx, KV cache eats ~10GB VRAM, spilling half of model layers to CPU. Results: 0% GPU util, 1200%+ CPU, 30-70s per request. For non-agent inference, reduce context to 32K to keep all layers on GPU. For agent use, too small regardless — 14B+ recommended. |
| deepseek-coder:6.7b | 3.8GB | 128K | Untested | |

**Model variants with baked-in context:**
- `laguna-xs.2:128k` (num_ctx=131072)
- `laguna-xs.2:64k` (num_ctx=65536)

### Tool Call Compatibility (Critical)

Local models produce tool calls in different formats. The Ollama `/api/chat` endpoint
accepts JSON `tool_calls` in the response. Models that produce XML or text-JSON calls
will not work in the tool loop.

| Model | Tool Call Format | Usable for Agent Tool Loop? |
|-------|-----------------|---------------------------|
| nemotron3:33b | JSON `tool_calls` in API response | ✅ Primary coding model |
| granite4.1:8b | JSON `tool_calls` in API response | ✅ Fast fallback |
| laguna-xs.2 | XML in `content` field | ❌ Needs XML parser |
| deepseek-coder-v2:16b | None | ❌ API rejects: "does not support tools" |
| hermes3:8b | JSON `tool_calls` | ⚠️ Too small for complex tasks |

**Test command:**
```bash
curl -s http://100.84.92.74:11434/api/chat -d '{
  "model":"nemotron3:33b",
  "messages":[{"role":"user","content":"Say hi"}],
  "tools":[{"type":"function","function":{"name":"test","description":"test","parameters":{"type":"object","properties":{}}}}],
  "stream":false
}' | python3 -c "import sys,json; m=json.load(sys.stdin)['message']; print('tool_calls:', m.get('tool_calls','none')); print('content:', m.get('content','')[:80])"
```

### OpenCode Compatibility Layer — DO NOT USE

OpenCode's `@ai-sdk/openai-compatible` provider was tested extensively and found
unreliable with models >8B:

- granite4.1:8b → works for trivial tasks at 4K context
- All models >16B → hang indefinitely, no response, no error
- Root cause: the AI SDK provider layer times out or mismatches stream format

**Use direct `/api/chat` instead.** See `crewai-setup` skill → Step 7 for the
`OllamaCodeTool` pattern that bypasses OpenCode entirely.

### Context Window Configuration

Ollama defaults to **4096 tokens** — insufficient for any coding agent. The fix
requires server-level configuration:

```bash
# Add to ollama.service:
Environment="OLLAMA_CONTEXT_LENGTH=131072"

# Then:
sudo systemctl daemon-reload && sudo systemctl restart ollama
```

Model variants with baked-in context provide explicit control but do NOT override
the server default — the server-level env var is the authoritative setting.

**Verification:** After restart, check with:
```bash
curl -s http://localhost:11434/api/ps | python3 -c "import sys,json; [print(m['name'], m['context_length']) for m in json.load(sys.stdin)['models']]"
```

## Routing Decision Tree

```
Need vision?
  → Use gemma4 or qwen3-vl on Ollama

Need tool calling for coding agents?
  → CrewAI + OllamaCodeTool (direct /api/chat)
  → Primary: nemotron3:33b (JSON tool calls ✓, 128K ctx)
  → Fallback: granite4.1:8b (fast, JSON tool calls ✓)
  → NOT: laguna (XML tool calls), deepseek-coder-v2 (no tools)

Need Hermes agent profile? (infra, creative, vision)
  → API models (DeepSeek Chat) for the Hermes tool loop
  → Local models unreliable for Hermes' 8K system prompt + tool loop

Need maximum speed for non-agent inference?
  → Ollama granite4.1:8b or hermes3:8b

Default / general purpose?
  → Ollama nemotron3:33b (coding) or granite4.1:8b (general)
```

## Model Selection for Coding Agents

The thin-wrapper pattern (see `crewai-setup` skill, Step 7) uses CrewAI agents
with direct Ollama `/api/chat` calls — no Hermes system prompt overhead.

**Three requirements for the coding model:**

1. **JSON tool_calls** — must produce structured `tool_calls` in the API response,
   not text XML or inline JSON in the `content` field
2. **≥64K context** — the system prompt + tool defs + task need room (128K recommended)
3. **No reasoning-token flooding** — models that emit `<think>` tokens before content
   time out in the tool loop

**Current working models:**

| Model | JSON tools | Context | Spillover | Verdict |
|-------|-----------|---------|-----------|---------|
| nemotron3:33b | ✅ | 128K | 11GB → RAM | **Primary.** Writes + runs code reliably. |
| granite4.1:8b | ✅ | 128K | None (fits VRAM) | **Fallback.** Fast, less capable. |
| laguna-xs.2 | ❌ XML | 128K | 7GB → RAM | Tool-less single-shot possible. |
| deepseek-coder-v2:16b | ❌ | 128K | None | Single-shot code gen only. |

## llama.cpp Deployment (Docker)

Since hq-ai is a QEMU VM without AVX, pre-built llama.cpp binaries crash with "Illegal instruction." Building from source requires cmake, build-essential, Vulkan SDK, glslc, glslang-tools, spirv-headers — and still fails on missing dependencies.

**Use the Docker image instead.** No build chain, survives reboots, same models.

### Image Selection (CRITICAL)

| Image | GPU? | Notes |
|-------|------|-------|
| `ghcr.io/ggml-org/llama.cpp:server` | ❌ CPU-only | `-ngl 99` silently ignored. Do NOT use for GPU. |
| `ghcr.io/ggml-org/llama.cpp:server-cuda` | ❌ Broken | Missing `libllama-common.so.0` |
| `ghcr.io/ggml-org/llama.cpp:full-cuda` | ✅ Works | Needs `LD_LIBRARY_PATH=/app` + `--server` prefix |

**The only working GPU image:** `ghcr.io/ggml-org/llama.cpp:full-cuda`

```bash
docker pull ghcr.io/ggml-org/llama.cpp:full-cuda
```

### GPU Docker Run Command

The `full-cuda` image has a multi-tool CLI — you MUST prefix with `--server`:

```bash
docker run -d --name llama-server \
    --gpus all -p 8080:8080 \
    -v /home/fated/llama.cpp-models:/models \
    -e LD_LIBRARY_PATH=/app \
    ghcr.io/ggml-org/llama.cpp:full-cuda \
    --server -m /models/model.gguf -c 8192 --host 0.0.0.0 --port 8080 -ngl 99
```

**Required flags:**
- `-e LD_LIBRARY_PATH=/app` — fixes `libllama-common.so.0` not found
- `--server` — required prefix for full-cuda image (not needed for `:server` image)
- `-ngl 99` — offload all layers to GPU
- `--gpus all` — Docker GPU passthrough

### Context Sizing for P5000 (16GB)

The KV cache is the bottleneck. Formula: `model_size + kv_cache ≈ total_vram`

| Context | KV Cache (est.) | Model 10GB fits? | Model 6GB fits? |
|---------|----------------|-------------------|-------------------|
| 4096 | ~1.4 GB | ✅ | ✅ |
| 8192 | ~2.7 GB | ✅ (12.7GB) | ✅ |
| 16384 | ~5.4 GB | ❌ (15.4GB: tight) | ✅ |
| 32768 | ~10.8 GB | ❌ | ✅ (16.8GB: tight) |
| 65536 | ~21.6 GB | ❌ | ❌ |

**DeepSeek-Coder-V2-Lite 16B Q4_K_M (9.8GB):** max context **8192**
**Qwopus 9B MTP Q4_K_M (5.8GB):** max context **16384**
**Hermes 64K minimum:** NOT achievable on P5000 with any model >4GB

The swap script at `/home/fated/bin/llama-swap` uses `docker run` with GPU passthrough, volume mounts for `/home/fated/llama.cpp-models`, and port mapping to :8080. Each slot stops the existing container and starts a new one with the right model flags.

Models on disk:
- `/home/fated/llama.cpp-models/Qwen3.6-27B-IQ4_XS.gguf` (supervisor, 15GB)
- `/home/fated/llama.cpp-models/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf` (reasoning, 8GB)
- `/home/fated/llama.cpp-models/gemma-4-E4B-it-Q4_K_M.gguf` (creative, 5GB)
- `/home/fated/llama.cpp-models/models--unsloth--Qwen3.5-9B-MTP-GGUF/snapshots/<hash>/Qwen3.5-9B-UD-Q4_K_XL.gguf` (coding, 6GB, HF cache dir)

## Both Running Simultaneously

Yes, both stacks can run at the same time. The P5000 has 16GB VRAM. The running llama.cpp model + all loaded Ollama models must fit. Current config fits comfortably — Qwen3.5-9B-MTP (6GB) + Ollama models (~32GB total but only active model layers are in VRAM).

## Docker-based llama.cpp (current deployment)

llama.cpp runs via Docker image `ghcr.io/ggml-org/llama.cpp:server` — NOT `ghcr.io/ggerganov` (org changed). The llama-swap script at `/home/fated/bin/llama-swap` manages model swapping via Docker containers.

Key details:
- Image: `ghcr.io/ggml-org/llama.cpp:server`
- Models mounted from `/home/fated/llama.cpp-models/` into container
- HuggingFace cache also mounted for on-demand model downloads
- Container name: `llama-server`
- Docker survives reboots — binaries in /home/fated/ not /tmp/

## Verification

```bash
# Check llama.cpp (Docker)
ssh fated@hq-ai "curl -s http://localhost:8080/health"

# Check Ollama  
ssh fated@hq-ai "curl -s http://localhost:11434/api/tags"

# List llama.cpp models
ssh fated@hq-ai "ls /home/fated/llama.cpp-models/"

# List Ollama models
ssh fated@hq-ai "curl -s http://localhost:11434/api/tags | python3 -c \"import sys,json; [print(m['name']) for m in json.load(sys.stdin)['models']]\""

# Swap models
ssh fated@hq-ai "/home/fated/bin/llama-swap {qwopus|deepseek-coder|supervisor|r1|gemma|stop|status}"
```

## Infra Passwordless Sudo

Infra agent needs passwordless sudo on hq-ai for Docker, systemctl, nvidia-smi, journalctl, and ollama. Run once on hq-ai:

```bash
echo 'fated ALL=(ALL) NOPASSWD: /usr/bin/docker, /usr/bin/systemctl, /usr/bin/nvidia-smi, /usr/bin/journalctl, /usr/bin/ollama' | sudo tee /etc/sudoers.d/hermes-infra && sudo chmod 440 /etc/sudoers.d/hermes-infra
```

**Pitfall:** nvidia-smi lives at `/usr/bin/nvidia-smi` on Ubuntu, NOT `/usr/sbin/`. Wrong path = password prompt despite sudoers entry.

## Reboot Recovery

After hq-ai reboot:
- Ollama auto-starts via systemd — BUT the service being up doesn't mean models
  are runnable. Verify with a real inference call, not just `/api/tags`.
- Open WebUI auto-starts via Docker (--restart unless-stopped)
- llama.cpp does NOT auto-start — must be restarted manually
- **/tmp is wiped on reboot.** The llama-swap script references `/tmp/llama-b9247/` — this directory vanishes. The llama.cpp binary and the ollama update staging area must live in permanent locations:
  - llama.cpp binary: `/home/fated/llama.cpp-b9247/` (not `/tmp/`)
  - llama-swap script needs its `LLAMA_DIR` updated to the permanent path
  - Ollama update downloads: stage in `/home/fated/` not `/tmp/`

### Ollama Post-Reboot Corruption: "llama-server binary not found"

**Symptom:** Ollama responds to `/api/tags` (lists models) but ALL inference
requests fail with:
```
HTTP 500: error starting llama-server: llama-server binary not found
(checked: /usr/local/lib/ollama/llama-server, ...)
```

**Root cause:** The `llama-server` binary inside the Ollama installation is
missing or corrupted — typically after an Ollama update, OS package conflict,
or filesystem issue. The model metadata survives (in Ollama's DB) but the
execution engine doesn't.

**Fix:** Reinstall Ollama. Download the latest release tarball and extract:
```bash
curl -fsSL "https://github.com/ollama/ollama/releases/download/<TAG>/ollama-linux-amd64.tar.zst" -o /home/fated/ollama-update.tar.zst
zstd -d /home/fated/ollama-update.tar.zst -o /home/fated/ollama-update.tar
tar xf /home/fated/ollama-update.tar -C /home/fated/
sudo systemctl stop ollama
sudo cp /home/fated/bin/ollama /usr/local/bin/ollama
sudo systemctl start ollama
```

Models do NOT need to be re-pulled — they survive in Ollama's blob store.

### hq-ai Rebuild (Full)

When hq-ai needs a full rebuild, strip to compute-node essentials only:
- **Keep:** Ollama, llama.cpp (Docker), Tailscale, OpenSSH, ComfyUI
- **Remove:** Open WebUI, any non-inference services
- hq-ai is a compute+network node — all UI/management lives elsewhere

Post-rebuild checklist (in order):
1. Tailscale (`sudo tailscale up --ssh`)
2. OpenSSH (key-based auth for agent-to-agent)
3. Ollama (install binary, re-pull 4 models: hermes3:8b, gemma4-coder, deepseek-r1:14b, qwen3-vl:8b)
4. llama.cpp Docker (pull `ghcr.io/ggml-org/llama.cpp:server`, restore models to `/home/fated/llama.cpp-models/`)
5. Passwordless sudo (`/etc/sudoers.d/hermes-infra`)
6. llama-swap script at `/home/fated/bin/llama-swap`
7. ComfyUI

### Ollama Update Procedure

Ollama releases use `.tar.zst` (zstd compression), not `.tgz`. Download and extract:

```bash
# Find latest release tag
curl -s https://api.github.com/repos/ollama/ollama/releases?per_page=3 | python3 -c "import sys,json; [print(r['tag_name']) for r in json.load(sys.stdin)]"

# Download (replace TAG)
curl -fsSL "https://github.com/ollama/ollama/releases/download/TAG/ollama-linux-amd64.tar.zst" -o /home/fated/ollama-update.tar.zst

# Extract and install
zstd -d /home/fated/ollama-update.tar.zst -o /home/fated/ollama-update.tar
tar xf /home/fated/ollama-update.tar -C /home/fated/
sudo systemctl stop ollama
sudo cp /home/fated/bin/ollama /usr/local/bin/ollama
sudo systemctl start ollama
ollama --version
```

Note: `cp` must be in passwordless sudoers, or the user runs the cp command manually.

## Remote Access

Always use direct SSH from the terminal tool, not the Tailscale MCP SSH tool. The MCP tool has timeout limits and host key friction. See `references/ssh-preference.md` for node IPs and rationale.

### Tailscale SSH Intercept (re-auth loop)

When `ssh fated@<tailnet-ip>` returns a URL like `https://login.tailscale.com/a/...` instead of connecting, Tailscale SSH is intercepting port 22 on the target node. This is NOT a regular SSH failure — it's Tailscale's check-mode requiring device re-authorization.

**Diagnosis:**
- `curl http://<tailnet-ip>:11434/api/tags` works → node is online, Tailscale routing works
- `ssh fated@<tailnet-ip>` returns re-auth URL → Tailscale SSH is on, check-mode expired
- `tailscale status` shows node online → not a connectivity problem

**Root cause:** Tailscale SSH is enabled on the target (`tailscale up --ssh`). It intercepts port 22 and requires periodic browser-based re-auth (check-mode). Cross-device SSH (`autogroup:admin` → other nodes) is gated by ACL, not just self-SSH rules.

**Fix — ACL changes (Tailscale dashboard > Access Controls):**

The Tailscale SSH ACL must include the connecting user in `users`. For sovereign → hq-ai, both must be signed into the same tailnet account:

```json
"ssh": [
  {
   "action": "check",
   "src":    ["autogroup:member"],
   "dst":    ["autogroup:self"],
   "users":  ["autogroup:nonroot", "root", "fated"],
  },
],
```

`dst` only accepts `autogroup:self` — cross-device `*` or `*:*` is rejected. Same-account ownership handles cross-device. Also ensure the target machine page lists `fated` under SSH users.

After fixing the ACL, visit the re-auth URL once to approve the device, then SSH works. Persistent fix (no re-auth ever): register an SSH public key via `tailscale configure ssh --add-key ~/.ssh/id_ed25519.pub` on the connecting machine.

See `references/tailscale-ssh-acl.md` for the full ACL JSON, common errors, and key-based auth setup.

## Rebuild from Source

If the llama.cpp binary is lost (/tmp wiped on reboot), see `references/hq-ai-llama-rebuild.md` for the full build-from-source procedure, including prerequisite packages and why pre-built binaries don't work on this VM.

## Pitfalls

- llama.cpp: only ONE model at a time. If you need a different slot, you must swap (takes ~5-10 seconds with Docker).
- Ollama models aren't all in VRAM simultaneously — they load/unload on demand. But concurrent calls to different models cause swapping.
- If a training pipeline is running on one stack, route new requests to the other.
- Gemma4 MTP is Mac-only — don't try it on hq-ai.
- **Never put binaries in /tmp/ on hq-ai** — /tmp is wiped on reboot. Permanent location: /home/fated/
- **Use direct SSH `ssh fated@100.x.x.x`** rather than Tailscale MCP SSH tool — faster, no host-key friction, survives re-auth cycles.
- **Docker image org is `ggml-org`** not `ggerganov` — the repo moved.
- **/tmp is wiped on reboot.** Never store binaries, scripts, or persistent state in /tmp. llama.cpp binary lives at `/home/fated/llama.cpp/build/bin/`. llama-swap script at `/home/fated/bin/llama-swap`. Ollama binary lives at `/usr/local/bin/ollama` (system-managed).
- **Pre-built llama.cpp binaries may crash on VM CPUs.** hq-ai runs on QEMU Virtual CPU without AVX flags. Release binaries compiled with AVX2/AVX512 will "Illegal instruction" crash. Build from source with `-DGGML_VULKAN=ON` (not CUDA — P5000 doesn't use CUDA for llama.cpp). Clone to `/home/fated/llama.cpp-build/`, cmake, build.
- **Ollama updates:** download from GitHub releases (`.tar.zst` format, not `.tgz`). Extract with `zstd -d`. Stop ollama service, replace `/usr/local/bin/ollama`, restart.
- **deepseek-r1:14b does NOT support tool calling.** Any Hermes profile using it will fail with HTTP 400 "does not support tools." Do not use for agent profiles.
- **gemma4-coder floods reasoning tokens** before content. With a full Hermes system prompt, this causes 60s+ timeouts. The model's `thinking` capability emits reasoning tokens that consume the entire token budget before any visible content appears. Not usable for agent profiles.
- **hermes3:8b is too small for agent coding tasks** — hallucinates identity, misses instructions, gets stuck explaining tool syntax instead of doing the task. 14B+ recommended for agent work.
- **qwen2.5-coder models format tool calls as text JSON** — they output `{"name": "write_file", "arguments": {...}}` in the `content` field rather than structured `tool_calls` in the OpenAI response. Hermes displays this as text instead of executing it. The model IS tool-capable, but incompatible with Hermes' tool loop parser. **Workaround:** use OpenCode CLI (purpose-built tool execution) or API models for Hermes profiles.
- **Local models ≠ local agents.** You can serve models locally (Ollama/llama.cpp) but that doesn't mean they can drive a Hermes agent loop. Even llama3.1:8b (the only local model producing native OpenAI-format tool_calls) falls back to text-describing tools when loaded with Hermes' full system prompt (~5K-8K tokens of SOUL.md + tool definitions + AGENTS.md + memory). The model correctly calls tools in simple 2-message tests, but context pressure from Hermes' prompt overwhelms 8B params. Use local models for inference (via curl/direct API or OpenCode) and API models for Hermes agent profiles.
- **Ollama `llama-server` binary missing fix:** if all models fail with "llama-server binary not found" but the API responds, the Ollama install is corrupted. Re-run the install script: `curl -fsSL https://ollama.com/install.sh | sh`. This happened with 0.30.0-rc22; downgrading to stable 0.24.0 fixed it.
- **128K context forces CPU/GPU spill on P5000 (16GB).** With `OLLAMA_CONTEXT_LENGTH=131072`, the KV cache is massive — even small models like hermes3:8b (4.7GB weights) use ~10GB for KV cache at 128K, forcing layers to split 50/50 between GPU and CPU. Symptoms: `ollama ps` shows `50%/50% CPU/GPU`, nvidia-smi shows 0% GPU utilization, CPU pegged at 1200%+, each request takes 30-70s. **Fix:** reduce context to 32K (`OLLAMA_CONTEXT_LENGTH=32768`). The KV cache shrinks to ~2.5GB, all layers stay on GPU. 32K is sufficient for summarization, grading, and non-agent inference. For coding agents needing 128K, use larger models where the weight/context ratio makes the spill acceptable. **Note:** editing ollama.service requires sudo — hq-ai does not have passwordless sudo for sed, so apply the fix manually or via the sudoers entry once set up.

## Sudo Setup (Infra Agent)

Infra needs passwordless sudo for operational commands. On hq-ai:

```bash
echo 'fated ALL=(ALL) NOPASSWD: /usr/bin/docker, /usr/bin/systemctl, /usr/bin/nvidia-smi, /usr/bin/journalctl, /usr/bin/ollama, /usr/bin/cp' | sudo tee /etc/sudoers.d/hermes-infra && sudo chmod 440 /etc/sudoers.d/hermes-infra
```

Verify with `sudo -n <command>`. Same pattern applies to other nodes (nano, conchai, charlotte, csweb, omega, sovereign).

See `references/tailscale-ssh-acl.md` for the full ACL JSON, common errors, and key-based auth setup.

See `references/crew-profile-pattern.md` for the full agent profile creation recipe.
- `/usr/bin/nvidia-smi` not `/usr/sbin/nvidia-smi` — wrong path in sudoers breaks passwordless sudo.
- **/tmp is volatile across reboots.** Never stage binaries, scripts, or model files in /tmp if they need to survive a reboot. Use /home/fated/ instead. The llama-swap script's LLAMA_DIR and the ollama update staging area both need permanent paths.

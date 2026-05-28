---
name: comfyui
description: "Generate images, video, and audio with ComfyUI — install, launch, manage nodes/models, run workflows with parameter injection. Uses the official comfy-cli for lifecycle and direct REST/WebSocket API for execution."
version: 5.5.0
author: [kshitijk4poor, alt-glitch, purzbeats]
license: MIT
platforms: [macos, linux, windows]
compatibility: "Requires ComfyUI (local, Comfy Desktop, or Comfy Cloud) and comfy-cli (auto-installed via pipx/uvx by the setup script)."
prerequisites:
  commands: ["python3"]
setup:
  help: "Run scripts/hardware_check.py FIRST to decide local vs Comfy Cloud; then scripts/comfyui_setup.sh auto-installs locally (or use Cloud API key for platform.comfy.org)."
metadata:
  hermes:
    tags:
      - comfyui
      - image-generation
      - stable-diffusion
      - flux
      - sd3
      - wan-video
      - hunyuan-video
      - creative
      - generative-ai
      - video-generation
    related_skills: [stable-diffusion-image-generation, image_gen]
    category: creative
---

# ComfyUI

Generate images, video, audio, and 3D content through ComfyUI using the
official `comfy-cli` for setup/lifecycle and direct REST/WebSocket API
for workflow execution.

## What's in this skill

**Reference docs (`references/`):**

- `official-cli.md` — every `comfy ...` command, with flags
- `rest-api.md` — REST + WebSocket endpoints (local + cloud), payload schemas
- `workflow-format.md` — API-format JSON, common node types, param mapping
- `template-integrity.md` — converting `comfyui-workflow-templates` from
  editor format to API format: Reroute bypass, dotted dynamic-input keys
  (`values.a`, `resize_type.width`), Cloud quirks (302 redirect, 1 concurrent
  free-tier job, 1080p VRAM ceiling), Discord-compatible ffmpeg stitch.
  Authored by [@purzbeats](https://github.com/purzbeats). Load this whenever
  you're starting from an official template.
- `remote-agent-architecture.md` — running the ComfyUI agent on a different
  node than the GPU server. Covers Tailscale connectivity, `COMFY_HOST` env
  var, `_common.py` patch, File Browser for output access, and the systemd
  service pattern. Load this when the user wants autonomous agent access to
  a remote ComfyUI instance.
- `model-ecosystem.md` — canonical HuggingFace URLs for every model family:
  Flux (checkpoint + CLIP/T5/VAE repos), Qwen Image Edit (2509/2511/Lightning
  + LoRAs), Wan2.1 video (FLF2V/I2V/T2V fp8), LTX-Video (2B/13B distilled).
  Load this before hunting down model download URLs — most models are in
  non-obvious Comfy-Org repacks or community mirrors.
- `qwen-image-edit-setup.md` — canonical Qwen Image Edit pipeline (May 2026):
  GGUF model loading, lenML nodes for pixel-offset fix, CLIP type `qwen_image`
  requirement, Lightning LoRA for 4-step generation, resolution alignment rules,
  multi-image reference editing. Load this when the user wants Qwen-based image
  editing — the pipeline has subtle requirements that differ from standard
  SD/Flux workflows.

**Scripts (`scripts/`):**

| Script | Purpose |
|--------|---------|
| `_common.py` | Shared HTTP, cloud routing, node catalogs (don't run directly) |
| `hardware_check.py` | Probe GPU/VRAM/disk → recommend local vs Comfy Cloud |
| `comfyui_setup.sh` | Hardware check + comfy-cli + ComfyUI install + launch + verify |
| `extract_schema.py` | Read a workflow → list controllable params + model deps |
| `check_deps.py` | Check workflow against running server → list missing nodes/models |
| `auto_fix_deps.py` | Run check_deps then `comfy node install` / `comfy model download` |
| `run_workflow.py` | Inject params, submit, monitor, download outputs (HTTP or WS) |
| `run_batch.py` | Submit a workflow N times with sweeps, parallel up to your tier |
| `ws_monitor.py` | Real-time WebSocket viewer for executing jobs (live progress) |
| `health_check.py` | Verification checklist runner — comfy-cli + server + models + smoke test |
| `fetch_logs.py` | Pull traceback / status messages for a given prompt_id |

**Example workflows (`workflows/`):** SD 1.5, SDXL, Flux Dev, SDXL img2img,
SDXL inpaint, ESRGAN upscale, AnimateDiff video, Wan T2V. See
`workflows/README.md`.

## When to Use

- User asks to generate images with Stable Diffusion, SDXL, Flux, SD3, etc.
- User wants to run a specific ComfyUI workflow file
- User wants to chain generative steps (txt2img → upscale → face restore)
- User needs ControlNet, inpainting, img2img, or other advanced pipelines
- User asks to manage ComfyUI queue, check models, or install custom nodes
- User wants video/audio/3D generation via AnimateDiff, Hunyuan, Wan, AudioCraft, etc.

## Architecture: Two Layers

```
┌─────────────────────────────────────────────────────┐
│ Layer 1: comfy-cli (official lifecycle tool)        │
│   Setup, server lifecycle, custom nodes, models     │
│   → comfy install / launch / stop / node / model    │
└─────────────────────────┬───────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────┐
│ Layer 2: REST/WebSocket API + skill scripts         │
│   Workflow execution, param injection, monitoring   │
│   POST /api/prompt, GET /api/view, WS /ws           │
│   → run_workflow.py, run_batch.py, ws_monitor.py    │
└─────────────────────────────────────────────────────┘
```

**Why two layers?** The official CLI is excellent for installation and server
management but has minimal workflow execution support. The REST/WS API fills
that gap — the scripts handle param injection, execution monitoring, and
output download that the CLI doesn't do.

## Quick Start

### Detect environment

```bash
# What's available?
command -v comfy >/dev/null 2>&1 && echo "comfy-cli: installed"
curl -s http://127.0.0.1:8188/system_stats 2>/dev/null && echo "server: running"

# Can this machine run ComfyUI locally? (GPU/VRAM/disk check)
python3 scripts/hardware_check.py
```

If nothing is installed, see **Setup & Onboarding** below — but always run the
hardware check first.

### One-line health check

```bash
python3 scripts/health_check.py
# → JSON: comfy_cli on PATH? server reachable? at least one checkpoint? smoke-test passes?
```

## Core Workflow

### Step 1: Get a workflow JSON in API format

Workflows must be in API format (each node has `class_type`). They come from:

- ComfyUI web UI → **Workflow → Export (API)** (newer UI) or
  the legacy "Save (API Format)" button (older UI)
- This skill's `workflows/` directory (ready-to-run examples)
- Community downloads (civitai, Reddit, Discord) — usually editor format,
  must be loaded into ComfyUI then re-exported

Editor format (top-level `nodes` and `links` arrays) is **not directly
executable**. The scripts detect this and tell you to re-export.

### Step 2: See what's controllable

```bash
python3 scripts/extract_schema.py workflow_api.json --summary-only
# → {"parameter_count": 12, "has_negative_prompt": true, "has_seed": true, ...}

python3 scripts/extract_schema.py workflow_api.json
# → full schema with parameters, model deps, embedding refs
```

### Step 3: Run with parameters

```bash
# Local (defaults to http://127.0.0.1:8188)
python3 scripts/run_workflow.py \
  --workflow workflow_api.json \
  --args '{"prompt": "a beautiful sunset over mountains", "seed": -1, "steps": 30}' \
  --output-dir ./outputs

# Cloud (export API key once; uses correct /api routing automatically)
export COMFY_CLOUD_API_KEY="comfyui-..."
python3 scripts/run_workflow.py \
  --workflow workflow_api.json \
  --args '{"prompt": "..."}' \
  --host https://cloud.comfy.org \
  --output-dir ./outputs

# Real-time progress via WebSocket (requires `pip install websocket-client`)
python3 scripts/run_workflow.py \
  --workflow flux_dev.json \
  --args '{"prompt": "..."}' \
  --ws

# img2img / inpaint: pass --input-image to upload + reference automatically
python3 scripts/run_workflow.py \
  --workflow sdxl_img2img.json \
  --input-image image=./photo.png \
  --args '{"prompt": "make it watercolor", "denoise": 0.6}'

# Batch / sweep: 8 random seeds, parallel up to cloud tier limit
python3 scripts/run_batch.py \
  --workflow sdxl.json \
  --args '{"prompt": "abstract"}' \
  --count 8 --randomize-seed --parallel 3 \
  --output-dir ./outputs/batch
```

`-1` for `seed` (or omitting it with `--randomize-seed`) generates a fresh
random seed per run.

### Step 4: Present results

The scripts emit JSON to stdout describing every output file:

```json
{
  "status": "success",
  "prompt_id": "abc-123",
  "outputs": [
    {"file": "./outputs/sdxl_00001_.png", "node_id": "9",
     "type": "image", "filename": "sdxl_00001_.png"}
  ]
}
```

## Decision Tree

| User says | Tool | Command |
|-----------|------|---------|
| **Lifecycle (use comfy-cli)** | | |
| "install ComfyUI" | comfy-cli | `bash scripts/comfyui_setup.sh` |
| "start ComfyUI" | comfy-cli | `comfy launch --background` |
| "stop ComfyUI" | comfy-cli | `comfy stop` |
| "install X node" | comfy-cli | `comfy node install <name>` |
| "download X model" | comfy-cli | `comfy model download --url <url> --relative-path models/checkpoints` |
| "list installed models" | comfy-cli | `comfy model list` |
| "list installed nodes" | comfy-cli | `comfy node show installed` |
| **Execution (use scripts)** | | |
| "is everything ready?" | script | `health_check.py` (optionally with `--workflow X --smoke-test`) |
| "what can I change in this workflow?" | script | `extract_schema.py W.json` |
| "check if W's deps are met" | script | `check_deps.py W.json` |
| "fix missing deps" | script | `auto_fix_deps.py W.json` |
| "generate an image" | script | `run_workflow.py --workflow W --args '{...}'` |
| "use this image" (img2img) | script | `run_workflow.py --input-image image=./x.png ...` |
| "8 variations with random seeds" | script | `run_batch.py --count 8 --randomize-seed ...` |
| "show me live progress" | script | `ws_monitor.py --prompt-id <id>` |
| "fetch the error from job X" | script | `fetch_logs.py <prompt_id>` |
| **Direct REST** | | |
| "what's in the queue?" | REST | `curl http://HOST:8188/queue` (local) or `--host https://cloud.comfy.org` |
| "cancel that" | REST | `curl -X POST http://HOST:8188/interrupt` |
| "free GPU memory" | REST | `curl -X POST http://HOST:8188/free` |

## Setup & Onboarding

When a user asks to set up ComfyUI, **the FIRST thing to do is ask whether
they want Comfy Cloud (hosted, zero install, API key) or Local (install
ComfyUI on their machine)**. Don't start running install commands or hardware
checks until they've answered.

**Official docs:** https://docs.comfy.org/installation
**CLI docs:** https://docs.comfy.org/comfy-cli/getting-started
**Cloud docs:** https://docs.comfy.org/get_started/cloud
**Cloud API:** https://docs.comfy.org/development/cloud/overview

### Step 0: Ask Local vs Cloud (ALWAYS FIRST)

Suggested script:

> "Do you want to run ComfyUI locally on your machine, or use Comfy Cloud?
>
> - **Comfy Cloud** — hosted on RTX 6000 Pro GPUs, all common models pre-installed,
>   zero setup. Requires an API key (paid subscription required to actually run
>   workflows; free tier is read-only). Best if you don't have a capable GPU.
> - **Local** — free, but your machine MUST meet the hardware requirements:
>   - NVIDIA GPU with **≥6 GB VRAM** (≥8 GB for SDXL, ≥12 GB for Flux/video), OR
>   - AMD GPU with ROCm support (Linux), OR
>   - Apple Silicon Mac (M1+) with **≥16 GB unified memory** (≥32 GB recommended).
>   - Intel Macs and machines with no GPU will NOT work — use Cloud instead.
>
> Which would you like?"

Routing:

- **Cloud** → skip to **Path A**.
- **Local** → run hardware check first, then pick a path from Paths B–E based on the verdict.
- **Unsure** → run the hardware check and let the verdict decide.

### Step 1: Verify Hardware (ONLY if user chose local)

```bash
python3 scripts/hardware_check.py --json
# Optional: also probe `torch` for actual CUDA/MPS:
python3 scripts/hardware_check.py --json --check-pytorch
```

| Verdict    | Meaning                                                       | Action |
|------------|---------------------------------------------------------------|--------|
| `ok`       | ≥8 GB VRAM (discrete) OR ≥32 GB unified (Apple Silicon)       | Local install — use `comfy_cli_flag` from report |
| `marginal` | SD1.5 works; SDXL tight; Flux/video unlikely                  | Local OK for light workflows, else **Path A (Cloud)** |
| `cloud`    | No usable GPU, <6 GB VRAM, <16 GB Apple unified, Intel Mac, Rosetta Python | **Switch to Cloud** unless user explicitly forces local |

The script also surfaces `wsl: true` (WSL2 with NVIDIA passthrough) and
`rosetta: true` (x86_64 Python on Apple Silicon — must reinstall as ARM64).

If verdict is `cloud` but the user wants local, do not proceed silently.
Show the `notes` array verbatim and ask whether they want to (a) switch to
Cloud or (b) force a local install (will OOM or be unusably slow on modern models).

### Choosing an Installation Path

Use the hardware check first. The table below is the fallback for when the
user has already told you their hardware:

| Situation | Recommended Path |
|-----------|------------------|
| `verdict: cloud` from hardware check | **Path A: Comfy Cloud** |
| No GPU / want to try without commitment | **Path A: Comfy Cloud** |
| Windows + NVIDIA + non-technical | **Path B: ComfyUI Desktop** |
| Windows + NVIDIA + technical | **Path C: Portable** or **Path D: comfy-cli** |
| Linux + any GPU | **Path D: comfy-cli** (easiest) |
| macOS + Apple Silicon | **Path B: Desktop** or **Path D: comfy-cli** |
| Headless / server / CI / agents | **Path D: comfy-cli** |

For the fully automated path (hardware check → install → launch → verify):

```bash
bash scripts/comfyui_setup.sh
# Or with overrides:
bash scripts/comfyui_setup.sh --m-series --port=8190 --workspace=/data/comfy
```

It runs `hardware_check.py` internally, refuses to install locally when the
verdict is `cloud` (unless `--force-cloud-override`), picks the right
`comfy-cli` flag, and prefers `pipx`/`uvx` over global `pip` to avoid polluting
system Python.

---

### Path A: Comfy Cloud (No Local Install)

For users without a capable GPU or who want zero setup. Hosted on RTX 6000 Pro.

**Docs:** https://docs.comfy.org/get_started/cloud

1. Sign up at https://comfy.org/cloud
2. Generate an API key at https://platform.comfy.org/login
3. Set the key:
   ```bash
   export COMFY_CLOUD_API_KEY="comfyui-xxxxxxxxxxxx"
   ```
4. Run workflows:
   ```bash
   python3 scripts/run_workflow.py \
     --workflow workflows/flux_dev_txt2img.json \
     --args '{"prompt": "..."}' \
     --host https://cloud.comfy.org \
     --output-dir ./outputs
   ```

**Pricing:** https://www.comfy.org/cloud/pricing
**Concurrent jobs:** Free/Standard 1, Creator 3, Pro 5. Free tier
**cannot run workflows via API** — only browse models. Paid subscription
required for `/api/prompt`, `/api/upload/*`, `/api/view`, etc.

---

### Path B: ComfyUI Desktop (Windows / macOS)

One-click installer for non-technical users. Currently Beta.

**Docs:** https://docs.comfy.org/installation/desktop
- **Windows (NVIDIA):** https://download.comfy.org/windows/nsis/x64
- **macOS (Apple Silicon):** https://comfy.org

Linux is **not supported** for Desktop — use Path D.

---

### Path C: ComfyUI Portable (Windows Only)

**Docs:** https://docs.comfy.org/installation/comfyui_portable_windows

Download from https://github.com/comfyanonymous/ComfyUI/releases, extract,
run `run_nvidia_gpu.bat`. Update via `update/update_comfyui_stable.bat`.

---

### Path D: comfy-cli (All Platforms — Recommended for Agents)

The official CLI is the best path for headless/automated setups.

**Docs:** https://docs.comfy.org/comfy-cli/getting-started

#### Install comfy-cli

```bash
# Recommended:
pipx install comfy-cli
# Or use uvx without installing:
uvx --from comfy-cli comfy --help
# Or (if pipx/uvx unavailable):
pip install --user comfy-cli
```

Disable analytics non-interactively:
```bash
comfy --skip-prompt tracking disable
```

#### Install ComfyUI

```bash
comfy --skip-prompt install --nvidia              # NVIDIA (CUDA)
comfy --skip-prompt install --amd                 # AMD (ROCm, Linux)
comfy --skip-prompt install --m-series            # Apple Silicon (MPS)
comfy --skip-prompt install --cpu                 # CPU only (slow)
comfy --skip-prompt install --nvidia --fast-deps  # uv-based dep resolution
```

Default location: `~/comfy/ComfyUI` (Linux), `~/Documents/comfy/ComfyUI`
(macOS/Win). Override with `comfy --workspace /custom/path install`.

#### Launch / verify

```bash
comfy launch --background                       # background daemon on :8188
comfy launch -- --listen 0.0.0.0 --port 8190    # LAN-accessible custom port
curl -s http://127.0.0.1:8188/system_stats      # health check
```

---

### Path E: Manual Install (Advanced / Unsupported Hardware)

For Ascend NPU, Cambricon MLU, Intel Arc, or other unsupported hardware.

**Docs:** https://docs.comfy.org/installation/manual_install

```bash
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu130
pip install -r requirements.txt
python main.py
```

---

### Post-Install: Download Models

```bash
# SDXL (general purpose, ~6.5 GB)
comfy model download \
  --url "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors" \
  --relative-path models/checkpoints

# SD 1.5 (lighter, ~4 GB, good for 6 GB cards)
comfy model download \
  --url "https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors" \
  --relative-path models/checkpoints

# Flux Dev fp8 (diffusion model, ~12 GB) — use wget; comfy-cli hangs on large files
wget -c -O models/checkpoints/flux1-dev-fp8.safetensors \
  "https://huggingface.co/Comfy-Org/flux1-dev/resolve/main/flux1-dev-fp8.safetensors"

# Flux text encoders (REQUIRED for Flux — NOT in Comfy-Org/flux1-dev)
# Correct source: comfyanonymous/flux_text_encoders
comfy --skip-prompt model download \
  --url "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors" \
  --relative-path models/clip
comfy --skip-prompt model download \
  --url "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp8_e4m3fn.safetensors" \
  --relative-path models/clip

# Flux VAE — both BFL repos are gated; use an open community mirror
wget -c -O models/vae/ae.safetensors \
  "https://huggingface.co/Kijai/flux-fp8/resolve/main/flux-vae-bf16.safetensors"

# CivitAI (set token first):
comfy model download \
  --url "https://civitai.com/api/download/models/128713" \
  --relative-path models/checkpoints \
  --set-civitai-api-token "YOUR_TOKEN"
```

List installed: `comfy model list`.

### Post-Install: Install Custom Nodes

```bash
comfy node install comfyui-impact-pack             # popular utility pack
comfy node install comfyui-controlnet-aux          # ControlNet preprocessors
comfy node install comfyui-essentials              # common helpers (includes rembg)
comfy node install ComfyUI-WanVideoWrapper         # Wan2.1 video generation
comfy node install ComfyUI-WanVideoKsampler        # Wan2.1 sampling
comfy node install ComfyUI-HunyuanVideoWrapper     # HunyuanVideo
comfy node install comfyui-ltxvideo                # LTX-Video (Lightricks, fast)
comfy node install ComfyUI-VideoHelperSuite        # video combine/split/format
comfy node update all
comfy node install-deps --workflow=workflow.json   # install everything a workflow needs
```

### Post-Install: Verify

```bash
python3 scripts/health_check.py
# → comfy_cli on PATH? server reachable? checkpoints? smoke test?

python3 scripts/check_deps.py my_workflow.json
# → are this workflow's nodes/models/embeddings installed?

python3 scripts/run_workflow.py \
  --workflow workflows/sd15_txt2img.json \
  --args '{"prompt": "test", "steps": 4}' \
  --output-dir ./test-outputs
```

## Image Upload (img2img / Inpainting)

The simplest way is to use `--input-image` with `run_workflow.py`:

```bash
python3 scripts/run_workflow.py \
  --workflow workflows/sdxl_img2img.json \
  --input-image image=./photo.png \
  --args '{"prompt": "make it cyberpunk", "denoise": 0.6}'
```

The flag uploads `photo.png`, then injects its server-side filename into
whatever schema parameter is named `image`. For inpainting, pass both:

```bash
python3 scripts/run_workflow.py \
  --workflow workflows/sdxl_inpaint.json \
  --input-image image=./photo.png \
  --input-image mask_image=./mask.png \
  --args '{"prompt": "fill with flowers"}'
```

Manual upload via REST:
```bash
curl -X POST "http://127.0.0.1:8188/upload/image" \
  -F "image=@photo.png" -F "type=input" -F "overwrite=true"
# Returns: {"name": "photo.png", "subfolder": "", "type": "input"}

# Cloud equivalent:
curl -X POST "https://cloud.comfy.org/api/upload/image" \
  -H "X-API-Key: $COMFY_CLOUD_API_KEY" \
  -F "image=@photo.png" -F "type=input" -F "overwrite=true"
```

## Cloud Specifics

- **Base URL:** `https://cloud.comfy.org`
- **Auth:** `X-API-Key` header (or `?token=KEY` for WebSocket)
- **API key:** set `$COMFY_CLOUD_API_KEY` once and the scripts pick it up automatically
- **Output download:** `/api/view` returns a 302 to a signed URL; the scripts
  follow it and strip `X-API-Key` before fetching from the storage backend
  (don't leak the API key to S3/CloudFront).
- **Endpoint differences from local ComfyUI:**
  - `/api/object_info`, `/api/queue`, `/api/userdata` — **403 on free tier**;
    paid only.
  - `/history` is renamed to `/history_v2` on cloud (the scripts route
    automatically).
  - `/models/<folder>` is renamed to `/experiment/models/<folder>` on cloud
    (the scripts route automatically).
  - `clientId` in WebSocket is currently ignored — all connections for a
    user receive the same broadcast. Filter by `prompt_id` client-side.
  - `subfolder` is accepted on uploads but ignored — cloud has a flat namespace.
- **Concurrent jobs:** Free/Standard: 1, Creator: 3, Pro: 5. Extras queue
  automatically. Use `run_batch.py --parallel N` to saturate your tier.

## Queue & System Management

```bash
# Local
curl -s http://127.0.0.1:8188/queue | python3 -m json.tool
curl -X POST http://127.0.0.1:8188/queue -d '{"clear": true}'    # cancel pending
curl -X POST http://127.0.0.1:8188/interrupt                      # cancel running
curl -X POST http://127.0.0.1:8188/free \
  -H "Content-Type: application/json" \
  -d '{"unload_models": true, "free_memory": true}'

# Cloud — same paths under /api/, plus:
python3 scripts/fetch_logs.py --tail-queue --host https://cloud.comfy.org
```

## Pitfalls

1. **API format required** — every script and the `/api/prompt` endpoint expect
   API-format workflow JSON. The scripts detect editor format (top-level
   `nodes` and `links` arrays) and tell you to re-export via
   "Workflow → Export (API)" (newer UI) or "Save (API Format)" (older UI).

2. **Server must be running** — all execution requires a live server.
   `comfy launch --background` starts one. Verify with
   `curl http://127.0.0.1:8188/system_stats`.

3. **Model names are exact** — case-sensitive, includes file extension.
   `check_deps.py` does fuzzy matching (with/without extension and folder
   prefix), but the workflow itself must use the canonical name. Use
   `comfy model list` to discover what's installed.

4. **Missing custom nodes** — "class_type not found" means a required node
   isn't installed. `check_deps.py` reports which package to install;
   `auto_fix_deps.py` runs the install for you.

5. **Working directory** — `comfy-cli` auto-detects the ComfyUI workspace.
   If commands fail with "no workspace found", use
   `comfy --workspace /path/to/ComfyUI <command>` or
   `comfy set-default /path/to/ComfyUI`.

6. **Cloud free-tier API limits** — `/api/prompt`, `/api/view`, `/api/upload/*`,
   `/api/object_info` all return 403 on free accounts. `health_check.py` and
   `check_deps.py` handle this gracefully and surface a clear message.

7. **Timeout for video/audio workflows** — auto-detected when an output node
   is `VHS_VideoCombine`, `SaveVideo`, etc.; the default jumps from 300 s to
   900 s. Override explicitly with `--timeout 1800`.

8. **Path traversal in output filenames** — server-supplied filenames are
   passed through `safe_path_join` to refuse anything escaping `--output-dir`.
   Keep this protection on — workflows with custom save nodes can produce
   arbitrary paths.

9. **Workflow JSON is arbitrary code** — custom nodes run Python, so
   submitting an unknown workflow has the same trust profile as `eval`.
   Inspect workflows from untrusted sources before running.

10. **Auto-randomized seed** — pass `seed: -1` in `--args` (or use
    `--randomize-seed` and omit the seed) to get a fresh seed per run.
    The actual seed is logged to stderr.

11. **`tracking` prompt** — first run of `comfy` may prompt for analytics.
    Use `comfy --skip-prompt tracking disable` to skip non-interactively.
    `comfyui_setup.sh` does this for you.

12. **Workspace directory must not exist** — `comfy --workspace /path install` clones ComfyUI fresh into the target directory. If the directory already exists as a non-git directory, the error is `exists but is not a valid git repository`. `rm -rf` it and retry.

13. **--restore for missing dependencies** — If launch fails with `ModuleNotFoundError` (common: `sqlalchemy`, `alembic`), run `comfy install --nvidia --restore` to reinstall all Python requirements. The initial install can occasionally skip packages, especially on first-run venv setups.\n\n13a. **Model filename mismatches** — Workflow JSONs often reference canonical filenames (e.g. `flux1-dev.safetensors`, `t5xxl_fp16.safetensors`) that don't match your actual downloaded files (e.g. `flux1-dev-fp8.safetensors`, `t5xxl_fp8_e4m3fn.safetensors`). Create symlinks: `ln -sf actual_file.safetensors expected_name.safetensors`. Also, workflows using `UNETLoader` expect models in `models/unet/`; symlink from `models/checkpoints/` if needed: `ln -sf ../checkpoints/flux1-dev-fp8.safetensors models/unet/flux1-dev.safetensors`. Run `check_deps.py` after creating symlinks to verify resolution.

14. **Systemd persistence** — For headless servers, create a systemd user service. Use the venv Python directly (`/workspace/.venv/bin/python main.py --listen 0.0.0.0 --port 8188`), not `comfy-cli launch`. Enable linger for unattended reboots: `sudo loginctl enable-linger $USER`. Copy and customize `templates/comfyui.service`.

15. **Multi-drive storage** — Point `--workspace` to a dedicated data partition (e.g. `/mnt/hermes_data/comfy`) to keep models off root. Models consume 6–50+ GB each. **Never touch Windows/NTFS drives without explicit user confirmation** — ask first, name the specific drive.

16. **Split/sharded model repos** — Some Comfy-Org models are split across multiple safetensors files (e.g. `split_files/diffusion_models/`). `comfy model download --url` expects a single file and returns 404. **DO NOT use git-lfs with glob patterns** — `git lfs pull -I "*.safetensors"` silently does nothing on these repos. The reliable method: `GIT_LFS_SKIP_SMUDGE=1 git clone <url>` to get the directory structure (LFS pointers only), then use `wget -c` with explicit HF resolve URLs for each file you need: `wget -c -O <local_path> "https://huggingface.co/<repo>/resolve/main/<path>"`. Full recipe in `references/split-model-download.md`.\n\n18a. **comfy-cli download hangs** — `comfy model download` can hang indefinitely on large files (12GB+) with 0 bytes transferred. Use wget directly as a fallback. The `--skip-prompt` flag is required for non-interactive use, but even with it, large downloads may stall.

17. **Custom nodes not in Manager registry** — `comfy node install <name>` searches the ComfyUI Manager registry. If a node isn't indexed there (404), clone it from GitHub directly: `cd custom_nodes && git clone <url> && cd <dir> && .venv/bin/pip install -r requirements.txt`. Search GitHub with: `curl -s "https://api.github.com/search/repositories?q=comfyui+<keywords>&sort=stars"`.

18. **`--skip-prompt` required for non-interactive downloads** — `comfy model download` and other comfy-cli commands may try to read from stdin (interactive prompts). When running in background or via scripts, always add `--skip-prompt`: `comfy --skip-prompt model download --url ...`. Without it, downloads abort with \"Input is not a terminal\" or hang silently.

19. **Custom node names may not match Manager registry** — `comfy node install <name>` queries the ComfyUI Manager registry, but some well-known nodes use different titles/IDs than their GitHub repo names. Examples: `ComfyUI_IPAdapter_plus` and `ComfyUI_essentials` (titles in the registry JSON) are not installable via `comfy node install comfyui-ipadapter-plus` or `comfy node install comfyui-essentials`. When `comfy node install` returns \"not found in registry\" for a known node, clone directly: `cd custom_nodes && git clone <url> && cd <dir> && ../.venv/bin/pip install -r requirements.txt`. Search the registry JSON manually with `grep -i '<keyword>' .venv/lib/.../custom-node-list.json` to discover the correct title.

20. **Flux support models are NOT in Comfy-Org/flux1-dev** — That repo only contains the diffusion model (flux1-dev-fp8.safetensors) and split variants. The CLIP-L, T5 text encoder, and VAE files are in separate repos: `comfyanonymous/flux_text_encoders` (clip_l.safetensors, t5xxl_fp8_e4m3fn.safetensors) and `black-forest-labs/FLUX.1-schnell` (ae.safetensors). The `black-forest-labs/FLUX.1-dev` repo is gated and requires authentication; use the Schnell repo for the open VAE.

21. **git-lfs is unreliable for HF split-model repos — use wget instead** — Split-model repos (pitfall #16) can exceed 50 GB total. The documented approach of `GIT_LFS_SKIP_SMUDGE=1 git clone` + `git lfs pull -I <glob>` frequently fails: glob patterns silently match nothing (files remain LFS pointers), and `git lfs fetch --all` hangs with 0 bytes transferred. The reliable approach is to clone the repo structure only (for workflow JSON files) and download individual model files via wget:
   ```bash
   # Clone repo structure only (skip LFS)
   cd models/
   GIT_LFS_SKIP_SMUDGE=1 git clone <hf-repo-url> <folder-name>
   # Download individual model files via wget — reliable and resumable
   wget -c -O <folder-name>/split_files/diffusion_models/model.safetensors \
     "https://huggingface.co/<repo>/resolve/main/split_files/diffusion_models/model.safetensors"
   ```
   For repos with ~10 files you need, wget each one explicitly. For repos with 50+ files, `git lfs pull` MAY work but expect it to hang; fall back to wget. The clone still provides workflow JSONs and directory structure even when LFS fails. This saves 30–80 GB of disk for repos with many precision variants (bf16, fp8, fp4, nvfp4).

22. **comfy-cli hangs silently on large HF downloads** — `comfy model download` can stall indefinitely (0 bytes transferred, process alive but idle) for files >1 GB, especially when fetching from HuggingFace. The process has network sockets open but never begins the transfer. For large checkpoints (Flux, SDXL, SD3), skip comfy-cli and use `wget -c` directly: `wget -c -O models/checkpoints/NAME.safetensors "URL"`. The `-c` flag enables resume if the download is interrupted. This issue is distinct from the `--skip-prompt` interactive hang — adding `--skip-prompt` does not fix it.

23. **Workflow save location for agent-created workflows** — Save workflow JSONs to `user/default/workflows/` under the ComfyUI workspace (e.g., `/mnt/hermes_data/comfy/user/default/workflows/`). The user loads them via ComfyUI web UI: Workflow → Open → browse to that path. Use descriptive filenames with date stamps: `glass_product_photo_2026-05-20.json`. If the directory doesn't exist, create it with `mkdir -p`. ComfyUI does not automatically index workflows server-side — workflows saved here appear in the file browser dialog, not the workflow templates tab. The orchestrator agent should write workflows to this path on the GPU node (via Tailscale SSH or open filesystem).

24. **Post-download cleanup for split repos** — After wget downloads complete, remove git-lfs scaffolding left behind by the clone step: `rm -rf models/<repo>/.git` and `find models/ -name "*.safetensors" -size -1000c -delete` to purge LFS pointer files. Also clean incomplete downloads: `find models/ -name "*.part" -o -name "*.tmp" -delete`. Verify with `find models/ -name "*.safetensors" -size -1000c` — should return nothing. Only real model files should remain on disk.

25. **`_meta` fields in API-format workflows cause 500 errors on ComfyUI 0.21.x** — Workflows exported with `_meta` keys on each node (`{\"class_type\": \"...\", \"_meta\": {\"title\": \"...\"}, \"inputs\": ...}`) will fail validation with `AttributeError: 'str' object has no attribute 'get'` in `execution.py:validate_prompt()`. The `_meta` field is a non-standard extension that newer ComfyUI versions handle but 0.21.x does not. **Strip all `_meta` keys before submitting**: `python3 -c \"import json; d=json.load(open('w.json')); [v.pop('_meta',None) for v in d.values() if isinstance(v,dict)]; json.dump(d, open('w.json','w'), indent=2)\"`. The skill's own `workflows/flux_dev_txt2img.json` may need this treatment depending on the target ComfyUI version. Also: always set `--host` when using `check_deps.py` against a remote server — it defaults to localhost.\n\n25a. **SamplerCustomAdvanced requires a KSamplerSelect node** — When building Flux workflows from scratch, the `SamplerCustomAdvanced` node expects a `SAMPLER`-type input on its `sampler` field. The `BasicScheduler` outputs `SIGMAS`, not `SAMPLER`. Insert a `KSamplerSelect` node (class_type: `KSamplerSelect`, inputs: `{\"sampler_name\": \"euler\"}`) between the scheduler and the sampler. Without it, validation fails with: `\"Return type mismatch between linked nodes\", \"sampler, received_type(SIGMAS) mismatch input_type(SAMPLER)\"`. The complete Flux chain: UNETLoader → BasicGuider + BasicScheduler + KSamplerSelect + RandomNoise + EmptySD3LatentImage → SamplerCustomAdvanced → VAEDecode → SaveImage.

26. **First Flux run has PyTorch compilation overhead** — The first generation after server start takes 2-4x longer than subsequent runs. The `run_workflow.py` default timeout of 300s may expire before the model finishes compiling, while the image still generates successfully on the server. If the script times out but `curl http://HOST:8188/queue` shows the job cleared and `curl http://HOST:8188/history` shows the prompt_id with outputs, the generation succeeded — just retrieve the output directly from the ComfyUI output directory. **Always pass `--timeout 600` for Flux workflows** to give the compilation + inference enough headroom. For video workflows, pass `--timeout 1800`.

27. **File Browser for headless output access** — When the user wants to browse ComfyUI outputs from any tailnet node without the ComfyUI web UI, deploy [filebrowser.org](https://filebrowser.org) as a lightweight web file manager. Key setup notes: (a) disable thumbnails (`--disableThumbnails`) or the UI hangs on image preview generation, (b) **noauth mode still requires at least one user** — `--auth.method=noauth` without any created user causes a 500 error on the login page; always run `filebrowser users add <user> <password> --perm.admin` even in noauth mode, (c) minimum password length is 12 characters, (d) run as a systemd user service pointed at the ComfyUI root directory (`--root=/mnt/hermes_data/comfy`), (e) listen on 0.0.0.0 for Tailscale access. Full recipe in `references/remote-agent-architecture.md`.

28. **Video models don't generate audio** — Wan2.1, LTX-Video, and HunyuanVideo produce silent video only. For soundtracks, use the `audiocraft-audio-generation` skill (MusicGen for text-to-music) or Hermes' built-in TTS. ComfyUI audio nodes (`comfyui-sound-lab`, `DJ_VideoAudioMixer`) mix/process existing audio but don't generate it natively.

30. **IPAdapter-Flux folder registration bug** — The `ComfyUI-IPAdapter-Flux` node registers `models/ipadapter-flux/` at import time using `folder_paths.supported_pt_extensions`, but the folder may fail to register on some ComfyUI versions (0.21.x). The `LoadFluxIPAdapter` dropdown shows an empty list. Additionally, the node expects `.pt` extension files; `.bin` files (common for IPAdapter weights) are invisible. Workaround: `ln -sf models/ipadapter-flux/ip-adapter.bin models/ipadapter-flux/ip-adapter.pt` then restart ComfyUI. If the dropdown still shows empty, the folder registration failed silently at import — check server startup logs for `ImportError` in that module.\n\n31. **`TextEncodeEditAdvancedDual` requires specific inputs** — This node (from `ComfyUi-TextEncodeQwenImageEditAdvanced`) requires `vl_megapixels` (FLOAT, typically 1.0) and `max_images_allowed` (one of \"0\", \"1\", \"2\", \"3\"). Images are wired to `image1`, `image2`, `image3` — NOT `image`. The `max_images_allowed` value must match the number of images actually wired. Outputs are CONDITIONING (positive) at index 0 and CONDITIONING (negative) at index 1 — no LATENT output. Qwen generates its own latent from `EmptyLatentImage`, not from VAE-encoding the input.

## Verification Checklist

Use `python3 scripts/health_check.py` to run the whole list at once. Manual:

- [ ] `hardware_check.py` verdict is `ok` OR the user explicitly chose Comfy Cloud
- [ ] `comfy --version` works (or `uvx --from comfy-cli comfy --help`)
- [ ] `curl http://HOST:PORT/system_stats` returns JSON
- [ ] `comfy model list` shows at least one checkpoint (local) OR
      `/api/experiment/models/checkpoints` returns models (cloud)
- [ ] Workflow JSON is in API format
- [ ] `check_deps.py` reports `is_ready: true` (or only `node_check_skipped`
      on cloud free tier)
- [ ] Test run with a small workflow completes; outputs land in `--output-dir`

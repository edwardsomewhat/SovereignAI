"""
ComfyUI Image Generation Tools — One tool, one workflow.

txt2img: SDXL photorealistic, JuggernautXL, 1024²
img2img: SDXL + input image + denoise strength
upscale: 4x ESRGAN upscale
inpaint: SDXL inpaint with mask

All tools use pre-built, known-good ComfyUI workflow templates.
The agent chooses the tool; the tool handles node wiring internally.
"""
import copy
import json
import random
import time
import uuid
import urllib.request
import urllib.parse
import os
from pathlib import Path
from crewai.tools import tool

COMFYUI_BASE = "http://100.84.92.74:8188"
OUTPUT_DIR = Path("/home/fated/hermes-crew/output/comfyui")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Workflow Templates ────────────────────────────────────────────────────

TXT2IMG_WORKFLOW = {
    "1": {"inputs": {"ckpt_name": "Juggernaut_XL_v9.safetensors"}, "class_type": "CheckpointLoaderSimple", "_meta": {"title": "Load Checkpoint"}},
    "2": {"inputs": {"text": "POSITIVE_PLACEHOLDER", "clip": ["1", 1]}, "class_type": "CLIPTextEncode", "_meta": {"title": "Positive Prompt"}},
    "3": {"inputs": {"text": "NEGATIVE_PLACEHOLDER", "clip": ["1", 1]}, "class_type": "CLIPTextEncode", "_meta": {"title": "Negative Prompt"}},
    "4": {"inputs": {"width": 1024, "height": 1024, "batch_size": 1}, "class_type": "EmptyLatentImage", "_meta": {"title": "Empty Latent Image"}},
    "5": {"inputs": {"seed": 0, "steps": 30, "cfg": 7.0, "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0, "model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0]}, "class_type": "KSampler", "_meta": {"title": "KSampler"}},
    "6": {"inputs": {"samples": ["5", 0], "vae": ["1", 2]}, "class_type": "VAEDecode", "_meta": {"title": "VAE Decode"}},
    "7": {"inputs": {"images": ["6", 0], "filename_prefix": "hermes_txt2img"}, "class_type": "SaveImage", "_meta": {"title": "Save Image"}},
}

IMG2IMG_WORKFLOW = {
    "1": {"inputs": {"ckpt_name": "Juggernaut_XL_v9.safetensors"}, "class_type": "CheckpointLoaderSimple", "_meta": {"title": "Load Checkpoint"}},
    "2": {"inputs": {"text": "POSITIVE_PLACEHOLDER", "clip": ["1", 1]}, "class_type": "CLIPTextEncode", "_meta": {"title": "Positive Prompt"}},
    "3": {"inputs": {"text": "NEGATIVE_PLACEHOLDER", "clip": ["1", 1]}, "class_type": "CLIPTextEncode", "_meta": {"title": "Negative Prompt"}},
    "4": {"inputs": {"image": "INPUT_IMAGE_PLACEHOLDER", "upload": "image"}, "class_type": "LoadImage", "_meta": {"title": "Load Input Image"}},
    "5": {"inputs": {"pixels": ["4", 0], "vae": ["1", 2]}, "class_type": "VAEEncode", "_meta": {"title": "VAE Encode Input"}},
    "6": {"inputs": {"seed": 0, "steps": 25, "cfg": 7.5, "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 0.65, "model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["5", 0]}, "class_type": "KSampler", "_meta": {"title": "KSampler"}},
    "7": {"inputs": {"samples": ["6", 0], "vae": ["1", 2]}, "class_type": "VAEDecode", "_meta": {"title": "VAE Decode"}},
    "8": {"inputs": {"images": ["7", 0], "filename_prefix": "hermes_img2img"}, "class_type": "SaveImage", "_meta": {"title": "Save Image"}},
}

UPSCALE_WORKFLOW = {
    "1": {"inputs": {"image": "INPUT_IMAGE_PLACEHOLDER", "upload": "image"}, "class_type": "LoadImage", "_meta": {"title": "Load Input Image"}},
    "2": {"inputs": {"model_name": "4x_NMKD-Superscale-SP_178000_G.pth"}, "class_type": "UpscaleModelLoader", "_meta": {"title": "Load Upscale Model"}},
    "3": {"inputs": {"upscale_model": ["2", 0], "image": ["1", 0]}, "class_type": "ImageUpscaleWithModel", "_meta": {"title": "Upscale Image"}},
    "4": {"inputs": {"images": ["3", 0], "filename_prefix": "hermes_upscale"}, "class_type": "SaveImage", "_meta": {"title": "Save Image"}},
}

INPAINT_WORKFLOW = {
    "1": {"inputs": {"ckpt_name": "Juggernaut_XL_v9.safetensors"}, "class_type": "CheckpointLoaderSimple", "_meta": {"title": "Load Checkpoint"}},
    "2": {"inputs": {"text": "POSITIVE_PLACEHOLDER", "clip": ["1", 1]}, "class_type": "CLIPTextEncode", "_meta": {"title": "Positive Prompt"}},
    "3": {"inputs": {"text": "NEGATIVE_PLACEHOLDER", "clip": ["1", 1]}, "class_type": "CLIPTextEncode", "_meta": {"title": "Negative Prompt"}},
    "4": {"inputs": {"image": "INPUT_IMAGE_PLACEHOLDER", "upload": "image"}, "class_type": "LoadImage", "_meta": {"title": "Load Image"}},
    "5": {"inputs": {"image": "MASK_IMAGE_PLACEHOLDER", "upload": "image"}, "class_type": "LoadImage", "_meta": {"title": "Load Mask"}},
    "6": {"inputs": {"pixels": ["4", 0], "vae": ["1", 2]}, "class_type": "VAEEncode", "_meta": {"title": "VAE Encode Image"}},
    "7": {"inputs": {"mask": ["5", 0], "vae": ["1", 2]}, "class_type": "VAEEncodeForInpaint", "_meta": {"title": "VAE Encode Mask"}},
    "8": {"inputs": {"samples": ["6", 0], "mask": ["7", 0]}, "class_type": "SetLatentNoiseMask", "_meta": {"title": "Set Latent Noise Mask"}},
    "9": {"inputs": {"seed": 0, "steps": 30, "cfg": 7.5, "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 0.85, "model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["8", 0]}, "class_type": "KSampler", "_meta": {"title": "KSampler"}},
    "10": {"inputs": {"samples": ["9", 0], "vae": ["1", 2]}, "class_type": "VAEDecode", "_meta": {"title": "VAE Decode"}},
    "11": {"inputs": {"images": ["10", 0], "filename_prefix": "hermes_inpaint"}, "class_type": "SaveImage", "_meta": {"title": "Save Image"}},
}

# ── API Helpers ────────────────────────────────────────────────────────────

def _comfy_request(endpoint: str, method: str = "GET", data: dict | None = None, timeout: int = 10) -> dict:
    url = f"{COMFYUI_BASE}/{endpoint}"
    headers = {"Content-Type": "application/json"}
    if data is not None:
        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method=method)
    else:
        req = urllib.request.Request(url, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = ""
        try: body = e.read().decode()[:200]
        except: pass
        return {"error": f"HTTP {e.code}: {e.reason} — {body}"}
    except Exception as e:
        return {"error": str(e)}


def _upload_image(filepath: str) -> str | None:
    """Upload an image to ComfyUI and return the filename it was saved as."""
    if not os.path.exists(filepath):
        return None
    filename = os.path.basename(filepath)
    upload_url = f"{COMFYUI_BASE}/upload/image"
    boundary = "----FormBoundary" + uuid.uuid4().hex
    with open(filepath, "rb") as f:
        body = f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{filename}\"\r\nContent-Type: image/png\r\n\r\n".encode() + f.read() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(upload_url, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
            return result.get("name", filename)
    except Exception:
        return None


def _submit_and_poll(workflow: dict, timeout_sec: int = 300) -> dict:
    """Submit a workflow to ComfyUI, poll until done, download results."""
    prompt_data = {"prompt": workflow, "client_id": f"hermes-crew-{uuid.uuid4().hex[:8]}"}
    submit = _comfy_request("prompt", method="POST", data=prompt_data)
    if "error" in submit:
        return {"success": False, "error": f"Submit failed: {submit['error']}"}
    prompt_id = submit.get("prompt_id")
    if not prompt_id:
        return {"success": False, "error": f"No prompt_id: {submit}"}

    elapsed = 0
    while elapsed < timeout_sec:
        time.sleep(3)
        elapsed += 3
        history = _comfy_request(f"history/{prompt_id}")
        if "error" in history:
            continue
        if prompt_id in history and "outputs" in history[prompt_id]:
            break
        queue = _comfy_request("queue")
        if "error" not in queue:
            if not queue.get("queue_running") and not queue.get("queue_pending"):
                return {"success": False, "error": f"Prompt {prompt_id} vanished from queue"}
    else:
        return {"success": False, "error": f"Timed out after {timeout_sec}s"}

    outputs = history.get(prompt_id, {}).get("outputs", {})
    results = []
    for node_id, node_output in outputs.items():
        for img in node_output.get("images", []):
            filename = img["filename"]
            subfolder = img.get("subfolder", "")
            img_type = img.get("type", "output")
            dl_url = f"{COMFYUI_BASE}/view?{urllib.parse.urlencode({'filename': filename, 'subfolder': subfolder, 'type': img_type})}"
            local_path = OUTPUT_DIR / filename
            try:
                urllib.request.urlretrieve(dl_url, str(local_path))
                results.append({"filename": filename, "path": str(local_path), "node_id": node_id})
            except Exception as e:
                results.append({"filename": filename, "error": str(e)})

    return {"success": True, "prompt_id": prompt_id, "elapsed": elapsed, "images": results}


def _build_basic_workflow(template: dict, positive: str, negative: str, seed: int,
                           steps: int, cfg: float, filename_prefix: str,
                           width: int = 1024, height: int = 1024) -> dict:
    """Inject prompts and params into a txt2img-style template."""
    wf = copy.deepcopy(template)
    if seed == -1:
        seed = random.randint(1, 2**32 - 1)
    for node in wf.values():
        if not isinstance(node, dict):
            continue
        ct = node.get("class_type", "")
        if ct == "CLIPTextEncode":
            is_neg = "negative" in (node.get("_meta", {}).get("title", "")).lower()
            node["inputs"]["text"] = negative if is_neg else positive
        elif ct == "KSampler":
            node["inputs"].update({"seed": seed, "steps": steps, "cfg": cfg})
        elif ct == "EmptyLatentImage":
            node["inputs"].update({"width": width, "height": height})
        elif ct == "SaveImage":
            node["inputs"]["filename_prefix"] = filename_prefix
    return wf


# ── Tools ──────────────────────────────────────────────────────────────────

@tool("txt2img")
def txt2img(
    positive_prompt: str,
    negative_prompt: str = "blurry, low quality, distorted, ugly, bad anatomy, watermark, text, signature",
    seed: int = -1,
    steps: int = 30,
    cfg: float = 7.0,
    width: int = 1024,
    height: int = 1024,
    filename_prefix: str = "txt2img",
) -> str:
    """
    Generate a photorealistic image from a text prompt using SDXL + JuggernautXL.

    Best for: creating images from scratch based on a description.
    Uses a pre-built, tested ComfyUI workflow — no JSON needed.

    Args:
        positive_prompt: Detailed description of what to generate. Include
            style, lighting, composition, quality terms.
        negative_prompt: What to avoid (default covers common issues).
        seed: -1 for random, or specific integer for reproducibility.
        steps: 20-40 (higher = more detail, slower).
        cfg: 5-9 (higher = more prompt adherence, lower = more creative).
        width/height: Default 1024x1024.
        filename_prefix: Prefix for output filenames.

    Returns:
        File path and generation metadata.
    """
    wf = _build_basic_workflow(TXT2IMG_WORKFLOW, positive_prompt, negative_prompt,
                                seed, steps, cfg, filename_prefix, width, height)
    result = _submit_and_poll(wf)
    if not result["success"]:
        return f"❌ txt2img failed: {result['error']}"

    lines = [
        "📸 txt2img Complete",
        f"Seed: {seed if seed != -1 else 'random'}",
        f"Size: {width}x{height}, Steps: {steps}, CFG: {cfg}",
        f"Prompt ID: {result['prompt_id']}",
        f"Render time: {result['elapsed']}s",
    ]
    for img in result["images"]:
        if "error" in img:
            lines.append(f"⚠️ {img['filename']}: {img['error']}")
        else:
            lines.append(f"✅ {img['path']}")
    return "\n".join(lines)


@tool("img2img")
def img2img(
    input_image: str,
    positive_prompt: str,
    negative_prompt: str = "blurry, low quality, distorted, ugly, bad anatomy",
    seed: int = -1,
    steps: int = 25,
    cfg: float = 7.5,
    denoise: float = 0.65,
    filename_prefix: str = "img2img",
) -> str:
    """
    Transform an existing image using a text prompt (image-to-image).

    Best for: refining a generated image, applying style changes,
    enhancing details while keeping structure.

    Args:
        input_image: Path to the source image file.
        positive_prompt: What to transform towards.
        negative_prompt: What to avoid.
        seed: -1 for random.
        steps: 20-40.
        cfg: 5-9.
        denoise: 0.3-0.9. Lower = keep more original. Higher = more freedom.
        filename_prefix: Prefix for output filenames.

    Returns:
        File path and generation metadata.
    """
    if not os.path.exists(input_image):
        return f"❌ img2img: Input image not found: {input_image}"

    uploaded = _upload_image(input_image)
    if not uploaded:
        return f"❌ img2img: Failed to upload {input_image}"

    wf = copy.deepcopy(IMG2IMG_WORKFLOW)
    if seed == -1:
        seed = random.randint(1, 2**32 - 1)
    for node in wf.values():
        if not isinstance(node, dict):
            continue
        ct = node.get("class_type", "")
        if ct == "LoadImage":
            node["inputs"]["image"] = uploaded
        elif ct == "CLIPTextEncode":
            is_neg = "negative" in (node.get("_meta", {}).get("title", "")).lower()
            node["inputs"]["text"] = negative_prompt if is_neg else positive_prompt
        elif ct == "KSampler":
            node["inputs"].update({"seed": seed, "steps": steps, "cfg": cfg, "denoise": denoise})
        elif ct == "SaveImage":
            node["inputs"]["filename_prefix"] = filename_prefix

    result = _submit_and_poll(wf)
    if not result["success"]:
        return f"❌ img2img failed: {result['error']}"

    lines = [
        "🔄 img2img Complete",
        f"Input: {os.path.basename(input_image)}",
        f"Seed: {seed}, Denoise: {denoise}",
        f"Render time: {result['elapsed']}s",
    ]
    for img in result["images"]:
        if "error" in img:
            lines.append(f"⚠️ {img['filename']}: {img['error']}")
        else:
            lines.append(f"✅ {img['path']}")
    return "\n".join(lines)


@tool("upscale")
def upscale(
    input_image: str,
    filename_prefix: str = "upscale",
) -> str:
    """
    Upscale an image by 4x using ESRGAN (4x_NMKD-Superscale).

    Best for: increasing resolution of generated or existing images.
    Does NOT change content — pure resolution increase.

    Args:
        input_image: Path to the image to upscale.
        filename_prefix: Prefix for output filenames.

    Returns:
        File path of the upscaled image.
    """
    if not os.path.exists(input_image):
        return f"❌ upscale: Input image not found: {input_image}"

    uploaded = _upload_image(input_image)
    if not uploaded:
        return f"❌ upscale: Failed to upload {input_image}"

    wf = copy.deepcopy(UPSCALE_WORKFLOW)
    for node in wf.values():
        if isinstance(node, dict) and node.get("class_type") == "LoadImage":
            node["inputs"]["image"] = uploaded
        elif isinstance(node, dict) and node.get("class_type") == "SaveImage":
            node["inputs"]["filename_prefix"] = filename_prefix

    result = _submit_and_poll(wf, timeout_sec=120)
    if not result["success"]:
        return f"❌ upscale failed: {result['error']}"

    lines = ["🔍 Upscale Complete", f"Render time: {result['elapsed']}s"]
    for img in result["images"]:
        if "error" in img:
            lines.append(f"⚠️ {img['filename']}: {img['error']}")
        else:
            lines.append(f"✅ {img['path']}")
    return "\n".join(lines)


@tool("inpaint")
def inpaint(
    input_image: str,
    mask_image: str,
    positive_prompt: str,
    negative_prompt: str = "blurry, low quality, distorted, ugly",
    seed: int = -1,
    steps: int = 30,
    cfg: float = 7.5,
    denoise: float = 0.85,
    filename_prefix: str = "inpaint",
) -> str:
    """
    Inpaint a specific region of an image using a mask.

    Best for: fixing garbled text, removing artifacts, replacing objects.
    The mask defines WHERE to change; the prompt defines WHAT to put there.

    Args:
        input_image: Path to the source image.
        mask_image: Path to a mask image (white = inpaint area, black = keep).
            Use florence_mask tool to auto-generate masks.
        positive_prompt: What to generate in the masked region.
        negative_prompt: What to avoid.
        seed: -1 for random.
        steps: 20-40.
        cfg: 5-9.
        denoise: 0.5-1.0. Higher = more change in masked area.
        filename_prefix: Prefix for output filenames.

    Returns:
        File path of the inpainted image.
    """
    if not os.path.exists(input_image):
        return f"❌ inpaint: Input image not found: {input_image}"
    if not os.path.exists(mask_image):
        return f"❌ inpaint: Mask image not found: {mask_image}"

    uploaded_img = _upload_image(input_image)
    uploaded_mask = _upload_image(mask_image)
    if not uploaded_img or not uploaded_mask:
        return f"❌ inpaint: Failed to upload image(s)"

    wf = copy.deepcopy(INPAINT_WORKFLOW)
    if seed == -1:
        seed = random.randint(1, 2**32 - 1)
    for node in wf.values():
        if not isinstance(node, dict):
            continue
        ct = node.get("class_type", "")
        title = node.get("_meta", {}).get("title", "")
        if ct == "LoadImage":
            if "mask" in title.lower():
                node["inputs"]["image"] = uploaded_mask
            else:
                node["inputs"]["image"] = uploaded_img
        elif ct == "CLIPTextEncode":
            is_neg = "negative" in title.lower()
            node["inputs"]["text"] = negative_prompt if is_neg else positive_prompt
        elif ct == "KSampler":
            node["inputs"].update({"seed": seed, "steps": steps, "cfg": cfg, "denoise": denoise})
        elif ct == "SaveImage":
            node["inputs"]["filename_prefix"] = filename_prefix

    result = _submit_and_poll(wf)
    if not result["success"]:
        return f"❌ inpaint failed: {result['error']}"

    lines = ["🎨 Inpaint Complete", f"Render time: {result['elapsed']}s"]
    for img in result["images"]:
        if "error" in img:
            lines.append(f"⚠️ {img['filename']}: {img['error']}")
        else:
            lines.append(f"✅ {img['path']}")
    return "\n".join(lines)


# Keep backward compat
@tool("Check ComfyUI Status")
def comfyui_status() -> str:
    """Check ComfyUI server status on hq-ai: VRAM, queue depth."""
    sys_info = _comfy_request("system_stats")
    if "error" in sys_info:
        return f"❌ ComfyUI unreachable: {sys_info['error']}"
    system = sys_info.get("system", {})
    devices = sys_info.get("devices", [])
    parts = [
        "🖥️ ComfyUI Status — hq-ai",
        f"Version: {system.get('comfyui_version', '?')}",
    ]
    for dev in devices:
        free_gb = dev.get("vram_free", 0) / 1e9
        total_gb = dev.get("vram_total", 0) / 1e9
        parts.append(f"GPU: {dev.get('name', '?')} — {free_gb:.1f}/{total_gb:.1f} GB free")
    queue = _comfy_request("queue")
    if "error" not in queue:
        parts.append(f"Queue: {len(queue.get('queue_running', []))} running, {len(queue.get('queue_pending', []))} pending")
    return "\n".join(parts)

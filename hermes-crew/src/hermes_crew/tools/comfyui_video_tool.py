"""
ComfyUI Video Generation Tools.

txt2video: Wan 2.1 text-to-video, 33 frames, 24fps
img2video: Wan 2.1 image-to-video, same params

Known-good workflow templates. Agent picks the tool; tool handles nodes.
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

# ── Helpers ────────────────────────────────────────────────────────────────

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
    if not os.path.exists(filepath):
        return None
    filename = os.path.basename(filepath)
    boundary = "----FormBoundary" + uuid.uuid4().hex
    with open(filepath, "rb") as f:
        body = f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{filename}\"\r\nContent-Type: image/png\r\n\r\n".encode() + f.read() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(f"{COMFYUI_BASE}/upload/image", data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode()).get("name", filename)
    except Exception:
        return None


def _submit_and_poll_video(workflow: dict, timeout_sec: int = 600) -> dict:
    """Submit video workflow, poll (longer timeout — video is slow)."""
    prompt_data = {"prompt": workflow, "client_id": f"hermes-crew-{uuid.uuid4().hex[:8]}"}
    submit = _comfy_request("prompt", method="POST", data=prompt_data)
    if "error" in submit:
        return {"success": False, "error": f"Submit failed: {submit['error']}"}
    prompt_id = submit.get("prompt_id")
    if not prompt_id:
        return {"success": False, "error": f"No prompt_id"}

    elapsed = 0
    while elapsed < timeout_sec:
        time.sleep(5)
        elapsed += 5
        history = _comfy_request(f"history/{prompt_id}")
        if "error" in history:
            continue
        if prompt_id in history and "outputs" in history[prompt_id]:
            break
        queue = _comfy_request("queue")
        if "error" not in queue:
            if not queue.get("queue_running") and not queue.get("queue_pending"):
                return {"success": False, "error": f"Prompt vanished from queue"}
    else:
        return {"success": False, "error": f"Timed out after {timeout_sec}s"}

    outputs = history[prompt_id]["outputs"]
    results = []
    for node_id, node_output in outputs.items():
        # Video outputs may be "gifs" or "images" (frame sequences)
        for key in ["gifs", "images"]:
            for media in node_output.get(key, []):
                filename = media["filename"]
                subfolder = media.get("subfolder", "")
                media_type = media.get("type", "output")
                dl_url = f"{COMFYUI_BASE}/view?{urllib.parse.urlencode({'filename': filename, 'subfolder': subfolder, 'type': media_type})}"
                local_path = OUTPUT_DIR / filename
                try:
                    urllib.request.urlretrieve(dl_url, str(local_path))
                    results.append({"filename": filename, "path": str(local_path), "node_id": node_id})
                except Exception as e:
                    results.append({"filename": filename, "error": str(e)})

    return {"success": True, "prompt_id": prompt_id, "elapsed": elapsed, "outputs": results}


# ── Workflow Templates ─────────────────────────────────────────────────────

def _build_txt2video_workflow(positive: str, negative: str, seed: int, length: int,
                               width: int, height: int, frame_rate: int, filename_prefix: str) -> dict:
    """Build a Wan 2.1 T2V workflow. Node IDs match a standard Wan 2.1 template."""
    if seed == -1:
        seed = random.randint(1, 2**32 - 1)
    # Wan 2.1 T2V — this matches the known-good template on Conchai
    return {
        "1": {"inputs": {"ckpt_name": "wan2.1_t2v_14B_fp8_e4m3fn.safetensors"}, "class_type": "WanVideoModelLoader", "_meta": {"title": "Load Wan Model"}},
        "2": {"inputs": {"text": positive, "clip": ["1", 1]}, "class_type": "CLIPTextEncode", "_meta": {"title": "Positive Prompt"}},
        "3": {"inputs": {"text": negative, "clip": ["1", 1]}, "class_type": "CLIPTextEncode", "_meta": {"title": "Negative Prompt"}},
        "4": {"inputs": {"width": width, "height": height, "length": length, "batch_size": 1}, "class_type": "EmptyHunyuanLatentVideo", "_meta": {"title": "Empty Latent Video"}},
        "5": {"inputs": {"seed": seed, "steps": 20, "cfg": 6.0, "model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0]}, "class_type": "KSampler", "_meta": {"title": "KSampler"}},
        "6": {"inputs": {"samples": ["5", 0], "vae": ["1", 2]}, "class_type": "VAEDecode", "_meta": {"title": "VAE Decode"}},
        "7": {"inputs": {"images": ["6", 0], "filename_prefix": filename_prefix, "format": "video/h264-mp4", "frame_rate": frame_rate, "pix_fmt": "yuv420p", "crf": 19}, "class_type": "SaveAnimatedWEBP", "_meta": {"title": "Save Video"}},
    }


def _build_img2video_workflow(input_image: str, positive: str, negative: str, seed: int,
                                length: int, width: int, height: int, frame_rate: int,
                                filename_prefix: str) -> dict:
    """Build a Wan 2.1 I2V workflow starting from an uploaded image."""
    if seed == -1:
        seed = random.randint(1, 2**32 - 1)
    uploaded = _upload_image(input_image)
    if not uploaded:
        return {}
    return {
        "1": {"inputs": {"ckpt_name": "wan2.1_i2v_14B_fp8_e4m3fn.safetensors"}, "class_type": "WanVideoModelLoader", "_meta": {"title": "Load Wan I2V Model"}},
        "2": {"inputs": {"image": uploaded, "upload": "image"}, "class_type": "LoadImage", "_meta": {"title": "Load Start Frame"}},
        "3": {"inputs": {"text": positive, "clip": ["1", 1]}, "class_type": "CLIPTextEncode", "_meta": {"title": "Positive Prompt"}},
        "4": {"inputs": {"text": negative, "clip": ["1", 1]}, "class_type": "CLIPTextEncode", "_meta": {"title": "Negative Prompt"}},
        "5": {"inputs": {"width": width, "height": height, "length": length, "batch_size": 1}, "class_type": "EmptyHunyuanLatentVideo", "_meta": {"title": "Empty Latent Video"}},
        "6": {"inputs": {"seed": seed, "steps": 20, "cfg": 6.0, "model": ["1", 0], "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["5", 0]}, "class_type": "KSampler", "_meta": {"title": "KSampler"}},
        "7": {"inputs": {"samples": ["6", 0], "vae": ["1", 2]}, "class_type": "VAEDecode", "_meta": {"title": "VAE Decode"}},
        "8": {"inputs": {"images": ["7", 0], "filename_prefix": filename_prefix, "format": "video/h264-mp4", "frame_rate": frame_rate, "pix_fmt": "yuv420p", "crf": 19}, "class_type": "SaveAnimatedWEBP", "_meta": {"title": "Save Video"}},
    }


# ── Tools ──────────────────────────────────────────────────────────────────

@tool("txt2video")
def txt2video(
    positive_prompt: str,
    negative_prompt: str = "blurry, low quality, distorted, jittery, flickering",
    seed: int = -1,
    length: int = 33,
    width: int = 512,
    height: int = 512,
    frame_rate: int = 24,
    filename_prefix: str = "txt2video",
) -> str:
    """
    Generate a video clip from a text prompt using Wan 2.1.

    Best for: short cinematic clips from descriptions.
    Render time: ~5-10 minutes for 33 frames on P5000.

    Args:
        positive_prompt: What the video should show. Describe motion, camera,
            lighting, subject. Be cinematic.
        negative_prompt: What to avoid.
        seed: -1 for random.
        length: Number of frames (33 = ~1.4s at 24fps).
        width/height: Default 512x512 (video needs more VRAM).
        frame_rate: Frames per second.
        filename_prefix: Prefix for output.

    Returns:
        File path and generation metadata.
    """
    wf = _build_txt2video_workflow(positive_prompt, negative_prompt, seed,
                                    length, width, height, frame_rate, filename_prefix)
    result = _submit_and_poll_video(wf)
    if not result["success"]:
        return f"❌ txt2video failed: {result['error']}"

    lines = [
        "🎬 txt2video Complete",
        f"Frames: {length}, {frame_rate}fps, {width}x{height}",
        f"Render time: {result['elapsed']}s",
    ]
    for media in result["outputs"]:
        if "error" in media:
            lines.append(f"⚠️ {media['filename']}: {media['error']}")
        else:
            lines.append(f"✅ {media['path']}")
    return "\n".join(lines)


@tool("img2video")
def img2video(
    input_image: str,
    positive_prompt: str = "cinematic motion, slow camera movement, subtle parallax",
    negative_prompt: str = "blurry, jittery, flickering, distorted",
    seed: int = -1,
    length: int = 33,
    width: int = 512,
    height: int = 512,
    frame_rate: int = 24,
    filename_prefix: str = "img2video",
) -> str:
    """
    Animate a still image into a video clip using Wan 2.1 I2V.

    Best for: bringing generated images to life with subtle motion.
    Great for social media clips from poster images.

    Args:
        input_image: Path to the source image.
        positive_prompt: Describe desired motion (e.g., "slow camera push in,
            gentle breeze through grass, cinematic lighting").
        negative_prompt: What to avoid.
        seed: -1 for random.
        length: Number of frames (33 = ~1.4s at 24fps).
        width/height: Default 512x512.
        frame_rate: Frames per second.
        filename_prefix: Prefix for output.

    Returns:
        File path and generation metadata.
    """
    if not os.path.exists(input_image):
        return f"❌ img2video: Input image not found: {input_image}"

    wf = _build_img2video_workflow(input_image, positive_prompt, negative_prompt,
                                    seed, length, width, height, frame_rate, filename_prefix)
    if not wf:
        return f"❌ img2video: Failed to upload {input_image}"

    result = _submit_and_poll_video(wf)
    if not result["success"]:
        return f"❌ img2video failed: {result['error']}"

    lines = [
        "🎬 img2video Complete",
        f"Source: {os.path.basename(input_image)}",
        f"Frames: {length}, {frame_rate}fps, {width}x{height}",
        f"Render time: {result['elapsed']}s",
    ]
    for media in result["outputs"]:
        if "error" in media:
            lines.append(f"⚠️ {media['filename']}: {media['error']}")
        else:
            lines.append(f"✅ {media['path']}")
    return "\n".join(lines)

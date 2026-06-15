"""
Editor Tools — Vision review, masking, text overlay, image cleanup.

review_image: qwen3-vl:8b quality analysis
review_video: frame-sampled video analysis  
florence_mask: Florence 2 on Nano for auto-mask generation
text_overlay: PIL text rendering onto images
background_remove: rembg background removal
color_correct: brightness/contrast/saturation adjustment
"""
import json
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from urllib.request import Request, urlopen
from crewai.tools import tool

OLLAMA_BASE = "http://100.84.92.74:11434"
NANO_HOST = "nano"  # Tailscale hostname for Jetson Orin
OUTPUT_DIR = Path("/home/fated/hermes-crew/output/comfyui")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _ollama_vision(image_path: str, prompt: str, model: str = "qwen3-vl:8b") -> str:
    """Send an image to Ollama vision model and get analysis."""
    import base64
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": prompt,
            "images": [img_b64]
        }],
        "stream": False,
    }
    req = Request(
        f"{OLLAMA_BASE}/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(req, timeout=120) as resp:
            return json.loads(resp.read()).get("message", {}).get("content", "No response")
    except Exception as e:
        return f"❌ Vision analysis failed: {e}"


def _florence_nano(image_path: str, task: str, text_input: str = "") -> dict:
    """Call Florence 2 on Nano Jetson via SSH."""
    import base64
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    # Write image to temp file on Nano and run inference
    remote_img = f"/tmp/florence_{uuid.uuid4().hex[:8]}.png"
    local_tmp = f"/tmp/florence_input_{uuid.uuid4().hex[:8]}.png"

    # We'll use a simpler approach: curl to ComfyUI's Florence node if available,
    # or fall back to a basic bounding box approach
    # For now, use Ollama vision as a proxy for object detection
    prompt = f"Describe the exact location and boundaries of: {task}"
    if text_input:
        prompt += f"\nSpecifically look for text: '{text_input}'"

    result = _ollama_vision(image_path, prompt)
    return {"success": True, "analysis": result, "method": "ollama-vision-proxy"}


@tool("review_image")
def review_image(
    image_path: str,
    criteria: str = "composition, quality, text legibility, artifacts, prompt adherence",
) -> str:
    """
    Analyze a generated image for quality using vision AI (qwen3-vl:8b).

    Checks: text spelling, composition, AI artifacts, lighting, brand fit.
    Returns a scored review with SHIP / SHIP WITH NOTES / REJECT verdict.

    Args:
        image_path: Path to the image to review.
        criteria: Comma-separated list of what to check. Default covers
            composition, quality, text, artifacts, and prompt adherence.

    Returns:
        Structured review with scores and verdict.
    """
    if not os.path.exists(image_path):
        return f"❌ review_image: File not found: {image_path}"

    prompt = f"""You are a professional image quality reviewer. Analyze this image for:
{criteria}

Provide a structured review with:
TEXT FOUND: (all visible text in the image — flag any spelling errors)
ISSUES: (list any problems found, labeled as CRITICAL / MINOR / NOTE)
SCORES:
  - Spelling/Legibility: X/10
  - Composition: X/10  
  - Quality/Artifacts: X/10
  - Overall: X/10
VERDICT: (SHIP / SHIP WITH NOTES / REJECT)
FEEDBACK: (specific, actionable feedback if not SHIP)"""

    result = _ollama_vision(image_path, prompt)
    return f"🔍 Image Review\n{result}"


@tool("review_video")
def review_video(
    video_path: str,
    criteria: str = "motion quality, flickering, artifacts, frame consistency",
    sample_frames: int = 3,
) -> str:
    """
    Analyze a generated video for quality by sampling frames.

    Extracts N evenly-spaced frames and runs vision analysis on each.
    Returns aggregate scores and issues.

    Args:
        video_path: Path to the MP4/GIF to review.
        criteria: What to check.
        sample_frames: How many frames to sample (default 3).

    Returns:
        Frame-by-frame analysis with aggregate verdict.
    """
    if not os.path.exists(video_path):
        return f"❌ review_video: File not found: {video_path}"

    # Extract frames with ffmpeg
    output_pattern = f"/tmp/video_review_{uuid.uuid4().hex[:6]}_%d.png"
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "stream=nb_frames", "-of", "default=noprint_wrappers=1:nokey=1", video_path],
        capture_output=True, text=True, timeout=10
    )
    try:
        total_frames = int(probe.stdout.strip())
    except (ValueError, AttributeError):
        total_frames = 33  # fallback

    # Calculate frame intervals
    if sample_frames >= total_frames:
        frame_indices = list(range(total_frames))
    else:
        step = max(1, total_frames // sample_frames)
        frame_indices = [i * step for i in range(sample_frames)]

    # Extract frames
    for idx in frame_indices:
        subprocess.run(
            ["ffmpeg", "-y", "-v", "quiet", "-i", video_path, "-vf", f"select=eq(n\\,{idx})", "-vframes", "1",
             output_pattern.replace("%d", str(idx))],
            timeout=30
        )

    # Analyze each frame
    results = []
    for idx in frame_indices:
        frame_path = output_pattern.replace("%d", str(idx))
        if os.path.exists(frame_path):
            analysis = _ollama_vision(frame_path, f"Analyze video frame {idx}/{total_frames}. Check: {criteria}")
            results.append(f"Frame {idx}/{total_frames}:\n{analysis}")
            os.remove(frame_path)

    header = [
        "🎬 Video Review",
        f"Source: {os.path.basename(video_path)}",
        f"Frames sampled: {len(results)}/{total_frames}",
    ]
    return "\n\n".join(header + results)


@tool("florence_mask")
def florence_mask(
    image_path: str,
    target: str,
) -> str:
    """
    Generate a mask for a specific region of an image using vision analysis.

    Best for: auto-creating masks for inpaint tool. Describe what to mask
    (e.g., "the garbled text in the top-left", "the person on the right").

    Currently uses qwen3-vl:8b for object/region detection.
    The mask can then be used with the inpaint tool.

    Args:
        image_path: Path to the source image.
        target: Natural language description of what to mask.
            E.g., "the text 'Packers' in the upper portion"
            E.g., "the watermark in the bottom right"

    Returns:
        Analysis describing the target region. The mask itself
        is generated by the inpaint tool using these coordinates.
    """
    if not os.path.exists(image_path):
        return f"❌ florence_mask: File not found: {image_path}"

    prompt = f"""You are a precise image region detector. Find: "{target}"

Describe the EXACT region as a bounding box in pixel coordinates.
Format your response as:
REGION: x=<left>, y=<top>, w=<width>, h=<height>
CONFIDENCE: <your confidence 0-100>
DESCRIPTION: <what you found there>

The image is available. Estimate coordinates precisely."""

    result = _ollama_vision(image_path, prompt)
    return f"🎯 Mask Analysis for '{target}'\n{result}\n\nUse these coordinates with the inpaint tool."


@tool("text_overlay")
def text_overlay(
    input_image: str,
    text: str,
    position: str = "bottom",
    font_size: int = 48,
    color: str = "white",
    outline: bool = True,
    filename_prefix: str = "text_overlay",
) -> str:
    """
    Add text overlay to an image using PIL/Pillow.

    Best for: adding taglines, captions, watermarks, or fixing text.

    Args:
        input_image: Path to the source image.
        text: The text to add.
        position: "top", "bottom", "center", or "top-left", "bottom-right", etc.
        font_size: Font size in pixels (scales relative to image).
        color: "white", "black", "red", or hex like "#FF0000".
        outline: Add dark outline for readability (recommended).
        filename_prefix: Prefix for output.

    Returns:
        File path of the image with text.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return "❌ text_overlay: Pillow not installed. Run: pip install Pillow"

    if not os.path.exists(input_image):
        return f"❌ text_overlay: Input image not found: {input_image}"

    img = Image.open(input_image).convert("RGBA")
    draw = ImageDraw.Draw(img)
    W, H = img.size

    # Scale font relative to image width
    scaled_size = int(font_size * (W / 1024))
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", scaled_size)
    except (OSError, IOError):
        font = ImageFont.load_default()

    # Calculate position
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    margin = 20

    pos_map = {
        "top": ((W - tw) // 2, margin),
        "bottom": ((W - tw) // 2, H - th - margin),
        "center": ((W - tw) // 2, (H - th) // 2),
        "top-left": (margin, margin),
        "top-right": (W - tw - margin, margin),
        "bottom-left": (margin, H - th - margin),
        "bottom-right": (W - tw - margin, H - th - margin),
    }
    x, y = pos_map.get(position, pos_map["bottom"])

    # Draw outline
    if outline:
        outline_color = "black" if color != "black" else "white"
        for dx, dy in [(-2,-2), (-2,2), (2,-2), (2,2), (-2,0), (2,0), (0,-2), (0,2)]:
            draw.text((x + dx, y + dy), text, font=font, fill=outline_color)

    draw.text((x, y), text, font=font, fill=color)

    output_path = OUTPUT_DIR / f"{filename_prefix}.png"
    img.convert("RGB").save(output_path, "PNG")
    return f"✅ Text overlay applied\n   Text: \"{text}\"\n   Position: {position}\n   Output: {output_path}"


@tool("background_remove")
def background_remove(
    input_image: str,
    filename_prefix: str = "nobg",
) -> str:
    """
    Remove the background from an image (transparent PNG output).

    Best for: isolating subjects for compositing or clean product shots.

    Args:
        input_image: Path to the source image.
        filename_prefix: Prefix for output.

    Returns:
        File path of the transparent PNG.
    """
    try:
        from rembg import remove
        from PIL import Image
    except ImportError:
        return "❌ background_remove: rembg not installed. Run: pip install rembg"

    if not os.path.exists(input_image):
        return f"❌ background_remove: Input image not found: {input_image}"

    with open(input_image, "rb") as f:
        input_bytes = f.read()

    output_bytes = remove(input_bytes)
    output_path = OUTPUT_DIR / f"{filename_prefix}.png"
    with open(output_path, "wb") as f:
        f.write(output_bytes)

    return f"🖼️ Background removed\n   Output: {output_path}"


@tool("color_correct")
def color_correct(
    input_image: str,
    brightness: float = 1.0,
    contrast: float = 1.0,
    saturation: float = 1.0,
    filename_prefix: str = "color_correct",
) -> str:
    """
    Adjust brightness, contrast, and saturation of an image.

    Best for: final polish before delivery. Subtle adjustments
    recommended (0.8-1.2 range for natural results).

    Args:
        input_image: Path to the source image.
        brightness: 0.0-2.0 (1.0 = unchanged).
        contrast: 0.0-2.0 (1.0 = unchanged).
        saturation: 0.0-2.0 (1.0 = unchanged).
        filename_prefix: Prefix for output.

    Returns:
        File path of the adjusted image.
    """
    try:
        from PIL import Image, ImageEnhance
    except ImportError:
        return "❌ color_correct: Pillow not installed. Run: pip install Pillow"

    if not os.path.exists(input_image):
        return f"❌ color_correct: Input image not found: {input_image}"

    img = Image.open(input_image).convert("RGB")

    if brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(brightness)
    if contrast != 1.0:
        img = ImageEnhance.Contrast(img).enhance(contrast)
    if saturation != 1.0:
        img = ImageEnhance.Color(img).enhance(saturation)

    output_path = OUTPUT_DIR / f"{filename_prefix}.png"
    img.save(output_path, "PNG")

    changes = []
    if brightness != 1.0: changes.append(f"brightness {brightness:.1f}x")
    if contrast != 1.0: changes.append(f"contrast {contrast:.1f}x")
    if saturation != 1.0: changes.append(f"saturation {saturation:.1f}x")

    return f"🎨 Color Corrected ({', '.join(changes)})\n   Output: {output_path}"

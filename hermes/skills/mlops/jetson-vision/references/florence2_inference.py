#!/usr/bin/env python3
"""Florence 2 inference on Jetson Orin Nano — working recipe.
Usage: python3 florence2_inference.py <image_path> [--task CAPTION|DETAILED_CAPTION|MORE_DETAILED_CAPTION|OD|OCR]
Output: JSON with task result to stdout.
"""
import sys, json, time
import torch

# ── MUST monkey-patch BEFORE importing transformers ──
# NVIDIA JetPack torch omits torch.distributed; these imports crash otherwise.
import transformers.integrations.deepspeed as _ds
_ds.is_deepspeed_zero3_enabled = lambda: False

import transformers.integrations.fsdp as _fsdp
_fsdp.is_fsdp_managed_module = lambda m: False
# ──────────────────────────────────────────────────────

from transformers import AutoProcessor, AutoModelForCausalLM
from PIL import Image

# Model loads once per process invocation (~4s cold, near-instant warm with caching)
MODEL = None
PROCESSOR = None

def load_model():
    global MODEL, PROCESSOR
    if MODEL is None:
        MODEL = AutoModelForCausalLM.from_pretrained(
            "microsoft/Florence-2-base",
            torch_dtype=torch.float16,
            trust_remote_code=True,
        ).to("cuda")
        PROCESSOR = AutoProcessor.from_pretrained(
            "microsoft/Florence-2-base",
            trust_remote_code=True,
        )
    return MODEL, PROCESSOR

def analyze(image_path: str, task: str = "<DETAILED_CAPTION>"):
    """Run Florence 2 on an image file. Returns dict with result."""
    model, processor = load_model()
    img = Image.open(image_path).convert("RGB")
    inputs = processor(text=task, images=img, return_tensors="pt").to("cuda", torch.float16)

    t0 = time.time()
    generated_ids = model.generate(
        input_ids=inputs["input_ids"],
        pixel_values=inputs["pixel_values"],
        max_new_tokens=1024,
        num_beams=3,
    )
    generated_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
    result = processor.post_process_generation(
        generated_text, task=task, image_size=(img.width, img.height)
    )
    dt = time.time() - t0

    return {
        "task": task,
        "result": result.get(task, str(result)),
        "image_size": list(img.size),
        "inference_time_s": round(dt, 1),
        "vram_used_gb": round((torch.cuda.mem_get_info()[1] - torch.cuda.mem_get_info()[0]) / 1e9, 1),
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: florence2_inference.py <image_path> [--task TASK]"}))
        sys.exit(1)

    image_path = sys.argv[1]
    task = "<DETAILED_CAPTION>"

    # Parse --task flag
    for i, arg in enumerate(sys.argv):
        if arg == "--task" and i + 1 < len(sys.argv):
            task = sys.argv[i + 1]

    result = analyze(image_path, task)
    print(json.dumps(result, indent=2))

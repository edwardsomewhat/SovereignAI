"""
Florence 2 inference on Jetson Orin — working test script.
Runs CAPTION, DETAILED_CAPTION, and MORE_DETAILED_CAPTION on a test image.
Requires the full Jetson setup from SKILL.md Steps 1-5.
"""

import sys
import time
import torch

# Monkey-patches required for Jetson torch (no distributed support)
import transformers.integrations.deepspeed as _ds

_ds.is_deepspeed_zero3_enabled = lambda: False

import transformers.integrations.fsdp as _fsdp

_fsdp.is_fsdp_managed_module = lambda m: False

# Now safe
from transformers import AutoProcessor, AutoModelForCausalLM
from PIL import Image


def main():
    print(f"CUDA: {torch.cuda.is_available()}  |  VRAM free: {torch.cuda.mem_get_info()[0] / 1e9:.1f}GB")

    print("Loading Florence-2-base...")
    t0 = time.time()
    model = AutoModelForCausalLM.from_pretrained(
        "microsoft/Florence-2-base",
        torch_dtype=torch.float16,
        trust_remote_code=True,
    ).to("cuda")
    processor = AutoProcessor.from_pretrained(
        "microsoft/Florence-2-base",
        trust_remote_code=True,
    )
    dt = time.time() - t0
    free, total = torch.cuda.mem_get_info()
    print(f"Loaded in {dt:.1f}s  |  VRAM used: {(total - free) / 1e9:.1f}GB  |  free: {free / 1e9:.1f}GB")

    # Test image: solid color (replace with real image for production)
    img = Image.new("RGB", (640, 480), color="cornflowerblue")

    tasks = ["<CAPTION>", "<DETAILED_CAPTION>", "<MORE_DETAILED_CAPTION>"]
    for task in tasks:
        inputs = processor(text=task, images=img, return_tensors="pt").to("cuda", torch.float16)
        t0 = time.time()
        ids = model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=256,
            num_beams=3,
        )
        text = processor.batch_decode(ids, skip_special_tokens=False)[0]
        result = processor.post_process_generation(text, task=task, image_size=(img.width, img.height))
        print(f"{task} ({time.time() - t0:.1f}s): {result}")

    print("✅ Florence 2 working on Jetson Orin CUDA!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

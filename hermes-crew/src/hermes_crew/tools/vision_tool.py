"""VisionTool — CrewAI tool for the vision agent.

Bridges CrewAI to the nano-box vision server (Jetson Orin Nano Super).
Routes images to the two-tier pipeline:
  - Tier 1: Coral TPU — fast classification (<15ms)
  - Tier 2: Florence 2 on GPU — deep captioning / OCR / detection

Communication: Tailscale SSH (keyless) to nano-box (100.81.229.44).
"""

import base64
import json
import os
import subprocess
import tempfile
from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


NANO_BOX_HOST = os.getenv("NANO_BOX_HOST", "nano-box")
VISION_WORKER = "/home/fated/vision-server/worker.py"
SUPPORTED_TASKS = [
    "<CAPTION>",
    "<DETAILED_CAPTION>",
    "<MORE_DETAILED_CAPTION>",
    "<OD>",
    "<OCR>",
    "<REGION_TO_DESCRIPTION>",
    "<REFERRING_EXPRESSION_SEGMENTATION>",
]


class VisionInput(BaseModel):
    """Input schema for vision analysis."""

    image_source: str = Field(
        description=(
            "Path to a local image file, or a URL to an image. "
            "Local paths can be absolute or relative."
        )
    )
    mode: str = Field(
        default="both",
        description="fast=Coral only (<15ms), deep=Florence only, both=tiered pipeline (default)",
    )
    task: str = Field(
        default="<DETAILED_CAPTION>",
        description=(
            "Florence task for deep mode. Options: <CAPTION> (short), "
            "<DETAILED_CAPTION> (paragraph), <MORE_DETAILED_CAPTION> (verbose), "
            "<OD> (object detection), <OCR> (text extraction)"
        ),
    )


def _run_ssh(command: str, timeout: int = 90) -> tuple[str, str, int]:
    """Run a command on nano-box via Tailscale SSH."""
    full_cmd = ["tailscale", "ssh", NANO_BOX_HOST, command]
    proc = subprocess.run(
        full_cmd, capture_output=True, text=True, timeout=timeout
    )
    return proc.stdout, proc.stderr, proc.returncode


def _pipe_image_to_nano(image_path: str) -> str:
    """Copy an image to nano-box via SSH stdin, return remote path."""
    remote_name = f"/tmp/hermes_vision_{os.path.basename(image_path)}"
    with open(image_path, "rb") as f:
        b64_data = base64.b64encode(f.read()).decode()

    cmd = f"base64 -d > {remote_name}"
    proc = subprocess.run(
        ["tailscale", "ssh", NANO_BOX_HOST, cmd],
        input=b64_data,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Failed to copy image: {proc.stderr}")
    return remote_name


def _download_url(url: str) -> str:
    """Download an image URL to a local temp file."""
    import urllib.request

    suffix = os.path.splitext(url.split("?")[0])[1] or ".jpg"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        urllib.request.urlretrieve(url, tmp.name)
        return tmp.name
    except Exception:
        tmp.close()
        os.unlink(tmp.name)
        raise


class VisionTool(BaseTool):
    """Analyze images using the nano-box vision pipeline (Coral TPU + Florence 2).

    Sends an image to the Jetson Orin Nano (nano-box) for two-tier analysis:
    - Coral TPU: sub-15ms fast classification (what kind of scene/object?)
    - Florence 2: GPU-powered deep captioning, object detection, or OCR

    Returns structured JSON with predictions, captions, and latency metrics.
    """

    name: str = "vision_analyze"
    description: str = (
        "Analyze an image using the nano-box vision pipeline. "
        "Supports fast Coral TPU classification (<15ms) and deep Florence 2 "
        "captioning/OCR/object detection. Use mode='fast' for quick scene checks, "
        "mode='deep' for detailed descriptions, or mode='both' (default) for "
        "the full tiered pipeline."
    )
    args_schema: type[BaseModel] = VisionInput

    def _run(
        self,
        image_source: str,
        mode: str = "both",
        task: str = "<DETAILED_CAPTION>",
    ) -> str:
        """Execute vision analysis on nano-box."""
        # Resolve image path
        if image_source.startswith(("http://", "https://")):
            local_path = _download_url(image_source)
            own_temp = True
        elif os.path.exists(image_source):
            local_path = image_source
            own_temp = False
        else:
            return json.dumps({"error": f"Image not found: {image_source}"})

        try:
            # Copy image to nano-box
            remote_path = _pipe_image_to_nano(local_path)

            # Validate task
            if task not in SUPPORTED_TASKS:
                task = "<DETAILED_CAPTION>"

            # Run vision worker
            worker_cmd = (
                f"python3 {VISION_WORKER} "
                f"--image {remote_path} "
                f"--mode {mode} "
                f"--task '{task}'"
            )
            stdout, stderr, exit_code = _run_ssh(worker_cmd, timeout=90)

            if exit_code != 0:
                return json.dumps({
                    "error": f"Vision worker failed (exit {exit_code})",
                    "stderr": stderr[:500],
                })

            # Clean up temp image on nano-box
            _run_ssh(f"rm -f {remote_path}", timeout=5)

            # Parse and return
            return stdout.strip()

        except subprocess.TimeoutExpired:
            return json.dumps({"error": "Vision analysis timed out (90s)"})
        except Exception as e:
            return json.dumps({"error": str(e)})
        finally:
            if own_temp and os.path.exists(local_path):
                os.unlink(local_path)

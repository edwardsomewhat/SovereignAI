---
name: vision-agent
description: "SovereignAI Vision Agent — CrewAI agent wired to nano-box two-tier vision pipeline (Coral TPU + Florence 2 on GPU)"
version: 1.0.0
tags: [crewai, vision, coral-tpu, florence-2, jetson, nano-box]
platforms: [linux]
---

# Vision Agent — SovereignAI CrewAI

The Vision Agent is a CrewAI agent that analyzes images using the nano-box
(Jetson Orin Nano Super) two-tier vision pipeline.

## Architecture

```
CREWAI SUPERVISOR
  → assigns vision_analysis task
    → VISION AGENT (hermes_crew, sovereign)
      → vision_analyze tool
        → pipe image via Tailscale SSH to nano-box
          → NANO-BOX (100.81.229.44)
            → Coral TPU (Docker, <15ms classification)
            → Florence 2 (GPU, 1-7s deep captioning)
          ← structured JSON
      ← CrewAI interprets results
    ← delivers to supervisor
```

## Files

| File | Location | Purpose |
|------|----------|---------|
| VisionTool | `hermes-crew/src/hermes_crew/tools/vision_tool.py` | CrewAI BaseTool bridge |
| Worker | `/home/fated/vision-server/worker.py` (nano-box) | Tiered inference orchestrator |
| Coral infer | `/home/fated/vision-server/coral_infer.py` (nano-box) | Docker container Coral script |
| Coral model | `/home/fated/models/mobilenet_v1_1.0_224_quant_edgetpu.tflite` (nano-box) | MobileNet V1, 4.7MB |
| Labels | `/home/fated/models/imagenet_labels.txt` (nano-box) | ImageNet 1000 |

## Tool interface

### vision_analyze

```
Args:
  image_source (str): Local path or URL to image
  mode (str): "fast" (Coral only, <15ms), "deep" (Florence only), "both" (default)
  task (str): Florence task — <CAPTION>, <DETAILED_CAPTION>, <MORE_DETAILED_CAPTION>, <OD>, <OCR>

Returns: JSON with tiers array, latency_ms per tier, total_latency_ms
```

### Example output

```json
{
  "image": "/tmp/hermes_vision_sample.jpg",
  "mode": "both",
  "tiers": [
    {
      "tier": "coral",
      "model": "mobilenet_v1_224_quant_edgetpu",
      "latency_ms": 14.82,
      "top_prediction": "ping-pong ball",
      "top5": [...]
    },
    {
      "tier": "florence2",
      "task": "<DETAILED_CAPTION>",
      "latency_ms": 6700.92,
      "result": "The image shows a blue circle on a green background..."
    }
  ],
  "total_latency_ms": 6715.74
}
```

## Performance

| Tier | Model | Latency | VRAM |
|------|-------|---------|------|
| Coral TPU | MobileNet V1 (quant) | 3-15ms | 0 (dedicated RAM) |
| Florence 2 | Florence-2-base (fp16) | 1.3-7.7s | 2.4 GB GPU |

## Adding new Coral models

Download pre-compiled Edge TPU models:

```bash
curl -sLO https://raw.githubusercontent.com/google-coral/test_data/master/<model>.tflite
# Place in /home/fated/models/ on nano-box
```

Verified working: `mobilenet_v1_1.0_224_quant_edgetpu.tflite`, `mobilenet_v2_1.0_224_quant_edgetpu.tflite`

For detection models (EfficientDet), update `coral_infer.py` with the appropriate output tensor parsing.

## Pitfalls

1. **Docker mount**: Coral infer script runs INSIDE the container — mount `/home/fated/vision-server:/app:ro` so the container can access `coral_infer.py`
2. **Image transport**: VisionTool copies images to nano-box via base64 pipe over SSH. Max ~10MB images. For larger, use direct file transfer.
3. **Florence model stays loaded**: The worker keeps the model in GPU memory between calls (singleton). If VRAM is needed elsewhere, kill the process.
4. **NvMapMem errors**: Harmless Jetson CUDA logging during memory allocation. Ignore.
5. **Tailscale SSH hostname**: Set via `NANO_BOX_HOST` env var. Defaults to "nano-box".

## CrewAI wiring

In `crew.py`:
```python
@agent
def vision(self) -> Agent:
    return Agent(
        config=self.agents_config["vision"],
        llm=_get_llm(),
        verbose=True,
        allow_delegation=False,
        tools=[VisionTool()],
    )
```

In `tools/__init__.py`:
```python
from .vision_tool import VisionTool
```

The supervisor assigns `vision_analysis` tasks to the vision agent, which calls
`vision_analyze` to process images through the nano-box pipeline.

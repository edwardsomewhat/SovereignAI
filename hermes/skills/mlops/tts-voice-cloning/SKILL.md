---
name: tts-voice-cloning
description: Set up and use Qwen3-TTS for voice cloning, voice design, and custom-voice synthesis — model selection, environment setup, API patterns, and the VoiceDesign→Clone pipeline for reusable character voices.
tags: [tts, voice-clone, qwen3-tts, speech-synthesis]
---

# TTS Voice Cloning

Set up and use Qwen3-TTS models for voice cloning, custom-voice synthesis, and voice design — from model selection through environment setup to the full VoiceDesign→Clone pipeline.

## Trigger

User asks to:
- Clone a voice from a reference audio clip
- Set up TTS for voice cloning
- Use Qwen3-TTS / qwen-tts
- Design a custom voice and use it across multiple lines
- Generate speech with a specific speaker or style

## Model Family Overview

Qwen3-TTS covers 10 languages (Chinese, English, Japanese, Korean, German, French, Russian, Portuguese, Spanish, Italian) with streaming and instruction control. Models are on HuggingFace under `Qwen/Qwen3-TTS-*`.

| Model | VRAM (bf16) | Purpose |
|-------|-------------|---------|
| **1.7B-Base** | ~3.5 GB | **Voice clone** — 3-second ref audio → cloned voice. Also used for fine-tuning. |
| 1.7B-CustomVoice | ~3.5 GB | 9 preset speakers (Vivian, Ryan, etc.) with instruction-based style control. |
| 1.7B-VoiceDesign | ~3.5 GB | Create voices from natural-language descriptions. |
| 0.6B-Base | ~1.3 GB | Smaller voice clone (lower quality, less VRAM). |
| 0.6B-CustomVoice | ~1.3 GB | Smaller preset-speaker model. |
| Tokenizer-12Hz | small | **Required for all models** — encodes/decodes speech tokens. |

**For voice cloning**: use **1.7B-Base** (best quality) or 0.6B-Base (VRAM-constrained). Both support `generate_voice_clone` with a reference audio + transcript, or `x_vector_only_mode=True` (no transcript needed, but lower quality).

**VoiceDesign→Clone pipeline**: Use 1.7B-VoiceDesign to generate a reference clip matching a target persona, then feed it into 1.7B-Base's `create_voice_clone_prompt` for reusable character voices across many lines.

## Environment Setup

```bash
# Requires Python 3.12 (not 3.11, not 3.14)
python3.12 -m venv ~/venvs/qwen3-tts
source ~/venvs/qwen3-tts/bin/activate

# PyTorch with CUDA 12.4 (works with driver >= 550)
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124

# Qwen3-TTS package
pip install -U qwen-tts

# FlashAttention 2 (reduces VRAM usage, recommended)
# If machine has < 96GB RAM + many CPU cores, cap parallel jobs:
MAX_JOBS=4 pip install -U flash-attn --no-build-isolation
```

## Voice Clone Usage

Minimal example — clone a voice from a reference audio and synthesize new speech:

```python
import torch
import soundfile as sf
from qwen_tts import Qwen3TTSModel

model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    device_map="cuda:0",
    dtype=torch.bfloat16,
    attn_implementation="flash_attention_2",
)

wavs, sr = model.generate_voice_clone(
    text="Hello, this is a cloned voice speaking.",
    language="English",
    ref_audio="path/to/reference.wav",
    ref_text="The transcript of the reference audio.",  # omit if x_vector_only_mode=True
)
sf.write("output.wav", wavs[0], sr)
```

### Reusable Clone Prompt

For multiple generations from the same reference (avoids re-computing features):

```python
prompt = model.create_voice_clone_prompt(
    ref_audio="reference.wav",
    ref_text="transcript here",
    x_vector_only_mode=False,  # True = no transcript needed, lower quality
)
wavs, sr = model.generate_voice_clone(
    text=["Line one.", "Line two."],
    language=["English", "English"],
    voice_clone_prompt=prompt,
)
```

## VoiceDesign→Clone Pipeline

Design a voice by description, then clone it for repeated use:

1. Load **VoiceDesign** model, call `generate_voice_design(text, language, instruct)` to produce a reference clip.
2. Load **Base** model, call `create_voice_clone_prompt(ref_audio=that_clip, ref_text=that_text)`.
3. Call `generate_voice_clone` with `voice_clone_prompt` for every subsequent line.

This is ideal for consistent character voices across many lines (game dialog, narration, etc.).

## Capturing Reference Audio

Reference clips for voice cloning should be:
- 2–5 seconds of clean speech (no background noise, no music)
- 16-bit mono WAV, 16–48 kHz sample rate
- Speaker alone, natural delivery

Capture from ALSA mic (see `references/alsa-headless.md`):
```bash
ffmpeg -f alsa -ac 1 -ar 48000 -i hw:0,0 -t 5 reference.wav
```

## VRAM Considerations

- 1.7B-Base in bf16: ~3.5 GB + tokenizer overhead (~0.5 GB) = ~4 GB minimum
- FlashAttention 2 reduces peak memory
- On 24 GB GPU with other services (ComfyUI, vLLM), free up VRAM first if needed:
  ```bash
  sudo systemctl stop comfyui  # or whatever is consuming VRAM
  ```
- Check usage: `nvidia-smi --query-compute-apps=pid,used_memory,name --format=csv`

## Pitfalls

- **Python version**: Must use 3.12. 3.11 and 3.14 are not supported by qwen-tts.
- **Tokenizer required**: All models need Qwen3-TTS-Tokenizer-12Hz. The `qwen-tts` package auto-downloads it on first use.
- **VRAM fragmentation**: Even if `nvidia-smi` shows enough free memory, PyTorch may fail with OOM if memory is fragmented. Restarting other GPU processes helps.
- **ALSA channel mismatch**: When playing back generated audio via ALSA, ensure stereo output (`-ac 2`). Mono can fail with I/O error on some codecs (e.g., Realtek ALC1220).
- **Model download**: First use triggers HuggingFace download. If network is slow, pre-download with `huggingface-cli download Qwen/Qwen3-TTS-12Hz-1.7B-Base --local-dir ./1.7B-Base` and pass the local path to `from_pretrained()`.

## References

- `references/alsa-headless.md` — ALSA audio setup on headless Ubuntu: unmute, test, playback
- `references/obsbot-tiny-linux.md` — Using Obsbot Tiny webcam/mic as capture source on Linux

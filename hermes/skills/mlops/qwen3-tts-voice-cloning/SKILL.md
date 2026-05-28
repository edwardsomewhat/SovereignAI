---
name: qwen3-tts-voice-cloning
description: Install and use Qwen3-TTS for voice cloning, voice design, and custom voice generation on Linux with NVIDIA GPU. Covers model selection, qwen-tts package, VRAM sizing, and audio I/O integration.
---

# Qwen3-TTS Voice Cloning

Use when: setting up Qwen3-TTS for voice cloning, voice design, or custom voice TTS on a Linux machine with NVIDIA GPU. Covers the `qwen-tts` Python package — NOT vLLM or Docker-based serving.

## Model Selection

| Model | Size (bf16) | VRAM | Purpose |
|-------|-------------|------|---------|
| Qwen3-TTS-12Hz-1.7B-Base | ~3.4 GB | ~5-6 GB | **Voice clone** from 3s reference audio |
| Qwen3-TTS-12Hz-1.7B-CustomVoice | ~3.4 GB | ~5-6 GB | 9 preset speakers with style instructions |
| Qwen3-TTS-12Hz-1.7B-VoiceDesign | ~3.4 GB | ~5-6 GB | Create voices from text descriptions |
| Qwen3-TTS-12Hz-0.6B-Base | ~1.2 GB | ~2.5 GB | Lighter voice clone |
| Qwen3-TTS-12Hz-0.6B-CustomVoice | ~1.2 GB | ~2.5 GB | Lighter preset speakers |
| Qwen3-TTS-Tokenizer-12Hz | small | auto | **Required** — auto-downloaded with any model |

**For voice cloning, use 1.7B-Base** (better quality). The 0.6B-Base is good for quick tests or if VRAM is tight.

**Bonus**: the VoiceDesign model can create a voice from a description, then feed it into the Base model for reusable cloning via `create_voice_clone_prompt`.

## Installation

Requires Python 3.12 (the `qwen-tts` package targets 3.12 specifically).

```bash
# Create venv with Python 3.12
python3.12 -m venv ~/venvs/qwen3-tts
source ~/venvs/qwen3-tts/bin/activate

# Install PyTorch with CUDA (match driver version)
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124

# Install qwen-tts and audio deps
pip install qwen-tts soundfile

# System audio tools (for playback/capture)
sudo apt-get install -y sox libsox-fmt-all alsa-utils

# Optional: flash-attn for faster inference (reduces VRAM)
pip install -U flash-attn --no-build-isolation
# On machines with <96GB RAM: MAX_JOBS=4 pip install -U flash-attn --no-build-isolation
```

**Pitfall**: `qwen-tts` pip package was built for Python 3.12. Using 3.13+ or 3.11 may cause dependency conflicts. Always use a 3.12 venv.

**Pitfall**: flash-attn compilation can OOM on machines with <96GB RAM. Use `MAX_JOBS=4` to limit parallelism.

## Voice Clone (1.7B-Base or 0.6B-Base)

Reference audio can be a file path, URL, base64 string, or `(numpy_array, sample_rate)` tuple.

```python
import torch
import soundfile as sf
from qwen_tts import Qwen3TTSModel

model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    device_map="cuda:0",
    dtype=torch.bfloat16,
)

# Simple clone: provide ref audio + its transcript
wavs, sr = model.generate_voice_clone(
    text="Hello! This is a cloned voice speaking.",
    language="English",
    ref_audio="path/to/reference.wav",
    ref_text="The exact words spoken in the reference audio.",
)
sf.write("output.wav", wavs[0], sr)

# x_vector_only mode: skip transcript (lower quality but simpler)
wavs, sr = model.generate_voice_clone(
    text="Cloning without transcript.",
    language="English",
    ref_audio="path/to/reference.wav",
    x_vector_only_mode=True,
)
```

**Reusable clone prompts** — build once, reuse many times:

```python
prompt = model.create_voice_clone_prompt(
    ref_audio="reference.wav",
    ref_text="Reference transcript.",
)

# Batch generate
wavs, sr = model.generate_voice_clone(
    text=["Line one.", "Line two."],
    language=["English", "English"],
    voice_clone_prompt=prompt,
)
```

## Voice Design (1.7B-VoiceDesign)

Create a voice from a natural-language description, then optionally clone it:

```python
design_model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
    device_map="cuda:0",
    dtype=torch.bfloat16,
)

wavs, sr = design_model.generate_voice_design(
    text="Hey there! I'm a custom designed voice.",
    language="English",
    instruct="Deep, resonant male voice, BBC documentary narrator style, calm and authoritative.",
)
```

**Voice Design → Clone pipeline**: design the voice, then feed its output into the Base model's `create_voice_clone_prompt` for reusable cloning across many lines.

## Custom Voice (1.7B-CustomVoice)

9 preset speakers with optional style instructions:

```python
model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    device_map="cuda:0",
    dtype=torch.bfloat16,
)

# See available speakers
print(model.get_supported_speakers())
# Vivian(Chinese), Serena(Chinese), Uncle_Fu(Chinese), Dylan(Beijing),
# Eric(Sichuan), Ryan(English), Aiden(English), Ono_Anna(Japanese), Sohee(Korean)

wavs, sr = model.generate_custom_voice(
    text="The quick brown fox jumps over the lazy dog.",
    language="English",
    speaker="Ryan",
    instruct="Very excited and energetic.",
)
```

## VRAM Management

- 0.6B models: ~2.5 GB VRAM
- 1.7B models: ~5-6 GB VRAM
- Both can coexist with other GPU workloads (tested alongside ComfyUI using 16.7 GB on RTX 3090)
- The tokenizer model is lightweight and auto-downloaded
- First run downloads models from HuggingFace (~1.2-3.4 GB). Subsequent runs use cache.

### Loading multiple models sequentially (critical pitfall)

When running VoiceDesign → Clone pipeline or switching between models, you **must** explicitly free the first model before loading the second. Python's GC and PyTorch's caching won't do it fast enough, causing `torch.OutOfMemoryError` even when nvidia-smi shows free VRAM:

```python
import gc

# After using model A, before loading model B:
del model_a
gc.collect()
torch.cuda.empty_cache()

# Now safe to load model B
model_b = Qwen3TTSModel.from_pretrained(...)
```

Without this, loading two 1.7B models back-to-back on a 24 GB card with other services will OOM every time. The `empty_cache()` call releases PyTorch's reserved-but-unallocated memory pool.

## Audio I/O Integration

See `references/alsa-audio-setup.md` for full ALSA configuration, device discovery, and common pitfalls (muted Master, Auto-Mute, front vs rear jacks).

Output is 24000 Hz WAV. For playback on ALSA (headless Linux), resample to 48kHz stereo:

```bash
# Play through ALSA (adjust device as needed — see references/alsa-audio-setup.md)
ffmpeg -i /tmp/tts_output.wav -ar 48000 -ac 2 -f alsa hw:3,0
```

For recording reference audio from a USB mic:

```bash
# Record 10s from Obsbot Tiny mic (or any hw:X,0 capture device)
ffmpeg -f alsa -ac 1 -ar 48000 -i hw:0,0 -t 10 /tmp/reference.wav
```

**Push-to-talk**: `scripts/ptt_record.py` runs as a background listener — hold Ctrl+B to record from the USB mic, release to stop. Output goes to `/tmp/ptt_recording.wav`.

## Supported Languages

Chinese, English, Japanese, Korean, German, French, Russian, Portuguese, Spanish, Italian. Pass `language="Auto"` for auto-detection, or specify explicitly for best results.

## Web UI Demo

```bash
pip install qwen-tts
qwen-tts-demo --help
```

## References

- `references/alsa-audio-setup.md` — ALSA device discovery, Master volume, Auto-Mute, front/rear jack mapping
- `references/obsbot-tiny.md` — Obsbot Tiny webcam: video formats, microphone, UVC PTZ gimbal control, sleep/wake
- `scripts/ptt_record.py` — Push-to-talk recorder daemon (hold Ctrl+B to record, release to stop)
- `scripts/quick-clone.py` — End-to-end: record from mic → clone → playback

---
name: qwen3-tts-voice-clone
description: Qwen3-TTS voice cloning, voice design, and push-to-talk recording on conchai with Obsbot Tiny mic.
category: mlops
---

# Qwen3-TTS Voice Clone on ConchAI

## Setup (one-time)

```bash
# Venv at ~/venvs/qwen3-tts (Python 3.12, PyTorch 2.6.0+cu124, qwen-tts 0.1.1)
source ~/venvs/qwen3-tts/bin/activate
```

Models cached in HF hub (~7GB total):
- `Qwen/Qwen3-TTS-12Hz-0.6B-Base` — lightweight voice clone
- `Qwen/Qwen3-TTS-12Hz-1.7B-Base` — high quality voice clone
- `Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign` — design voices from text description
- Tokenizer auto-downloads with models

## Audio Devices

| Device | ALSA | Details |
|--------|------|---------|
| Obsbot Tiny mic | `hw:0,0` | 48kHz mono 16-bit |
| Rear line out | `hw:3,0` | Stereo, needs 48kHz resample |
| Front headphone | `hw:3,1` | Stereo |

**CRITICAL**: Master and Line Out must be unmuted. Check with:
```bash
amixer -c 3 sset Master 100% unmute
amixer -c 3 sset 'Line Out' 100% unmute
amixer -c 3 sset 'Auto-Mute Mode' Disabled
```

### Audio Troubleshooting

If no sound from speakers, check in this order:

1. **Master volume** — the overall card volume. Often at 0% after cold boot:
   ```bash
   amixer -c 3 sget Master        # if [off] or 0%, fix it
   amixer -c 3 sset Master 100% unmute
   ```

2. **Auto-Mute Mode** — when Enabled, rear Line Out mutes if front headphone jack was ever used:
   ```bash
   amixer -c 3 sset 'Auto-Mute Mode' Disabled
   ```

3. **Wrong port** — front headphone = `hw:3,1`, rear line out = `hw:3,0`. Try both.

4. **Channel count** — ALSA devices often reject mono. Always use `-ac 2` with ffmpeg:
   ```bash
   ffmpeg -i audio.wav -ar 48000 -ac 2 -f alsa hw:3,0
   ```

5. **Sample rate** — Qwen3-TTS outputs 24kHz. Resample to 48kHz for ALSA:
   ```bash
   ffmpeg -i output.wav -ar 48000 -ac 2 -f alsa hw:3,0
   ```

## Voice Message Input (Telegram → TTS-ready WAV)

Hermes saves incoming Telegram voice messages as Opus OGG in `~/.hermes/audio_cache/`. The newest file is the most recent voice message. Convert to 24kHz mono WAV for Qwen3-TTS:

```bash
# Find the latest voice message
ls -t ~/.hermes/audio_cache/audio_*.ogg | head -1

# Convert Opus OGG → 24kHz mono WAV (Qwen3-TTS native format)
ffmpeg -y -i ~/.hermes/audio_cache/audio_<id>.ogg \
  -ar 24000 -ac 1 /tmp/voice_ref.wav
```

**Pitfall**: Qwen3-TTS expects the sample rate it was trained on (24kHz for 12Hz models). Feeding 48kHz audio causes mismatched output.

## Voice Clone (from reference audio)

```python
from qwen_tts import Qwen3TTSModel
import soundfile as sf

model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    device_map="cuda:0", dtype=torch.bfloat16,
)

# Method 1: x_vector_only (no transcript needed, slightly lower quality)
wavs, sr = model.generate_voice_clone(
    text="Text to speak in cloned voice",
    language="English",
    ref_audio="/path/to/reference.wav",
    x_vector_only_mode=True,
)

# Method 2: with transcript (better quality)
wavs, sr = model.generate_voice_clone(
    text="Text to speak in cloned voice",
    language="English",
    ref_audio="/path/to/reference.wav",
    ref_text="exact transcript of reference audio",
)
sf.write("output.wav", wavs[0], sr)
```

## Voice Design + Clone Pipeline

```python
# Step 1: Design voice from description
vd_model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
    device_map="cuda:0", dtype=torch.bfloat16,
)
wavs, sr = vd_model.generate_voice_design(
    text="Reference sentence for the designed voice",
    language="English",
    instruct="Voice description in natural language",
)
sf.write("designed_ref.wav", wavs[0], sr)
del vd_model; gc.collect(); torch.cuda.empty_cache()

# Step 2: Clone from designed voice
clone_model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    device_map="cuda:0", dtype=torch.bfloat16,
)
prompt = clone_model.create_voice_clone_prompt(
    ref_audio="designed_ref.wav", ref_text="Reference sentence...",
)
wavs2, sr2 = clone_model.generate_voice_clone(
    text=["Line 1", "Line 2"],
    language=["English", "English"],
    voice_clone_prompt=prompt,
)
```

## Playback

```bash
ffmpeg -i output.wav -ar 48000 -ac 2 -f alsa hw:3,0
```

## Push-to-Talk Recording & Dictation

Script at `scripts/ptt_record.py` (included with this skill). Copy to `~/scripts/` and run:
```bash
sudo ~/venvs/qwen3-tts/bin/python ~/scripts/ptt_record.py
```

| Hotkey | Function | Output |
|--------|----------|--------|
| **Ctrl+B** | Record audio from Obsbot mic | `/tmp/ptt_recording.wav` |
| **Ctrl+V** | Record + transcribe (dictation) | `/tmp/ptt_dictation.txt` |

Dictation uses faster-whisper "small" model on GPU (~1GB VRAM). First use downloads the model (~500MB). Release the key to stop recording and save/transcribe.

Requires `evdev`, `faster-whisper` in the venv. Needs sudo for `/dev/input/` access unless user is in `input` group:
```bash
sudo usermod -aG input $USER  # requires re-login
```

## Obsbot Tiny PTZ Control

```bash
# Wake camera (must do before moves)
v4l2-ctl -d /dev/video0 -c pan_absolute=0

# Pan/tilt/zoom
v4l2-ctl -d /dev/video0 -c pan_absolute=36000    # 10° right
v4l2-ctl -d /dev/video0 -c tilt_absolute=-36000  # 10° down
v4l2-ctl -d /dev/video0 -c zoom_absolute=50      # 50% zoom
```
Pan range: ±468000 (±130°), Tilt range: ±324000 (±90°), Zoom: 0-100

## VRAM Management

ComfyUI uses ~16.7GB. Only load ONE TTS model at a time. Always `del model; gc.collect(); torch.cuda.empty_cache()` before loading another.

### Freeing VRAM from ComfyUI (without stopping it)

ComfyUI's `/api/free` endpoint unloads all loaded models while keeping the server running:

```bash
curl -s -X POST http://localhost:8188/api/free \
  -H "Content-Type: application/json" \
  -d '{"unload_models": true, "free_memory": true}'
```

This frees ~16.7GB instantly — much better than killing ComfyUI. After generating TTS, models reload on next ComfyUI queue execution.

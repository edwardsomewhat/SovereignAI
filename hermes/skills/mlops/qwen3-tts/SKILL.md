---
name: qwen3-tts
description: Install and use Qwen3-TTS for voice cloning, voice design, and text-to-speech. Covers model selection, venv setup, API patterns, ALSA playback, and webcam-mic capture.
---

# Qwen3-TTS Voice Cloning

Qwen3-TTS is Alibaba's open-source TTS series supporting voice cloning, voice design, and custom-voice synthesis across 10 languages with streaming support.

## Model Selection

| Model | Size (bf16) | Purpose | When to Use |
|-------|-------------|---------|-------------|
| 1.7B-Base | ~3.4 GB | Voice clone | Best quality cloning. Needs ref_audio + ref_text (or x_vector_only). |
| 0.6B-Base | ~1.2 GB | Voice clone | Lighter/faster clone. Good for testing, lower VRAM. |
| 1.7B-CustomVoice | ~3.4 GB | 9 preset speakers | When you want Vivian/Ryan/etc. with style instructions. |
| 1.7B-VoiceDesign | ~3.4 GB | Voice from description | Design voices by natural-language description. |
| Tokenizer-12Hz | small | Encoder/decoder | Auto-downloaded as dependency. Encodes speech to discrete codes. |

**For voice cloning:** Use 1.7B-Base for quality, 0.6B-Base for speed/low VRAM. Both support 3-second reference audio.

## Setup

```bash
# Requires Python 3.12 (3.11 may work, 3.14 may not)
python3.12 -m venv ~/venvs/qwen3-tts
source ~/venvs/qwen3-tts/bin/activate
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install qwen-tts soundfile

# Optional: faster inference
pip install flash-attn --no-build-isolation
# If RAM < 96GB: MAX_JOBS=4 pip install flash-attn --no-build-isolation
```

Verify: `python -c "from qwen_tts import Qwen3TTSModel; print('OK')"`

## Voice Clone API

Three modes, from best to simplest:

### 1. Full clone (ref_audio + ref_text) — best quality
```python
model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    device_map="cuda:0", dtype=torch.bfloat16,
)
wavs, sr = model.generate_voice_clone(
    text="Target text to speak in cloned voice.",
    language="English",
    ref_audio="/path/to/reference.wav",   # local path, URL, base64, or (array, sr)
    ref_text="Exact transcript of reference audio.",
)
```

### 2. x_vector_only (no transcript) — good quality, more convenient
```python
wavs, sr = model.generate_voice_clone(
    text="Target text.",
    language="English",
    ref_audio="/path/to/reference.wav",
    x_vector_only_mode=True,  # No transcript needed
)
```

### 3. Reusable prompt (clone once, generate many)
```python
prompt = model.create_voice_clone_prompt(
    ref_audio=ref, ref_text=text, x_vector_only_mode=False
)
wavs, sr = model.generate_voice_clone(
    text=["Line 1", "Line 2"],
    language=["English", "English"],
    voice_clone_prompt=prompt,  # Reuse across calls
)
```

### Voice Design → Clone pipeline
Create a voice by description, then clone it for consistent character output:
```python
design_model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign", ...
)
ref_wavs, sr = design_model.generate_voice_design(
    text="Reference sentence.",
    language="English",
    instruct="Deep male voice, resonant, slow and deliberate.",
)
clone_model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base", ...
)
prompt = clone_model.create_voice_clone_prompt(
    ref_audio=(ref_wavs[0], sr), ref_text="Reference sentence."
)
wavs, sr = clone_model.generate_voice_clone(
    text="New sentence.", language="English", voice_clone_prompt=prompt
)
```

## Capturing Reference Audio

### From Obsbot Tiny webcam mic
```bash
ffmpeg -f alsa -ac 1 -ar 48000 -i hw:0,0 -t 10 /tmp/ref.wav
```

### From any ALSA mic
```bash
# List capture devices
arecord -l
# Record (card X, device Y)
ffmpeg -f alsa -ac 1 -ar 48000 -i hw:X,Y -t 10 /tmp/ref.wav
```

## Playing Generated Audio

ALSA on headless Linux: must use stereo (-ac 2), resample to 48kHz:
```bash
# Rear line out (hw:3,0 on this machine)
ffmpeg -i output.wav -ar 48000 -ac 2 -f alsa hw:3,0

# Front headphone (hw:3,1 on this machine)
ffmpeg -i output.wav -ar 48000 -ac 2 -f alsa hw:3,1
```

## Pitfalls

- **Model download is silent on first use.** The model auto-downloads from HF on first `from_pretrained()`. Check VRAM before/after to confirm.
- **VoiceDesign + Clone needs both models.** Each uses ~3-4GB. On 24GB card with ComfyUI (~17GB), you can only load one at a time. Generate the reference clip, save it, free the design model, then load the clone model.
- **Longer reference audio captures more prosody.** 3 seconds is minimum; 10+ seconds captures rhythm, pacing, and emotional range better.
- **ALSA Master volume may be 0%.** On headless Ubuntu, `amixer -c N sget Master` often shows 0% and muted. Set and unmute before playback.
- **ALSA Auto-Mute may block rear output.** When front headphones are plugged (or were plugged), Auto-Mute can silence the rear line out. Disable it: `amixer -c N sset 'Auto-Mute Mode' Disabled`.
- **flash-attn warnings are non-fatal.** The model runs fine with PyTorch's native attention, just slower.
- **Python 3.14 may not work.** The docs recommend 3.12. Tested working on 3.12.13.

## VRAM Budget

| Component | VRAM |
|-----------|------|
| 0.6B-Base | ~2.4 GB |
| 1.7B-Base | ~3.5 GB |
| 1.7B-CustomVoice | ~3.5 GB |
| 1.7B-VoiceDesign | ~3.5 GB |
| Tokenizer only | ~0.5 GB |

With ComfyUI running (~17GB on 3090), the 0.6B model fits comfortably. The 1.7B models are tight — stop ComfyUI if needed.

## References

- `references/obsbot-tiny.md` — Obsbot Tiny webcam: PTZ controls, sleep/wake, mic capture
- `references/alsa-audio.md` — ALSA audio debugging on headless Ubuntu

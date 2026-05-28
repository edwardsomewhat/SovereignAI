---
name: hermes-custom-tts
description: Deploy custom local TTS providers (Qwen, VoxCPM, etc.) as Hermes custom command providers — including remote GPU bridging and voice cloning.
triggers:
  - User wants to set up local/custom TTS on Hermes
  - User mentions Qwen TTS, voice cloning, or custom TTS provider
  - User asks about running TTS on a remote GPU node
  - User wants to change the voice Hermes speaks in
---

# Hermes Custom TTS Provider Deployment

Deploy any local TTS engine (Qwen3-TTS, VoxCPM, XTTS, etc.) as a Hermes custom command provider. Covers the remote-GPU bridge pattern for when the GPU lives on another machine.

## Architecture

```
User speaks/texts → Hermes
  │
  ├─ STT: faster-whisper (local CPU, already built-in)
  │
  ├─ LLM processing
  │
  └─ TTS: custom command provider
       │
       ├─ Hermes writes text → temp file
       ├─ Calls bridge script with {input_path} {output_path}
       │    ├─ SCP text → GPU node
       │    ├─ Run TTS wrapper → WAV/MP3
       │    └─ SCP audio ← GPU node
       └─ Hermes converts → Opus → Telegram voice bubble
```

## Hermes Config Pattern

```yaml
# ~/.hermes/config.yaml
tts:
  provider: my-tts              # name of your custom provider
  providers:
    my-tts:
      type: command
      command: "/path/to/bridge.sh --text-file {input_path} --out {output_path}"
      output_format: wav          # or mp3 if ffmpeg is available
      timeout: 180                # seconds — model loading can be slow
      voice_compatible: true      # enables Telegram voice bubble (Opus conversion)
  speed: 1.0

voice:
  auto_tts: true                 # auto-send voice replies on messaging platforms
```

Placeholders: `{input_path}` and `{output_path}` are filled by Hermes. Use shell-quote-aware quoting.

## Bridge Script (Remote GPU Pattern)

When the GPU is on another machine, the bridge does SCP→run→SCP:

```bash
#!/bin/bash
# Copies text to GPU node, runs TTS, copies audio back
INPUT=""; OUTPUT=""; VOICE_ARGS=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --text-file) INPUT="$2"; shift 2 ;;
        --out) OUTPUT="$2"; shift 2 ;;
        --voice-ref) VOICE_ARGS="--voice-ref $2"; shift 2 ;;
        *) shift ;;
    esac
done

scp -q "$INPUT" gpu-node:/tmp/tts-input.txt && \
ssh gpu-node "~/tts-venv/bin/python ~/tts-wrapper.py $VOICE_ARGS --text-file /tmp/tts-input.txt --out /tmp/tts-output.wav" && \
scp -q gpu-node:/tmp/tts-output.wav "$OUTPUT"
```

Key: SSH key auth must work without password prompts (`ssh gpu-node 'echo ok'` must succeed).

## Qwen3-TTS Specifics

### Model Selection

| Model | Purpose | VRAM | Notes |
|-------|---------|------|-------|
| `Qwen3-TTS-12Hz-1.7B-Base` | Voice cloning | ~6GB | Needs `ref_audio` + `x_vector_only_mode=True` |
| `Qwen3-TTS-12Hz-1.7B-CustomVoice` | Built-in voices | ~6GB | 9 premium timbres (Vivian, etc.) |
| `Qwen3-TTS-12Hz-0.6B-Base` | Lightweight cloning | ~2-3GB | Lower quality, fits alongside coder model |

### PyTorch Compatibility

**Critical**: Check GPU driver compatibility before installing. On the P5000 (driver 535, CUDA 12.2):
- ❌ PyTorch 2.12 (needs CUDA 13.x driver)
- ✅ PyTorch 2.5.1+cu121

```bash
# Create isolated venv (qwen-tts has heavy deps)
python3 -m venv ~/qwen-tts-venv
~/qwen-tts-venv/bin/pip install torch==2.5.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu121
~/qwen-tts-venv/bin/pip install qwen-tts soundfile
```

### Wrapper Script

Voice cloning via x_vector mode (no transcription of reference needed):

```python
from qwen_tts import Qwen3TTSModel
import torch, soundfile as sf

model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    device_map="cuda:0",
    dtype=torch.bfloat16,
)

wavs, sr = model.generate_voice_clone(
    text="Hello world",
    language="English",
    ref_audio="/path/to/voice-sample.wav",
    x_vector_only_mode=True,  # skips ref_text requirement
)
sf.write("output.wav", wavs[0], sr)
```

For built-in voices:
```python
model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    device_map="cuda:0",
    dtype=torch.bfloat16,
)
wavs, sr = model.generate_custom_voice(
    text="Hello", language="English", speaker="Vivian"
)
```

### Voice Sample Requirements

- 3-7 seconds of clean speech
- Mono, 16kHz WAV (convert with `ffmpeg -i input.ogg -ar 16000 -ac 1 output.wav`)
- Telegram voice notes work great — Hermes stores incoming audio in `~/.hermes/audio_cache/`

### Testing

```bash
# Test wrapper directly on GPU node
echo "Test sentence" > /tmp/test.txt
~/qwen-tts-venv/bin/python ~/qwen-tts-wrapper.py --voice-ref ~/voice.wav --text-file /tmp/test.txt --out /tmp/test.wav

# Test full bridge
echo "Test" > /tmp/bridge-test.txt
~/.hermes/qwen-tts-bridge.sh --text-file /tmp/bridge-test.txt --out /tmp/bridge-test.wav
file /tmp/bridge-test.wav  # should show WAV audio

# Test in Hermes: restart gateway, send message, check for voice bubble
```

## Pitfalls

1. **Wrong parameter name**: Qwen API uses `ref_audio` not `reference_audio`
2. **x_vector_only_mode**: Required when you don't have `ref_text` (transcription of reference clip). Without it, API demands `ref_text`
3. **No ffmpeg on GPU node**: Fall back to WAV output; Hermes converts to Opus locally
4. **Model download on first use**: First call slow (~10-20s) as ~6GB model downloads
5. **GPU contention**: TTS model (~4-6GB) competes with Ollama coder model (~13GB). Use `OLLAMA_KEEP_ALIVE=30s` so models unload when idle
6. **Driver mismatch**: Always check `nvidia-smi` CUDA version before picking PyTorch version
7. **Config requires gateway restart**: `hermes restart` after changing `tts.provider`

## Files Reference

- Bridge script: `~/.hermes/qwen-tts-bridge.sh`
- Wrapper script: `~/qwen-tts-wrapper.py` (on GPU node)
- Venv: `~/qwen-tts-venv/` (on GPU node)
- Voice samples: `~/nick-voice.wav` (on GPU node)
- Reference: `references/qwen-tts-details.md` — full API reference and troubleshooting

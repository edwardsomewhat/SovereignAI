# Voice Integration Research — Qwen TTS/ASR for SovereignAI

Research findings for adding voice (TTS + STT) to the SovereignAI crew, fully local.

## Qwen3-TTS (Text → Speech)

- **Repo**: github.com/QwenLM/Qwen3-TTS
- **License**: Apache 2.0
- **Models**: 0.6B (~2-3GB VRAM) and 1.7B (~6GB VRAM with FlashAttention 2)
- **Key feature**: Voice cloning from 3 seconds of audio
- **Voice design**: Natural language control over timbre, emotion, prosody
- **Streaming**: First audio packet after single character; 97ms latency
- **Languages**: 10 (Chinese, English, Japanese, Korean, German, French, Russian, Portuguese, Spanish, Italian)
- **Install**: `pip install qwen-tts`
- **Crane engine**: Pure Rust inference, ~4GB VRAM for 1.7B, faster than real-time
  - See: insiderllm.com/guides/crane-qwen3-tts-local-voice-cloning/

## Qwen3-ASR (Speech → Text)

- **Repo**: github.com/QwenLM/Qwen3-ASR
- **Models**: 0.6B (~2-3GB) and 1.7B
- **Languages**: 30 languages + 22 Chinese dialects
- **Features**: Language identification + speech recognition (all-in-one)
- **Rust impl**: github.com/second-state/qwen3_asr_rs — CLI + API server
- **License**: Open source

## Hardware Fit

hq-ai's P5000 (16GB VRAM):
```
Coding mode:    gpt-oss:20b              ~13GB  | free: ~3GB
Voice mode:     Qwen3-TTS 0.6B           ~2GB   | fits alongside coder
                Qwen3-ASR 0.6B           ~2GB   | ~4GB total

OR with Ollama idle unloading (OLLAMA_KEEP_ALIVE=30s):
Voice mode:     Qwen3-TTS 1.7B           ~6GB   | coder unloaded
                Qwen3-ASR 1.7B           ~6GB   | ~12GB total ✅
```

Voice and coding workloads are never simultaneous — natural turn-taking.
Set `OLLAMA_KEEP_ALIVE=30s` so the coder model unloads during conversation.

## Hermes Voice Integration

Hermes already supports voice mode across CLI, Telegram, and Discord:
- **STT**: faster-whisper (local, free), Groq Whisper, OpenAI Whisper
- **TTS**: 10 providers, 3 local (NeuTTS, KittenTTS, Piper)
- **Custom TTS providers**: configurable via `config.yaml` under `tts.providers.<name>`
- **Telegram**: Voice messages auto-transcribed; voice bubble replies
- **Discord**: Bot joins voice channel for real-time conversation
- **CLI**: Push-to-talk (`Ctrl+B`) with continuous conversation loop

To integrate Qwen as custom provider: deploy model as API server on hq-ai,
point Hermes at it via custom command provider config. Docs:
hermes-agent.nousresearch.com/docs/user-guide/features/tts

## Deployment Recipe (tested 2026-05-25)

### Step 1: Create isolated venv

Qwen TTS needs its own Python environment to avoid dependency conflicts:

```bash
python3 -m venv ~/qwen-tts-venv
~/qwen-tts-venv/bin/pip install -U qwen-tts soundfile
```

### Step 2: Match PyTorch to CUDA driver

PyTorch 2.12 ships with CUDA 13.x toolkit — requires driver ≥560.
If the GPU has driver 535 (CUDA 12.2), downgrade PyTorch:

```bash
~/qwen-tts-venv/bin/pip install torch==2.5.1 torchaudio==2.5.1 \
  --index-url https://download.pytorch.org/whl/cu121
```

Verify: `~/qwen-tts-venv/bin/python -c "import torch; print(torch.cuda.is_available())"`

### Step 3: Wrapper script

Hermes custom TTS providers call a CLI that reads text and writes audio.
Built-in voices (no cloning sample needed) use the CustomVoice model:

```python
# ~/qwen-tts-wrapper.py
from qwen_tts import Qwen3TTSModel
import torch, soundfile as sf, argparse, sys, os

parser = argparse.ArgumentParser()
parser.add_argument('--text-file', required=True)
parser.add_argument('--out', required=True)
parser.add_argument('--voice-vivian', action='store_true')
parser.add_argument('--voice-ref')
parser.add_argument('--language', default='English')
args = parser.parse_args()

with open(args.text_file) as f:
    text = f.read().strip()

if args.voice_ref and os.path.exists(args.voice_ref):
    # Base model — voice cloning. x_vector_only_mode extracts voice
    # fingerprint without needing a transcript (ref_text).
    model = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        device_map="cuda:0", dtype=torch.bfloat16,
    )
    wavs, sr = model.generate_voice_clone(
        text=text, language=args.language,
        ref_audio=args.voice_ref,         # ✅ ref_audio, NOT reference_audio
        x_vector_only_mode=True,          # skips ref_text requirement
    )
else:
    # CustomVoice model — 9 built-in premium timbres
    model = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
        device_map="cuda:0", dtype=torch.bfloat16,
    )
    wavs, sr = model.generate_custom_voice(
        text=text, language=args.language,
        speaker="Vivian",
    )

sf.write(args.out, wavs[0], sr)
```

Skip FlashAttention 2 (`attn_implementation="flash_attention_2"`) unless it's
specifically installed — SDPA fallback works fine, just warns.

### Step 4: Bridge script (if GPU is on a different machine)

Hermes runs commands on the local machine. If the GPU is on hq-ai, bridge with SSH:

```bash
#!/bin/bash
# ~/.hermes/qwen-tts-bridge.sh
INPUT=""; OUTPUT=""; VOICE="--voice-vivian"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --text-file) INPUT="$2"; shift 2 ;;
        --out) OUTPUT="$2"; shift 2 ;;
        --voice-ref) VOICE="--voice-ref $2"; shift 2 ;;
        *) shift ;;
    esac
done
scp -q "$INPUT" hq-ai:/tmp/qwen-tts-input.txt
ssh hq-ai "~/qwen-tts-venv/bin/python ~/qwen-tts-wrapper.py $VOICE \
  --text-file /tmp/qwen-tts-input.txt --out /tmp/qwen-tts-output.wav"
scp -q hq-ai:/tmp/qwen-tts-output.wav "$OUTPUT"
```

### Step 5: Hermes config

```yaml
# ~/.hermes/config.yaml
tts:
  provider: qwen
  providers:
    qwen:
      type: command
      command: "/home/fated/.hermes/qwen-tts-bridge.sh --text-file {input_path} --out {output_path}"
      output_format: wav           # pydub+ffmpeg needed for mp3; wav works without
      timeout: 180
      voice_compatible: true       # triggers ffmpeg Ogg/Opus conversion for Telegram
  speed: 1.0

voice:
  auto_tts: false                 # voice-in → voice-out only (prevents P5000 waste on text)
```

Placeholders `{input_path}` and `{output_path}` are filled by Hermes at runtime.
Set `voice_compatible: true` and Hermes converts WAV to Opus/OGG for Telegram voice bubbles.
Without ffmpeg, voice bubbles fall back to regular file attachments.

### Step 6: Voice cloning (switch from Vivian to your voice)

Record a clean 3-second clip, save to hq-ai as `~/my-voice.wav`.
Change the bridge script's default VOICE line from `--voice-vivian` to `--voice-ref ~/my-voice.wav`.
The model switches from CustomVoice (preset timbres) to Base (clone mode).

## Known Issues

- **ffmpeg required for MP3 output**: If ffmpeg is absent, output WAV instead.
  Hermes' `voice_compatible: true` handles WAV→Opus conversion for Telegram bubbles
  as long as ffmpeg is on the Hermes machine (not the GPU machine).
- **flash-attn optional**: Install for faster inference, but SDPA fallback works.
  `pip install flash-attn --no-build-isolation` (needs RAM <96GB: set MAX_JOBS=4).
- **sox warning**: Harmless — soundfile writes WAV without it.
- **Model reload overhead**: Model unloads from GPU after idle. First TTS call in a
  session is slow (model load + GPU warmup). Subsequent calls are fast (cached).

## Telegram Limitation

Telegram Bot API does NOT support VoIP calls. Voice interaction is async:
user sends voice note → transcribed → agent responds with voice bubble.
For real-time conversation, use Discord voice channels.

#!/usr/bin/env python3
"""Qwen TTS wrapper for Hermes custom command provider.

Usage:
  Voice cloning:  wrapper.py --voice-ref ~/voice.wav --text-file /tmp/text.txt --out /tmp/out.wav
  Built-in voice: wrapper.py --voice-vivian --text-file /tmp/text.txt --out /tmp/out.wav
"""
import argparse, sys, os
import torch
import soundfile as sf
from qwen_tts import Qwen3TTSModel

MODEL = None
MODEL_NAME = None

def get_model(model_name, device="cuda:0"):
    global MODEL, MODEL_NAME
    if MODEL is None or MODEL_NAME != model_name:
        print(f"[qwen-tts] Loading model: {model_name}...", file=sys.stderr)
        MODEL = Qwen3TTSModel.from_pretrained(
            model_name,
            device_map=device,
            dtype=torch.bfloat16,
        )
        MODEL_NAME = model_name
        print(f"[qwen-tts] Model loaded.", file=sys.stderr)
    return MODEL


def main():
    parser = argparse.ArgumentParser(description="Qwen TTS wrapper for Hermes")
    parser.add_argument("--text-file", required=True, help="File containing text to speak")
    parser.add_argument("--out", required=True, help="Output audio file (.wav)")
    parser.add_argument("--voice-ref", help="Reference audio for voice cloning (3-7s WAV)")
    parser.add_argument("--voice-vivian", action="store_true", help="Use Vivian preset")
    parser.add_argument("--language", default="English")
    args = parser.parse_args()

    with open(args.text_file, "r", encoding="utf-8") as f:
        text = f.read().strip()
    if not text:
        print("[qwen-tts] Empty text, skipping.", file=sys.stderr)
        sys.exit(0)

    print(f"[qwen-tts] Generating {len(text)} chars...", file=sys.stderr)

    if args.voice_ref and os.path.exists(args.voice_ref):
        model = get_model("Qwen/Qwen3-TTS-12Hz-1.7B-Base")
        wavs, sr = model.generate_voice_clone(
            text=text, language=args.language,
            ref_audio=args.voice_ref, x_vector_only_mode=True,
        )
    else:
        speaker = "Vivian"
        model = get_model("Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice")
        wavs, sr = model.generate_custom_voice(
            text=text, language=args.language, speaker=speaker,
        )

    out_ext = os.path.splitext(args.out)[1].lower()
    if out_ext == ".mp3":
        try:
            from pydub import AudioSegment
            import io
            wav_buf = io.BytesIO()
            sf.write(wav_buf, wavs[0], sr, format="WAV")
            wav_buf.seek(0)
            audio = AudioSegment.from_wav(wav_buf)
            audio.export(args.out, format="mp3", bitrate="128k")
        except Exception as e:
            print(f"[qwen-tts] MP3 failed ({e}), writing WAV", file=sys.stderr)
            sf.write(args.out, wavs[0], sr)
    else:
        sf.write(args.out, wavs[0], sr)

    size_kb = os.path.getsize(args.out) / 1024
    print(f"[qwen-tts] Done: {args.out} ({size_kb:.1f} KB)", file=sys.stderr)


if __name__ == "__main__":
    main()

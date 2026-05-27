#!/usr/bin/env python3
"""Quick voice clone: record reference audio from Obsbot mic, clone, playback."""
import subprocess, sys
from pathlib import Path

MIC_DEVICE = "hw:0,0"      # Obsbot Tiny mic
SPEAKER_DEVICE = "hw:3,1"   # Front headphone jack
REF_DURATION = 10           # seconds to record
MODEL = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"  # or 0.6B-Base for lighter

def record(path, duration=REF_DURATION):
    print(f"Recording {duration}s from {MIC_DEVICE}...")
    subprocess.run([
        "ffmpeg", "-y", "-f", "alsa", "-ac", "1", "-ar", "48000",
        "-i", MIC_DEVICE, "-t", str(duration), path
    ], check=True)
    print(f"Saved: {path}")

def clone(ref_audio, ref_text, output, text):
    import torch, soundfile as sf
    from qwen_tts import Qwen3TTSModel

    print(f"Loading model: {MODEL}")
    model = Qwen3TTSModel.from_pretrained(
        MODEL, device_map="cuda:0", dtype=torch.bfloat16)

    print(f"Cloning voice: '{text}'")
    wavs, sr = model.generate_voice_clone(
        text=text, language="English",
        ref_audio=ref_audio, ref_text=ref_text,
    )
    sf.write(output, wavs[0], sr)
    print(f"Saved: {output}")
    return sr

def play(path):
    print("Playing...")
    subprocess.run([
        "ffmpeg", "-i", path, "-ar", "48000", "-ac", "2",
        "-f", "alsa", SPEAKER_DEVICE
    ], check=True)

if __name__ == "__main__":
    ref_wav = "/tmp/qwen_ref.wav"
    out_wav = "/tmp/qwen_clone.wav"
    ref_text = sys.argv[1] if len(sys.argv) > 1 else input("Reference transcript: ")
    gen_text = sys.argv[2] if len(sys.argv) > 2 else input("Text to synthesize: ")

    record(ref_wav)
    clone(ref_wav, ref_text, out_wav, gen_text)
    play(out_wav)

#!/usr/bin/env python3
"""End-to-end: record from mic → clone with Qwen3-TTS 1.7B → playback.

Usage:
    source ~/venvs/qwen3-tts/bin/activate
    python quick-clone.py "Text to speak in cloned voice."
"""

import subprocess, sys, os, gc
import torch, soundfile as sf
from qwen_tts import Qwen3TTSModel

REF_FILE = "/tmp/quick_clone_ref.wav"
OUT_FILE = "/tmp/quick_clone_out.wav"
MIC = "hw:0,0"
SPEAKER = "hw:3,0"
DURATION = 5  # seconds to record


def record():
    print(f"Recording {DURATION}s from {MIC}... speak now!")
    subprocess.run([
        "ffmpeg", "-y", "-f", "alsa", "-ac", "1", "-ar", "48000",
        "-i", MIC, "-t", str(DURATION), REF_FILE,
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    size = os.path.getsize(REF_FILE)
    print(f"Captured: {size/1024:.0f} KB")


def clone(text):
    print(f"Loading 1.7B Base model...")
    model = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        device_map="cuda:0", dtype=torch.bfloat16,
    )
    print(f"Cloning: \"{text}\"")
    wavs, sr = model.generate_voice_clone(
        text=text, language="English",
        ref_audio=REF_FILE, x_vector_only_mode=True,
    )
    sf.write(OUT_FILE, wavs[0], sr)
    print(f"Generated: {len(wavs[0])/sr:.1f}s → {OUT_FILE}")

    del model; gc.collect(); torch.cuda.empty_cache()


def play():
    print("Playing back...")
    subprocess.run([
        "ffmpeg", "-y", "-i", OUT_FILE, "-ar", "48000", "-ac", "2",
        "-f", "alsa", SPEAKER,
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    text = sys.argv[1] if len(sys.argv) > 1 else "Hello! This is my cloned voice."
    record()
    clone(text)
    play()
    print("Done.")

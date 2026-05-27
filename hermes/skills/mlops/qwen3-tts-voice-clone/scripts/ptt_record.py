#!/usr/bin/env python3
"""Push-to-talk recorder + dictation.
Ctrl+B: record audio to /tmp/ptt_recording.wav
Ctrl+V: record audio + transcribe to /tmp/ptt_dictation.txt

Requires: evdev, faster-whisper, ffmpeg
Run with: sudo ~/venvs/qwen3-tts/bin/python ptt_record.py
Needs sudo for /dev/input access (or add user to 'input' group).
"""

import subprocess
import signal
import sys
import os
import time
import threading
from evdev import InputDevice, ecodes, list_devices

OUTPUT_FILE = "/tmp/ptt_recording.wav"
DICTATION_FILE = "/tmp/ptt_dictation.txt"
MIC_DEVICE = "hw:0,0"
SAMPLE_RATE = 16000  # 16kHz for whisper

recording_process = None
ctrl_held = False
b_held = False
v_held = False
dictation_mode = False  # True when Ctrl+V triggered

WHISPER_MODEL = None
WHISPER_LOCK = threading.Lock()


def find_keyboards():
    keyboards = []
    for path in list_devices():
        try:
            dev = InputDevice(path)
            caps = dev.capabilities()
            if ecodes.EV_KEY in caps:
                keys = caps[ecodes.EV_KEY]
                if ecodes.KEY_A in keys or ecodes.KEY_ENTER in keys:
                    keyboards.append(dev)
        except (PermissionError, OSError):
            pass
    return keyboards


def start_recording(mode="record"):
    global recording_process, dictation_mode
    if recording_process is not None:
        return
    dictation_mode = (mode == "dictate")
    label = "DICTATING" if dictation_mode else "Recording"
    print(f"\n🎤 {label}... (release to stop)", flush=True)
    recording_process = subprocess.Popen(
        [
            "ffmpeg", "-y",
            "-f", "alsa", "-ac", "1", "-ar", str(SAMPLE_RATE),
            "-i", MIC_DEVICE,
            OUTPUT_FILE
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def transcribe():
    """Transcribe the recording using faster-whisper."""
    global WHISPER_MODEL
    if not os.path.exists(OUTPUT_FILE):
        return

    with WHISPER_LOCK:
        if WHISPER_MODEL is None:
            print("  Loading whisper model (first time)...", flush=True)
            from faster_whisper import WhisperModel
            WHISPER_MODEL = WhisperModel("small", device="cuda", compute_type="float16")

        print("  Transcribing...", flush=True)
        segments, info = WHISPER_MODEL.transcribe(OUTPUT_FILE, beam_size=5, language="en")
        text = " ".join(seg.text.strip() for seg in segments)

    if text:
        with open(DICTATION_FILE, "w") as f:
            f.write(text)
        print(f"📝 {DICTATION_FILE}: {text}", flush=True)
    else:
        print("  (no speech detected)", flush=True)


def stop_recording():
    global recording_process
    if recording_process is None:
        return
    recording_process.send_signal(signal.SIGINT)
    try:
        recording_process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        recording_process.kill()
        recording_process.wait()

    size = os.path.getsize(OUTPUT_FILE) if os.path.exists(OUTPUT_FILE) else 0
    duration = size / (SAMPLE_RATE * 2)
    label = "Dictation" if dictation_mode else "Recording"
    print(f"✅ {label}: {duration:.1f}s, {size/1024:.0f}KB", flush=True)

    was_dictation = dictation_mode
    recording_process = None

    if was_dictation and size > 16000:  # at least 0.5s of audio
        transcribe()


def handle_event(dev, event):
    global ctrl_held, b_held, v_held, recording_process

    if event.type != ecodes.EV_KEY:
        return

    key_pressed = event.value == 1
    key_released = event.value == 0

    if event.code == ecodes.KEY_LEFTCTRL or event.code == ecodes.KEY_RIGHTCTRL:
        if key_pressed:
            ctrl_held = True
        elif key_released:
            ctrl_held = False
            if recording_process:
                stop_recording()

    elif event.code == ecodes.KEY_B:
        if key_pressed:
            b_held = True
            if ctrl_held and recording_process is None:
                start_recording("record")
        elif key_released:
            b_held = False
            if recording_process and not dictation_mode:
                stop_recording()

    elif event.code == ecodes.KEY_V:
        if key_pressed:
            v_held = True
            if ctrl_held and recording_process is None:
                start_recording("dictate")
        elif key_released:
            v_held = False
            if recording_process and dictation_mode:
                stop_recording()


def main():
    print("Push-to-Talk + Dictation ready.", flush=True)
    print("  Ctrl+B = record audio  → /tmp/ptt_recording.wav", flush=True)
    print("  Ctrl+V = dictate text   → /tmp/ptt_dictation.txt", flush=True)
    print(f"  Mic: {MIC_DEVICE} @ {SAMPLE_RATE}Hz", flush=True)

    keyboards = find_keyboards()
    if not keyboards:
        print("No keyboard devices found!", file=sys.stderr)
        sys.exit(1)

    print(f"  Found {len(keyboards)} keyboard(s)", flush=True)

    try:
        from select import poll, POLLIN
        p = poll()
        fd_to_dev = {}
        for dev in keyboards:
            fd = dev.fileno()
            p.register(fd, POLLIN)
            fd_to_dev[fd] = dev

        while True:
            for fd, _ in p.poll(100):
                dev = fd_to_dev[fd]
                try:
                    for event in dev.read():
                        handle_event(dev, event)
                except BlockingIOError:
                    pass
    except KeyboardInterrupt:
        print("\nExiting...", flush=True)
        if recording_process:
            stop_recording()


if __name__ == "__main__":
    main()

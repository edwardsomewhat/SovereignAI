#!/usr/bin/env python3
"""Push-to-talk recorder: hold Ctrl+B to record from Obsbot mic, release to stop.

Requires: evdev (pip install evdev), ffmpeg, input group membership or sudo.
Usage: sudo python ptt_record.py   (or run as user in 'input' group)
"""

import subprocess
import signal
import sys
import os
import time
from evdev import InputDevice, ecodes, list_devices

OUTPUT_FILE = "/tmp/ptt_recording.wav"
MIC_DEVICE = "hw:0,0"
SAMPLE_RATE = 48000

recording_process = None
ctrl_held = False
b_held = False


def find_keyboards():
    """Find all keyboard input devices."""
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


def start_recording():
    global recording_process
    if recording_process is not None:
        return
    print("\n🎤 Recording... (release Ctrl+B to stop)", flush=True)
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
    recording_process = None
    size = os.path.getsize(OUTPUT_FILE) if os.path.exists(OUTPUT_FILE) else 0
    duration = size / (SAMPLE_RATE * 2)  # 16-bit mono
    print(f"✅ Saved: {OUTPUT_FILE} ({duration:.1f}s, {size/1024:.0f}KB)", flush=True)


def handle_event(dev, event):
    global ctrl_held, b_held, recording_process

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
                start_recording()
        elif key_released:
            b_held = False
            if recording_process:
                stop_recording()


def main():
    print("Push-to-Talk ready. Hold Ctrl+B to record.", flush=True)
    print(f"Microphone: {MIC_DEVICE} @ {SAMPLE_RATE}Hz", flush=True)
    print(f"Output: {OUTPUT_FILE}", flush=True)

    keyboards = find_keyboards()
    if not keyboards:
        print("No keyboard devices found!", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(keyboards)} keyboard(s)", flush=True)

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

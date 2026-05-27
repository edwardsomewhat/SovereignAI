---
name: uvc-ptz-camera
description: Control UVC PTZ webcams on Linux via v4l2 — pan, tilt, zoom, camera wake from sleep, format enumeration, and capture.
---

# UVC PTZ Camera Control (v4l2)

Use when: controlling a USB webcam's pan/tilt/zoom gimbal, waking a sleeping camera, capturing video/audio, or enumerating supported formats on headless Linux. Works with any UVC-compliant PTZ camera (Obsbot Tiny, Logitech PTZ Pro, etc.) — no vendor software needed.

For device-specific ranges and quirks, see `references/obsbot-tiny-1st-gen.md`.

## Prerequisites

```bash
sudo apt-get install -y v4l-utils ffmpeg alsa-utils
```

## Device Detection

```bash
# Find the camera
v4l2-ctl --list-devices
ls /dev/video*

# Get camera name
cat /sys/class/video4linux/video0/name

# Full capabilities dump
v4l2-ctl -d /dev/video0 --all
```

## Format Enumeration

```bash
# List supported video formats and resolutions
ffmpeg -f v4l2 -list_formats all -i /dev/video0
# or
v4l2-ctl -d /dev/video0 --list-formats-ext
```

## PTZ (Pan/Tilt/Zoom) Control

Most UVC PTZ cameras expose these standard controls:

```bash
# List all controls, filter for PTZ
v4l2-ctl -d /dev/video0 --list-ctrls | grep -iE "pan|tilt|zoom"

# Pan (left/right) — values in arc-seconds (1° = 3600)
v4l2-ctl -d /dev/video0 -c pan_absolute=36000    # 10° right
v4l2-ctl -d /dev/video0 -c pan_absolute=-36000   # 10° left
v4l2-ctl -d /dev/video0 -c pan_absolute=0        # center

# Tilt (up/down)
v4l2-ctl -d /dev/video0 -c tilt_absolute=36000   # 10° up
v4l2-ctl -d /dev/video0 -c tilt_absolute=-36000  # 10° down

# Zoom (digital, 0-100)
v4l2-ctl -d /dev/video0 -c zoom_absolute=50

# Speed control (set before move for controlled speed)
v4l2-ctl -d /dev/video0 -c pan_speed=40 -c tilt_speed=30
```

The Obsbot Tiny 1st Gen ranges: pan ±468000 (~±130°), tilt ±324000 (~±90°), zoom 0-100, pan_speed ±160, tilt_speed ±120.

## Camera Sleep/Wake Quirk

**Pitfall**: Many PTZ cameras park the lens and enter a low-power sleep state after inactivity. Opening the video stream (`/dev/video0`) does NOT wake them. A PTZ command DOES.

**Wake workaround** — always precede camera use with a zero-move or micro-move:
```bash
# Option A: zero-move (stays at current position, wakes camera)
v4l2-ctl -d /dev/video0 -c pan_absolute=0

# Option B: micro-nudge and return (0.5° twitch)
v4l2-ctl -d /dev/video0 -c pan_absolute=1800 && sleep 0.2 && v4l2-ctl -d /dev/video0 -c pan_absolute=0
```

This should be the FIRST command in any camera script. Without it, subsequent PTZ commands silently fail on a sleeping camera.

## Video Capture

```bash
# Single frame snapshot
ffmpeg -f v4l2 -video_size 1280x720 -i /dev/video0 -vframes 1 snapshot.jpg

# Record video (H.264 if supported, else MJPEG)
ffmpeg -f v4l2 -input_format h264 -video_size 1920x1080 -i /dev/video0 -t 10 output.mp4
```

## Audio Capture (Built-in Mic)

USB cameras with microphones appear as separate ALSA capture devices:

```bash
cat /proc/asound/cards  # find the USB Audio card
ffmpeg -f alsa -ac 1 -ar 48000 -i hw:<card>,0 -t 5 recording.wav
```

## Other Useful Controls

```bash
# Exposure
v4l2-ctl -d /dev/video0 -c auto_exposure=1     # Manual mode
v4l2-ctl -d /dev/video0 -c exposure_time_absolute=500

# White balance
v4l2-ctl -d /dev/video0 -c white_balance_automatic=0
v4l2-ctl -d /dev/video0 -c white_balance_temperature=4500

# Brightness/contrast/saturation
v4l2-ctl -d /dev/video0 -c brightness=60 -c contrast=55 -c saturation=60
```

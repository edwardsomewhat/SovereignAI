# Obsbot Tiny 1st Gen — Device Reference

## Hardware Identity
- USB ID: `3564:fef0` (Remo Tech Co., Ltd.)
- Model string: "OBSBOT Tiny: OBSBOT Tiny Camera"
- Video: `/dev/video0` and `/dev/video1` (both map to same camera, UVC driver)
- Audio: ALSA card 0, capture only at `hw:0,0` — 48kHz, mono, 16-bit S16_LE
- Formats: MJPEG, YUYV (raw), H.264 — all at 640x360, 960x540, 1280x720, 1920x1080
- Default: 1280x720 YUYV at 10fps (may differ)

## PTZ Ranges
- pan_absolute: -468000 to 468000 (step 3600 = 1°), ~±130° total range
- tilt_absolute: -324000 to 324000 (step 7200 = 2°), ~±90° total range
- zoom_absolute: 0 to 100 (digital zoom)
- pan_speed: -160 to 160
- tilt_speed: -120 to 120

## Sleep Behavior
Camera parks lens (points down) and enters low-power sleep after ~30-60 seconds of inactivity.
Opening /dev/video0 does NOT wake it.
Any PTZ command wakes it — use `pan_absolute=0` as a zero-move wake.
Without waking first, PTZ commands silently fail.

## OSC Protocol
Also supports OSC (Open Sound Control) protocol, but requires OBSBOT Center software
(Windows/Mac GUI only, not available for Linux). For Linux, UVC PTZ via v4l2 is the path.

## ConchAI Setup (this machine)
- Connected via USB 3.0 hub
- Device path: usb-0000:16:00.4-2.1
- ComfyUI uses same GPU (RTX 3090), leaves ~7.5 GB free — enough for TTS alongside

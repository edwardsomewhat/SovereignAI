# Obsbot Tiny on Linux

Using Obsbot Tiny (1st Gen, USB ID 3564:fef0) as a standard UVC/UAC webcam and microphone on Linux. No special drivers or OBSBOT Center software needed for basic capture.

## Detection

```bash
lsusb | grep -i obsbot
# Bus 007 Device 003: ID 3564:fef0 Remo Tech Co., Ltd. OBSBOT Tiny

ls /dev/video*
# /dev/video0 /dev/video1
```

Two video devices expose the same camera (different UVC interfaces). Use `/dev/video0`.

## Video Capture

Supported formats (check with `v4l2-ctl -d /dev/video0 --list-formats-ext`):

| Format | Resolutions |
|--------|-------------|
| MJPEG (compressed) | 640x360, 960x540, 1280x720, 1920x1080 |
| YUYV (raw) | 640x360, 640x480, 960x540, 1280x720, 1920x1080 |
| H.264 (compressed) | 640x360, 960x540, 1280x720, 1920x1080 |

### Capture Examples

```bash
# Test grab one frame
ffmpeg -f v4l2 -video_size 1280x720 -i /dev/video0 -vframes 1 -f null -

# Record 5-second H.264 clip
ffmpeg -f v4l2 -input_format h264 -video_size 1920x1080 -i /dev/video0 -t 5 -c copy output.mp4

# Stream MJPEG (for vision tools)
ffmpeg -f v4l2 -input_format mjpeg -video_size 1920x1080 -i /dev/video0 -vframes 1 still.jpg
```

## Microphone Capture

The Obsbot Tiny exposes a USB audio capture device:

```bash
cat /proc/asound/cards
# Card 0: OBSBOT Tiny (USB Audio)
```

Capture specs: 48 kHz, mono, 16-bit S16_LE.

```bash
# Record 3 seconds
ffmpeg -f alsa -ac 1 -ar 48000 -i hw:0,0 -t 3 reference.wav

# Monitor levels
ffmpeg -f alsa -ac 1 -ar 48000 -i hw:0,0 -af volumedetect -t 3 -f null /dev/null
```

## OSC / PTZ Control

The Obsbot Tiny supports OSC (Open Sound Control) for pan/tilt/zoom and other controls, but requires OBSBOT Center software running (GUI-only, Windows/Mac). Without it, the camera operates as a fixed UVC device with no PTZ control from Linux.

The camera stores its last position on power-off, so position it via OBSBOT Center once and it will retain that framing when connected to Linux.

## Pitfalls

- **Not a standard UVC PTZ camera**: PTZ control requires OBSBOT Center or OSC protocol — not available via standard UVC PTZ controls (no `v4l2-ctl --set-ctrl=pan_absolute`).
- **Dual video devices**: `/dev/video0` and `/dev/video1` are the same physical camera. Use `/dev/video0`.
- **Microphone auto-detected**: The USB audio interface appears automatically as an ALSA card. No configuration needed.
- **Firmware updates**: Require OBSBOT Center (Windows/Mac). Not possible from Linux.

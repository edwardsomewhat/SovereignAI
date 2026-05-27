# Obsbot Tiny Webcam (1st Gen)

USB ID: 3564:fef0 (Remo Tech Co., Ltd.)
Driver: uvcvideo (standard UVC/UAC, no special drivers needed)

## Video Capture

Device: `/dev/video0` and `/dev/video1` (both expose same camera)

Supported formats:
- MJPEG: 640x360, 960x540, 1280x720, 1920x1080
- YUYV (raw): same resolutions, 10fps typically
- H.264: same resolutions

Capture test:
```bash
ffmpeg -f v4l2 -video_size 1280x720 -i /dev/video0 -vframes 1 capture.jpg
```

## Microphone Capture

ALSA device: `hw:0,0` (USB Audio)
Format: 48kHz, 16-bit, mono
```bash
ffmpeg -f alsa -ac 1 -ar 48000 -i hw:0,0 -t 10 /tmp/mic.wav
```

## PTZ Gimbal Control

The camera exposes standard UVC PTZ controls via v4l2. **No OBSBOT Center required.**

| Control | Range | Step | Meaning |
|---------|-------|------|---------|
| `pan_absolute` | -468000 to 468000 | 3600 (1°) | Left/right, ±130° total |
| `tilt_absolute` | -324000 to 324000 | 7200 (2°) | Up/down, ±90° total |
| `zoom_absolute` | 0 to 100 | 1 | Digital zoom |
| `pan_speed` | -160 to 160 | 1 | Movement speed |
| `tilt_speed` | -120 to 120 | 1 | Movement speed |

Commands:
```bash
# Pan 10° right
v4l2-ctl -d /dev/video0 -c pan_absolute=36000
# Tilt 20° down
v4l2-ctl -d /dev/video0 -c tilt_absolute=-144000
# Zoom to 50%
v4l2-ctl -d /dev/video0 -c zoom_absolute=50
# Return to center
v4l2-ctl -d /dev/video0 -c pan_absolute=0 -c tilt_absolute=0 -c zoom_absolute=0
```

## Sleep/Wake

The camera parks its lens (points down) after inactivity. Opening the video stream alone does NOT wake it. A PTZ command is required:

```bash
# Wake the camera (no visible movement)
v4l2-ctl -d /dev/video0 -c pan_absolute=0
```

After wake, the camera responds to PTZ commands normally. Always precede camera operations with this wake command.

## Other Controls

Standard UVC image controls exposed:
- Brightness, contrast, saturation, hue (0-100)
- White balance (auto/manual, 2800K-6500K)
- Auto exposure (auto/manual/shutter priority)
- Gain (1-48)
- Sharpness (0-100)
- Backlight compensation (0-18)

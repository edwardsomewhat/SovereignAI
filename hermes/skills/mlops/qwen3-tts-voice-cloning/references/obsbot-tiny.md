# Obsbot Tiny (1st Gen) on Linux

USB ID: `3564:fef0` (Remo Tech Co., Ltd.)
Driver: `uvcvideo` (standard USB Video Class)
Works out of the box — no proprietary software needed.

## Video capture

Two video devices exposed:
- `/dev/video0` — main camera
- `/dev/video1` — metadata/secondary (usually same stream)

Supported formats:
- YUYV (raw): 640x360, 640x480, 960x540, 1280x720, 1920x1080
- MJPEG: same resolutions
- H.264: same resolutions

Quick capture:
```bash
# Grab a frame
ffmpeg -f v4l2 -video_size 1920x1080 -i /dev/video0 -vframes 1 capture.jpg

# Record video
ffmpeg -f v4l2 -video_size 1280x720 -i /dev/video0 -t 10 output.mp4
```

## Microphone

ALSA card 0, capture only. 48kHz mono 16-bit. Device: `hw:0,0`.

```bash
# Record 10 seconds
ffmpeg -f alsa -ac 1 -ar 48000 -i hw:0,0 -t 10 recording.wav
```

## UVC PTZ Gimbal Control

The Obsbot Tiny exposes standard UVC PTZ (Pan-Tilt-Zoom) controls via v4l2. Full gimbal control without any proprietary software.

### Controls

| Control | Range | Step | Meaning |
|---------|-------|------|---------|
| `pan_absolute` | -468000 to +468000 | 3600 (1°) | Left/right pan |
| `tilt_absolute` | -324000 to +324000 | 7200 (2°) | Up/down tilt |
| `zoom_absolute` | 0 to 100 | 1 | Digital zoom level |
| `pan_speed` | -160 to 160 | 1 | Pan movement speed |
| `tilt_speed` | -120 to 120 | 1 | Tilt movement speed |

Values are in arc-seconds (1/3600 degree). To convert degrees to raw value: `degrees × 3600`.

```bash
# Install v4l2-ctl if not present
sudo apt-get install -y v4l-utils

# Pan 10° right
v4l2-ctl -d /dev/video0 -c pan_absolute=36000

# Tilt 15° down
v4l2-ctl -d /dev/video0 -c tilt_absolute=-54000

# Zoom to 50%
v4l2-ctl -d /dev/video0 -c zoom_absolute=50

# Return to center, zoom out
v4l2-ctl -d /dev/video0 -c pan_absolute=0 -c tilt_absolute=0 -c zoom_absolute=0

# Smooth sweep (set speed then move)
v4l2-ctl -d /dev/video0 -c pan_speed=40 -c pan_absolute=200000
```

### Sleep/Wake

The camera parks the lens down after inactivity (privacy/sleep mode). **Opening the video stream alone does NOT wake it.** Any PTZ command does.

**Wake workaround**: always precede camera operations with a zero-move:
```bash
v4l2-ctl -d /dev/video0 -c pan_absolute=0  # wakes camera, stays in place
```

### List all controls

```bash
v4l2-ctl -d /dev/video0 --list-ctrls
```

Also includes standard webcam controls: brightness, contrast, saturation, white balance, auto-exposure, backlight compensation, sharpness, gain.

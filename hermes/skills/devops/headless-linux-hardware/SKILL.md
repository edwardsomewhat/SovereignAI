---
name: headless-linux-hardware
description: Manage audio and camera peripherals on headless Linux (no PulseAudio, no desktop) — ALSA audio discovery/playback/capture and UVC PTZ webcam control via v4l2.
---

# Headless Linux Hardware

Audio and camera peripheral management on headless Ubuntu/Debian servers. Two subsystems covered:

- **Audio (ALSA)** — device discovery, front vs rear jack selection, mixer control, ffmpeg playback/capture
- **Camera (UVC PTZ)** — pan/tilt/zoom via v4l2, sleep/wake quirks, format enumeration, video/audio capture

## Audio (ALSA)

Use when: playing or recording audio on a headless server with ALSA only (no PulseAudio/PipeWire).

### Device Discovery

```bash
# List all sound cards
cat /proc/asound/cards

# List ALSA devices (playback = 'p', capture = 'c')
ls /dev/snd/pcm*

# List mixer controls for a card
amixer -c <N> scontrols
```

### Front vs Rear Audio Jacks

On Realtek codecs (ALC1220, ALC897, etc.), front and rear jacks are often separate ALSA devices:

- **hw:N,0** — usually rear Line Out
- **hw:N,1** — usually front Headphone

Always test both when the user says they can't hear anything. Check which controls exist:
```bash
amixer -c <N> scontrols | grep -iE "headphone|line.out|front"
```

**Pitfall**: The user says "headphone jack" or "front audio jack" — always try `hw:N,1` first. If they say "rear" or "speakers in the back", try `hw:N,0`.

### Mixer: Unmute and Set Volume

```bash
# Install if missing
sudo apt-get install -y alsa-utils

# Check current state
amixer -c <N> sget 'Headphone'
amixer -c <N> sget 'Line Out'

# Unmute and set volume (0-100%)
amixer -c <N> sset 'Headphone' 70% unmute
amixer -c <N> sset 'Line Out' 70% unmute
```

Controls might show `[off]` or `[0.00dB]` — both can mean muted. Always `unmute` explicitly.

### Playback with ffmpeg

```bash
# CRITICAL: ALSA devices typically require STEREO (-ac 2). Mono will fail with:
#   "cannot set channel count to 1 (Invalid argument)"

# Play a WAV file through front headphone jack
ffmpeg -i input.wav -ar 48000 -ac 2 -f alsa hw:3,1

# Generate a test tone (sine wave) to verify output
ffmpeg -f lavfi -i "sine=frequency=440:duration=2" -ac 2 -ar 48000 -f alsa hw:3,1
```

**Pitfall**: `-ac 1` (mono) causes "Input/output error" on most ALSA hardware. Always `-ac 2`.

**Pitfall**: Some ALSA devices reject sample rates other than 48kHz. Resample with `-ar 48000`.

### Capture with ffmpeg

```bash
# Record from a USB mic (typically mono, 48kHz)
ffmpeg -f alsa -ac 1 -ar 48000 -i hw:0,0 -t 5 /tmp/recording.wav
```

### Master Volume and Auto-Mute

```bash
# Master volume often at 0% and muted on headless installs
amixer -c N sset 'Master' 100% unmute

# Auto-Mute can block rear output when front was used
amixer -c N sset 'Auto-Mute Mode' Disabled
```

### Test Tones

```bash
# 440Hz sine for 1 second — confirms audio path works
ffmpeg -f lavfi -i "sine=frequency=440:duration=1" -ac 2 -ar 48000 -f alsa hw:N,M

# 1kHz for 3 seconds — louder/more noticeable
ffmpeg -f lavfi -i "sine=frequency=1000:duration=3" -ac 2 -ar 48000 -f alsa hw:N,M
```

### No PulseAudio Fallback

If PulseAudio is not running (common on headless servers):
- All audio goes through ALSA directly (hw: devices)
- No `pactl`, no `pacmd`
- Volume/mute managed via `amixer`
- `speaker-test` from alsa-utils can also test output: `speaker-test -c 2 -t sine -l 1 -D hw:3,1`

### Audio Verification Checklist

1. `cat /proc/asound/cards` — card exists?
2. `ls /dev/snd/pcm*` — devices present?
3. `amixer -c N sget 'Headphone'` — is it muted/off?
4. `amixer -c N sset 'Headphone' 70% unmute` — fix if needed
5. `ffmpeg -f lavfi -i "sine=frequency=440:duration=1.5" -ac 2 -ar 48000 -f alsa hw:N,1` — hear a tone?

## Camera (UVC PTZ)

Use when: controlling a USB webcam's pan/tilt/zoom gimbal, waking a sleeping camera, capturing video/audio, or enumerating supported formats on headless Linux. Works with any UVC-compliant PTZ camera (Obsbot Tiny, Logitech PTZ Pro, etc.) — no vendor software needed.

For device-specific ranges and quirks, see `references/obsbot-tiny-1st-gen.md`.

### Prerequisites

```bash
sudo apt-get install -y v4l-utils ffmpeg alsa-utils
```

### Device Detection

```bash
# Find the camera
v4l2-ctl --list-devices
ls /dev/video*

# Get camera name
cat /sys/class/video4linux/video0/name

# Full capabilities dump
v4l2-ctl -d /dev/video0 --all
```

### Format Enumeration

```bash
# List supported video formats and resolutions
ffmpeg -f v4l2 -list_formats all -i /dev/video0
# or
v4l2-ctl -d /dev/video0 --list-formats-ext
```

### PTZ (Pan/Tilt/Zoom) Control

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

### Camera Sleep/Wake Quirk

**Pitfall**: Many PTZ cameras park the lens and enter a low-power sleep state after inactivity. Opening the video stream (`/dev/video0`) does NOT wake them. A PTZ command DOES.

**Wake workaround** — always precede camera use with a zero-move or micro-move:
```bash
# Option A: zero-move (stays at current position, wakes camera)
v4l2-ctl -d /dev/video0 -c pan_absolute=0

# Option B: micro-nudge and return (0.5° twitch)
v4l2-ctl -d /dev/video0 -c pan_absolute=1800 && sleep 0.2 && v4l2-ctl -d /dev/video0 -c pan_absolute=0
```

This should be the FIRST command in any camera script. Without it, subsequent PTZ commands silently fail on a sleeping camera.

### Video Capture

```bash
# Single frame snapshot
ffmpeg -f v4l2 -video_size 1280x720 -i /dev/video0 -vframes 1 snapshot.jpg

# Record video (H.264 if supported, else MJPEG)
ffmpeg -f v4l2 -input_format h264 -video_size 1920x1080 -i /dev/video0 -t 10 output.mp4
```

### Audio Capture (Built-in Mic)

USB cameras with microphones appear as separate ALSA capture devices:

```bash
cat /proc/asound/cards  # find the USB Audio card
ffmpeg -f alsa -ac 1 -ar 48000 -i hw:<card>,0 -t 5 recording.wav
```

### Other Useful Controls

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

## Reference files

- `references/obsbot-tiny-1st-gen.md` — Obsbot Tiny 1st Gen device reference: PTZ ranges, sleep behavior, hardware identity, conchai setup

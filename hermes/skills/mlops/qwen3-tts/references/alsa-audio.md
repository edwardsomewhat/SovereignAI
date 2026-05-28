# ALSA Audio on Headless Ubuntu

Debugging audio output on a headless Ubuntu Server with no PulseAudio.

## Quick Health Check

```bash
# List sound cards
cat /proc/asound/cards

# List playback devices
aplay -l

# List capture devices
arecord -l

# Check all mixer controls on card N
amixer -c N scontrols

# Check specific control
amixer -c N sget 'Master'
amixer -c N sget 'Headphone'
amixer -c N sget 'Line Out'
```

## Common Gotchas

### 1. Master volume at 0% and muted
On fresh headless installs, the Master control is often at 0% and muted.
```bash
amixer -c N sset 'Master' 100% unmute
```

### 2. Auto-Mute Mode blocks rear output
When Auto-Mute is Enabled and front headphones were ever detected, the rear Line Out is silenced even after unplugging front.
```bash
amixer -c N sget 'Auto-Mute Mode'   # Check
amixer -c N sset 'Auto-Mute Mode' Disabled
```

### 3. Mono audio rejected by stereo-only devices
ALSA devices often require stereo. ffmpeg's `sine` generator produces mono by default.
```bash
# Fix: add -ac 2 before ALSA output
ffmpeg -i input.wav -ac 2 -ar 48000 -f alsa hw:N,M
```

### 4. Sample rate mismatch
TTS models often output 24000Hz. ALSA hw devices may not support it.
```bash
# Always resample to 48000
ffmpeg -i input.wav -ar 48000 -ac 2 -f alsa hw:N,M
```

### 5. Missing alsa-utils
```bash
sudo apt-get install -y alsa-utils
```

## Test Tones

```bash
# 440Hz sine for 1 second — confirms audio path works
ffmpeg -f lavfi -i "sine=frequency=440:duration=1" -ac 2 -ar 48000 -f alsa hw:N,M

# 1kHz for 3 seconds — louder/more noticeable
ffmpeg -f lavfi -i "sine=frequency=1000:duration=3" -ac 2 -ar 48000 -f alsa hw:N,M
```

## Play WAV Files

```bash
ffmpeg -i /path/to/file.wav -ar 48000 -ac 2 -f alsa hw:N,M
```

## This Machine (conchai)

| Device | ALSA | Purpose |
|--------|------|---------|
| hw:0,0 | USB Audio (Obsbot Tiny) | Microphone capture, 48kHz mono |
| hw:1,x | HDA NVidia | HDMI/DP audio (GPU) |
| hw:2,x | HD-Audio Generic | HDMI/DP audio (AMD iGPU) |
| hw:3,0 | ALC1220 Analog (rear) | Rear line out |
| hw:3,1 | ALC1220 Analog (front) | Front headphone jack |
| hw:3,0 | ALC1220 capture | Rear mic in |

Key mixer controls on card 3: Master, Headphone, Line Out, Auto-Mute Mode, Capture.

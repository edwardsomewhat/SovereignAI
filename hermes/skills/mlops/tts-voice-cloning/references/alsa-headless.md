# ALSA Audio on Headless Ubuntu

Quick reference for setting up and testing audio on a headless Ubuntu Server (no PulseAudio, no desktop).

## Hardware Discovery

```bash
# List sound cards
cat /proc/asound/cards

# List ALSA playback devices
aplay -l

# List ALSA capture devices
arecord -l

# List /dev/snd nodes
ls -la /dev/snd/
```

Device naming: `hw:CARD,DEVICE` or `hw:CARD,DEVICE` subdevice — e.g., `hw:3,0` = card 3, device 0.

`pcmC3D0p` = Card 3, Device 0, Playback. `pcmC0D0c` = Card 0, Device 0, Capture.

## Mixer Control (amixer)

```bash
# Install if missing
sudo apt-get install -y alsa-utils

# List controls for a card
amixer -c 3 scontrols

# Check headphone state
amixer -c 3 sget Headphone

# Unmute and set volume
amixer -c 3 sset Headphone 70% unmute
```

Common controls: `Headphone`, `Line Out`, `Master`, `Capture`, `Front Mic`, `Front Mic Boost`.

## Testing Playback

```bash
# Generate sine tone and play — MUST use stereo (-ac 2)
ffmpeg -f lavfi -i "sine=frequency=440:duration=1.5" -ac 2 -f alsa hw:3,0

# Play a WAV file
ffmpeg -i audio.wav -ac 2 -f alsa hw:3,0
```

## Testing Capture

```bash
# Record from mic
ffmpeg -f alsa -ac 1 -ar 48000 -i hw:0,0 -t 5 test.wav

# Play it back
ffmpeg -i test.wav -ac 2 -f alsa hw:3,0
```

## Pitfalls

- **Channel mismatch**: Many ALSA devices (Realtek ALC1220, etc.) require stereo output. Mono (`-ac 1`) produces `cannot set channel count to 1 (Invalid argument)` or silent I/O errors. Always add `-ac 2` for playback.
- **No PulseAudio**: On headless servers, PulseAudio is typically not running. Use direct ALSA (`hw:X,Y`) or install/setup pulse if needed for more complex routing.
- **Volume at zero/muted**: Even if the device exists, the mixer may be muted or at 0%. Check with `amixer` and unmute.
- **Multiple cards**: HDMI/DP audio outputs (NVIDIA, AMD GPU) appear as separate cards. The motherboard audio (Realtek) is usually the one with headphone/line-out jacks.

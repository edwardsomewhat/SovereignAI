# ALSA Audio Setup for Headless Linux

How to discover, configure, and debug audio devices on a headless Ubuntu server with no PulseAudio or PipeWire.

## Device Discovery

```bash
# List all sound cards
cat /proc/asound/cards

# List ALSA devices (pcm devices = playback/capture endpoints)
ls -la /dev/snd/pcm*

# Show all mixer controls for a card
amixer -c CARD_NUM scontrols

# Show detailed codec info (jack sensing, pin configs)
cat /proc/asound/cardCARD_NUM/codec#0
```

## Common Pitfalls

### Master volume at 0% and muted

The most common cause of "no sound" on Realtek chips (ALC1220, ALC897, etc.):

```bash
amixer -c 3 sget 'Master'
# If showing "0% [off]" → this is the problem

amixer -c 3 sset 'Master' 100% unmute
```

The Master control is a card-wide volume that gates all outputs. Even if Line Out and Headphone are at 100%, nothing plays if Master is off.

### Auto-Mute Mode blocks rear output

When Auto-Mute is "Enabled" and headphones are plugged into the front jack, the rear Line Out is silently muted:

```bash
amixer -c 3 sget 'Auto-Mute Mode'
# If "Enabled" → disable it

amixer -c 3 sset 'Auto-Mute Mode' Disabled
```

### Front vs rear jack mapping

On ALC1220 (and most Realtek codecs):
- `hw:3,0` (pcmC3D0p) = rear panel Line Out (green jack)
- `hw:3,1` (pcmC3D1p) = front panel Headphone
- `hw:3,0` (pcmC3D0c) = rear Mic In
- `hw:3,0` capture may also map to front mic depending on jack detection

USB audio devices (webcam mics) get their own card, typically card 0:
- `hw:0,0` = capture (mono mic)
- Check with `cat /proc/asound/card0/stream0`

### ALSA requires stereo for playback

Mono audio to a stereo ALSA device fails with "cannot set channel count to 1":

```bash
# FAILS
ffmpeg -i mono.wav -f alsa hw:3,0

# WORKS
ffmpeg -i mono.wav -ac 2 -f alsa hw:3,0
```

### Sample rate mismatch

Qwen3-TTS outputs 24000 Hz. Most ALSA devices expect 44100 or 48000 Hz. Always resample:

```bash
ffmpeg -i tts_output.wav -ar 48000 -ac 2 -f alsa hw:3,0
```

## Playback test

```bash
# 1kHz sine tone, 3 seconds — if you hear this, ALSA works
ffmpeg -f lavfi -i "sine=frequency=1000:duration=3" -ac 2 -ar 48000 -f alsa hw:3,0
```

## Capture test

```bash
# Record 5s from USB mic, play back
ffmpeg -f alsa -ac 1 -ar 48000 -i hw:0,0 -t 5 /tmp/test.wav
ffmpeg -i /tmp/test.wav -ar 48000 -ac 2 -f alsa hw:3,0
```

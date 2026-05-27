---
name: headless-linux-audio
description: ALSA audio device discovery, playback, and capture on headless Linux (no PulseAudio). Identify front vs rear jacks, unmute controls, use ffmpeg for playback/capture.
---

# Headless Linux Audio (ALSA)

Use when: playing or recording audio on a headless Ubuntu/Debian server with ALSA only (no PulseAudio/PipeWire). Covers device discovery, front vs rear jack selection, ffmpeg playback/capture, and mixer control.

## Device Discovery

```bash
# List all sound cards
cat /proc/asound/cards

# List ALSA devices (playback = 'p', capture = 'c')
ls /dev/snd/pcm*

# List mixer controls for a card
amixer -c <N> scontrols
```

## Front vs Rear Audio Jacks

On Realtek codecs (ALC1220, ALC897, etc.), front and rear jacks are often separate ALSA devices:

- **hw:N,0** — usually rear Line Out
- **hw:N,1** — usually front Headphone

Always test both when the user says they can't hear anything. Check which controls exist:
```bash
amixer -c <N> scontrols | grep -iE "headphone|line.out|front"
```

**Pitfall**: The user says "headphone jack" or "front audio jack" — always try `hw:N,1` first. If they say "rear" or "speakers in the back", try `hw:N,0`.

## Mixer: Unmute and Set Volume

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

## Playback with ffmpeg

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

## Capture with ffmpeg

```bash
# Record from a USB mic (typically mono, 48kHz)
ffmpeg -f alsa -ac 1 -ar 48000 -i hw:0,0 -t 5 /tmp/recording.wav
```

## No PulseAudio Fallback

If PulseAudio is not running (common on headless servers):
- All audio goes through ALSA directly (hw: devices)
- No `pactl`, no `pacmd`
- Volume/mute managed via `amixer`
- `speaker-test` from alsa-utils can also test output: `speaker-test -c 2 -t sine -l 1 -D hw:3,1`

## Verification Checklist

1. `cat /proc/asound/cards` — card exists?
2. `ls /dev/snd/pcm*` — devices present?
3. `amixer -c N sget 'Headphone'` — is it muted/off?
4. `amixer -c N sset 'Headphone' 70% unmute` — fix if needed
5. `ffmpeg -f lavfi -i "sine=frequency=440:duration=1.5" -ac 2 -ar 48000 -f alsa hw:N,1` — hear a tone?

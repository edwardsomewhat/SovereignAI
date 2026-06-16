---
name: esp32-firmware
description: "Flash and configure ESP32/ESP32-S3/ESP32-C3/ESP32-C6 firmware from a headless Linux CLI — device detection, esptool flashing, manifest discovery, PlatformIO pitfalls, serial diagnostics, and WireClaw configuration."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [esp32, embedded, firmware, flashing, esptool, wireclaw, microcontroller]
---

# ESP32 Firmware Flashing & Configuration

Flash firmware to ESP32 family devices (S3, C3, C6) from a headless Linux CLI without browser-based tools. Covers device detection, esptool flashing, firmware URL discovery from web-flash manifests, PlatformIO pitfalls, serial diagnostics, and WireClaw-specific configuration.

## Quick Reference

| Task | Command / Approach |
|------|-------------------|
| Find ESP32 device | `lsusb \| grep -i espressif` then `ls /dev/ttyACM*` |
| Identify chip | `esptool --port /dev/ttyACM0 chip-id` |
| Flash firmware | `esptool --port /dev/ttyACM0 write-flash 0x0 bootloader.bin 0x8000 partitions.bin ...` |
| Monitor serial | `stty -F /dev/ttyACM0 115200 raw -echo; cat /dev/ttyACM0` |
| Discover firmware URLs | Fetch `manifest.json` from the web-flash page (see technique below) |

## Device Detection

ESP32 devices appear as Espressif USB JTAG/serial debug units:

```bash
lsusb | grep -i espressif
# Bus 001 Device 006: ID 303a:1001 Espressif USB JTAG/serial debug unit

ls /dev/ttyACM*
# /dev/ttyACM0
```

**Pitfall:** The device number can change after resets (`/dev/ttyACM0` → `/dev/ttyACM1`). Always re-check after flashing.

## Permission Fix

ESP32 serial ports are owned by `root:dialout`. Quick fix:

```bash
sudo chmod a+rw /dev/ttyACM*
# Or: sudo usermod -aG dialout $USER  (requires new login)
```

## Installing esptool

```bash
pip3 install --break-system-packages esptool
# Use --break-system-packages on Ubuntu 24.04+ with PEP 668
```

## Firmware URL Discovery (Web Flash Manifest)

Many ESP32 projects use browser-based flashing (esp-web-tools). To find the raw firmware URLs without a browser:

1. Load the flash page and check for `<esp-web-install-button>` 
2. Get the `manifest` attribute
3. Fetch the manifest JSON — it lists all partition files and offsets

Example for WireClaw:
```bash
# The flash page at wireclaw.io/flash.html has:
# <esp-web-install-button manifest="firmware/manifest.json">

# Fetch the manifest:
curl -sL "https://wireclaw.io/firmware/manifest.json"
# Returns JSON with chipFamily entries, each listing parts with path + offset

# Download firmware files (ESP32-S3 example):
BASE="https://wireclaw.io/firmware/esp32s3"
for f in bootloader.bin partitions.bin boot_app0.bin firmware.bin littlefs.bin; do
  curl -sLo "$f" "$BASE/$f"
done
```

## Flashing with esptool

Flash all partitions in one command for speed:

```bash
esptool --port /dev/ttyACM0 --baud 460800 \
  --before default-reset --after hard-reset \
  write-flash --flash-mode dio --flash-size 4MB --flash-freq 80m \
  0x0 bootloader.bin \
  0x8000 partitions.bin \
  0xe000 boot_app0.bin \
  0x10000 firmware.bin \
  0x290000 littlefs.bin
```

**Verify flash size:** Use `esptool chip-id` to confirm the actual flash size (e.g., "Embedded Flash 4MB"). Mismatched `--flash-size` can cause silent corruption.

## PlatformIO Pitfalls

### Board Config Mismatch

PlatformIO may auto-detect a different board variant than your actual hardware. The build output shows what it thinks you have:

```
HARDWARE: ESP32S3 240MHz, 320KB RAM, 8MB Flash
```

If your board actually has **4MB Flash** (check with `esptool chip-id`), a PlatformIO build with 8MB Flash config will produce firmware that fails to boot with:

```
E (226) esp_image: invalid segment length 0xffffffff
E (226) boot: OTA app partition slot 0 is not bootable
```

**Fix:** Always flash known-good firmware first (from the project's web-flash binaries), then only flash the filesystem partition if you need custom data.

### Failed Upload Corrupts Firmware

If `pio run -t upload` fails mid-flash ("The chip stopped responding"), the firmware partition may be partially written and unbootable. You MUST re-flash the firmware partition from known-good binaries.

### Building Only the Filesystem

When you only need to customize the SPIFFS/LittleFS data (e.g., config.json):

```bash
pio run -e esp32-s3 -t buildfs
# Output: .pio/build/esp32-s3/littlefs.bin
# Flash it manually with esptool (safer than pio upload)
```

## Serial Diagnostics

Monitor boot messages to diagnose issues:

```bash
# Set raw mode and read
stty -F /dev/ttyACM0 115200 raw -echo -hupcl
timeout 15 cat /dev/ttyACM0
```

Key boot messages:
- `ESP-ROM:esp32s3` — ROM bootloader started
- `invalid segment length 0xffffffff` — corrupted firmware
- `OTA app partition slot 0 is not bootable` — firmware partition damaged
- Normal boot shows WiFi connection attempts, IP acquisition, etc.

## WireClaw Configuration

WireClaw is an AI agent firmware for ESP32 that communicates via Telegram/Serial/NATS and uses LLM APIs.

### Configuration File Format

```json
{
  "wifi_ssid": "MyNetwork",
  "wifi_pass": "password",
  "api_key": "sk-...",
  "model": "deepseek-v4-flash",
  "device_name": "wireclaw-01",
  "api_base_url": "https://api.deepseek.com/v1",
  "max_tokens": 4096,
  "temperature": 0.7,
  "timezone": "PST8PDT,M3.2.0,M11.1.0"
}
```

### API Provider Configuration

WireClaw supports two API modes:

| Mode | api_base_url | api_key | 
|------|-------------|---------|
| OpenRouter (default) | empty | OpenRouter key |
| Custom API (OpenAI-compatible) | `https://api.deepseek.com/v1` | Provider's API key |

**Pitfall:** The setup portal labels `api_base_url` as "only needed for local LLMs" but it works for ANY OpenAI-compatible endpoint, including cloud APIs like DeepSeek. Set it to use providers other than OpenRouter.

### Configuration Flow (Headless Limitation)

WireClaw's primary configuration method is a captive portal on the "WireClaw-Setup" WiFi AP (192.168.4.1). From a headless server, you CANNOT connect to this AP.

**Options:**
1. **Phone/laptop**: Connect to "WireClaw-Setup" → captive portal auto-opens → fill form → Save & Reboot
2. **Pre-baked filesystem**: Build a custom littlefs.bin with config.json using PlatformIO `buildfs`, then flash only that partition
3. **Web UI after setup**: Once on WiFi, access `http://wireclaw-01.local/api/config` via REST API

### Model Discovery

To find available models for a provider:

```bash
# DeepSeek API example:
curl -s https://api.deepseek.com/v1/models \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); [print(m['id']) for m in d.get('data',[])]"
```

## Reference Files

- `references/wireclaw-setup.md` — Full WireClaw setup walkthrough with config examples and API notes

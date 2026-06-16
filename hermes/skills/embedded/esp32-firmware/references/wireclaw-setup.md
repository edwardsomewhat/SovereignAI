# WireClaw Setup Walkthrough

Full end-to-end guide for flashing and configuring WireClaw on ESP32-S3.

## Hardware Requirements

- ESP32-S3 (or C3, C6) with 4MB+ flash
- USB-C cable (data-capable, not charge-only)

## Step 1: Firmware Flashing

### Download firmware

```bash
mkdir -p /tmp/wireclaw-flash && cd /tmp/wireclaw-flash
BASE="https://wireclaw.io/firmware/esp32s3"
for f in bootloader.bin partitions.bin boot_app0.bin firmware.bin littlefs.bin; do
  curl -sLo "$f" "$BASE/$f"
done
```

### Flash

```bash
sudo chmod a+rw /dev/ttyACM0
esptool --port /dev/ttyACM0 --baud 460800 \
  --before default-reset --after hard-reset \
  write-flash --flash-mode dio --flash-size 4MB --flash-freq 80m \
  0x0 bootloader.bin \
  0x8000 partitions.bin \
  0xe000 boot_app0.bin \
  0x10000 firmware.bin \
  0x290000 littlefs.bin
```

Flash takes ~30 seconds. All partitions verified.

## Step 2: Configuration (Captive Portal)

After flashing, ESP32 boots into setup mode:

1. ESP32 creates open WiFi AP: **WireClaw-Setup**
2. Connect phone/laptop to it
3. Captive portal opens automatically (or browse to 192.168.4.1)
4. Fill in the form
5. Save & Reboot

### DeepSeek API Configuration

| Field | Value |
|-------|-------|
| WiFi SSID | Your network name |
| WiFi Password | Your WiFi password |
| API Key | DeepSeek API key (sk-...) |
| Model | `deepseek-v4-flash` |
| API Base URL | `https://api.deepseek.com/v1` |
| Device Name | `wireclaw-01` (or custom) |

**Important:** WireClaw's form says "API Base URL is only needed for local LLMs" but this is misleading — it works for ANY OpenAI-compatible endpoint, including DeepSeek's cloud API. Set it to bypass OpenRouter.

### OpenRouter Configuration (default)

| Field | Value |
|-------|-------|
| API Key | OpenRouter API key |
| Model | `openai/gpt-4o-mini` or any OpenRouter model |
| API Base URL | Leave blank |

## Step 3: Post-Setup Access

After reboot, WireClaw connects to your WiFi. Find it at:

- `http://wireclaw-01.local/` (mDNS)
- Or the IP assigned by your router

### REST API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/config` | GET | Current config (sensitive fields masked) |
| `/api/config` | POST | Update config (JSON merge) |
| `/api/prompt` | GET/POST | System prompt |
| `/api/memory` | GET/POST | AI persistent memory |
| `/api/status` | GET | Device status, uptime, WiFi info |
| `/api/reboot` | POST | Reboot device |

Example:
```bash
# Check status
curl http://wireclaw-01.local/api/status

# Change model
curl -X POST -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-pro"}' \
  http://wireclaw-01.local/api/config
```

## Step 4: Serial Commands

WireClaw supports serial commands at 115200 baud:

| Command | Action |
|---------|--------|
| `/setup` | Re-enter setup mode (creates AP) |
| `/devices` | List registered sensors/actuators |
| `/rules` | List automation rules |
| `/memory` | Show AI persistent memory |
| `/reboot` | Reboot device |

```bash
# Connect to serial monitor
stty -F /dev/ttyACM0 115200 raw -echo
cat /dev/ttyACM0 &  # Read output
echo "/devices" > /dev/ttyACM0  # Send command
```

## Supported Models

### DeepSeek API (api_base_url: https://api.deepseek.com/v1)

Models confirmed available (June 2026):
- `deepseek-v4-flash` — fast, cost-effective
- `deepseek-v4-pro` — higher quality, slower

To check current models:
```bash
curl -s https://api.deepseek.com/v1/models \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" | jq '.data[].id'
```

### Local LLM (HTTP)

For local models via Ollama/llama.cpp:
```json
{
  "api_base_url": "http://192.168.1.50:11434/v1/chat/completions",
  "model": "gpt-oss:latest",
  "api_key": ""
}
```

Recommended local models: `gpt-oss:latest` (20B), `qwen3` variants.

## Common Issues

### ESP32 not detected
- Try a different USB cable (many are charge-only)
- Check `dmesg | tail -20` after plugging in
- ESP32-S3 has built-in USB-serial; no external chip needed

### "Chip stopped responding" during flash
- ESP32 may need manual download mode: hold BOOT, press RESET, release RESET, release BOOT
- Or try again — auto-reset via DTR/RTS sometimes needs a second attempt

### Boot loop: "No bootable app partitions"
- Firmware partition corrupted. Re-flash all partitions from known-good binaries
- Do NOT mix PlatformIO-built firmware with web-flash firmware on different board configs (8MB vs 4MB flash mismatch)

### Device number changes after reset
- Normal behavior. After flashing, check `ls /dev/ttyACM*` — device may be `/dev/ttyACM1` instead of `/dev/ttyACM0`

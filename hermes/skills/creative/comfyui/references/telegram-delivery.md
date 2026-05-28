# Telegram Delivery for Generated Images

Pattern for delivering ComfyUI outputs to a Telegram bot. Used by the Creative
agent in the SovereignAI crew.

## Prerequisites

- Telegram bot token (create via @BotFather)
- Chat ID of the recipient (get via `getUpdates` after sending any message to the bot)

## Send an Image

```bash
curl -s -X POST "https://api.telegram.org/bot<TOKEN>/sendPhoto" \
  -F chat_id=<CHAT_ID> \
  -F photo=@/path/to/image.png \
  -F caption="Your caption here"
```

## Send a Status Message

```bash
curl -s -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
  -d chat_id=<CHAT_ID> \
  -d text="Your message here"
```

## Finding the Chat ID

```bash
# After sending any message to the bot in Telegram:
curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); \
  [print(f'chat_id: {m[\"message\"][\"chat\"][\"id\"]} | {m[\"message\"][\"chat\"].get(\"first_name\",\"?\")}') \
  for u in d.get('result',[]) if 'message' in u]"
```

## End-to-End Creative Agent Pipeline

1. Agent receives image generation request with prompt
2. Agent creates or selects a ComfyUI workflow JSON
3. Agent submits to ComfyUI via `POST /api/prompt` (wrapped in `{"prompt": ...}`)
4. Agent polls `GET /history/<prompt_id>` until `outputs` appear
5. Agent downloads the image (scp from remote node if needed)
6. Agent sends image to Telegram via `sendPhoto` with caption

## Hermes Gateway vs Direct API

The Creative agent pipeline uses **direct Telegram Bot API calls** (curl /sendPhoto).
This is distinct from the Hermes Gateway (`hermes gateway run`) which provides
**two-way chat** (users can message the bot and Hermes responds).

- **Direct API (current)**: Token used inline in curl commands. Single-direction
  (agent → user). Images and status messages pushed to Telegram.
- **Hermes Gateway (future)**: Token must be set in `~/.hermes/.env` as
  `TELEGRAM_BOT_TOKEN=<token>`. Run `hermes gateway setup` then
  `hermes gateway install`. Enables two-way chat where users can send prompts
  to the bot and Hermes responds.

## SovereignAI-Specific

- **hq-ai** (100.84.92.74): ComfyUI 0.8.2 on :8188, P5000 16GB. Checkpoints: Juggernaut_XL_v9.safetensors
- **conchai** (100.69.153.16): ComfyUI 0.21.1 on :8188, RTX 3090 24GB. Workspace: /mnt/hermes_data/comfy/. Checkpoints: juggernautXL_ragnarokBy, flux1-dev-fp8, dreamshaper_8, photon_v1, qwen_image_edit, sd_xl_base_1.0
- **Bot**: @SovereignHQbot, token and chat_id in Hermes memory
- **Workflow pattern**: KSampler with dpmpp_2m + karras at 20 steps for SDXL (~40s on 3090). SDTurboScheduler only works with turbo-tuned models — avoid with standard checkpoints.

# Telegram Bot Setup Session Notes - 2026-05-12

## Environment
- OS: Linux (Ubuntu-based, same as signal-cli session)
- User: fated
- Telegram client: Official apps (Android/iOS/Web)
- Bot creation method: @BotFather via Telegram chat

## Key Actions

### 1. Bot Creation
- User interacted with @BotFather to create a new bot
- Provided bot name and username (ending in 'bot')
- Received bot token from BotFather

### 2. Token Provision
- User provided the following bot token:
  ```
  8731025975:AAHaRL9Ibkx1A0t1bDh7em5E2yXrMzWB__k
  ```
- This token follows the standard format: `<bot_id>:<hash>`
- Token was saved to Hermes memory for future reference

### 3. Validation Approach Discussed
- Recommended validation via `getMe` API endpoint:
  ```bash
  curl -s "https://api.telegram.org/bot8731025975:AAHaRL9Ibkx1A0t1bDh7em5E2yXrMzWB__k/getMe"
  ```
- To send messages, need to obtain chat_id via `getUpdates` after initiating conversation with bot

## Pitfalls Encountered (General, not specific to this token)
- **Token security**: Emphasized that token must be kept private; anyone with it can control the bot
- **Chat ID acquisition**: New bots don't receive updates until user initiates chat (sends `/start` or any message)
- **Rate limits**: Telegram API limits (~30 messages per second)
- **HTTPS requirement**: All API calls must use https://api.telegram.org
- **Privacy mode**: By default, bots in groups only see messages that start with '/' or mention the bot

## Working Command Sequence (Template)
```bash
# 1. Verify token validity
curl -s "https://api.telegram.org/bot<TOKEN>/getMe"

# 2. Start conversation with bot in Telegram (user sends any message to bot)

# 3. Get updates to find chat_id
curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates" | jq '.result[-1].message.chat.id'

# 4. Send a test message (replace CHAT_ID with value from step 3)
curl -s -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
     -d chat_id=<CHAT_ID> \
     -d text="Hello from Hermes bot!"

# 5. Optional: Set up webhook for production (instead of polling)
# curl -s "https://api.telegram.org/bot<TOKEN>/setWebhook?url=<YOUR_WEBHOOK_URL>"
```

## Verification Steps
After bot creation:
- Token validation via `getMe` returns `"ok": true`
- Bot responds to `/start` in Telegram
- `getUpdates` shows recent messages from users
- `sendMessage` delivers messages to target chat

## References Used
- Telegram Bot API: https://core.telegram.org/bots/api
- BotFather guide: https://core.telegram.org/bots#6-botfather
- Official Telegram apps for bot interaction
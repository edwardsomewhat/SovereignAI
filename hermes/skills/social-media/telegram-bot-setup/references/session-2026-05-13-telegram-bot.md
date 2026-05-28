# Session-Specific Details: Telegram Bot Setup (2026-05-13)

## Summary
This session covered creating a Telegram bot, obtaining its token, finding the user's chat ID, testing message sending, and experimenting with a simple polling/echo script.

## Environment
- OS: Linux (Ubuntu-based, as seen from `apt` usage)
- Tools available: `curl`, `python3`, `jq` (optional)
- Hermes version: unspecified, but agent capable of running Python scripts and making HTTP requests.

## Step-by-Step Commands Used

### 1. Bot Creation & Token Retrieval
- User created bot via @BotFather.
- Token obtained: `8731025975:AAGsNgLbk5wGVXrWhjRKLNvtP2tU6J6y3gA`
- Token saved to Hermes memory via `memory add`.

### 2. Getting Chat ID
- User messaged the bot (sent `/start` or any text) to initialize the chat.
- Ran:
  ```bash
  curl -s "https://api.telegram.org/bot8731025975:AAGsNgLbk5wGVXrWhjRKLNvtP2tU6J6y3gA/getUpdates"
  ```
- Extracted `chat.id` from the returned JSON: `6311989610`.
- Chat ID saved to Hermes memory.

### 3. Testing Send Message
- Sent a test message:
  ```bash
  curl -s -X POST "https://api.telegram.org/bot8731025975:AAGsNgLbk5wGVXrWhjRKLNvtP2tU6J6y3gA/sendMessage" \
       -d chat_id=6311989610 \
       -d text="Test from Hermes"
  ```
- Response confirmed delivery (`ok`: true, `message_id`: 6).

### 4. Simple Echo Bot Script (Polling)
- Created `/home/fated/telegram_bot.py`:
  ```python
  import time, requests, json

  TOKEN = "8731025975:AAGsNgLbk5wGVXrWhjRKLNvtP2tU6J6y3gA"
  URL = f"https://api.telegram.org/bot{TOKEN}"

  def get_updates(offset=None):
      params = {"timeout": 30, "offset": offset}
      resp = requests.get(URL + "/getUpdates", params=params)
      return resp.json()

  def send_message(chat_id, text):
      requests.post(URL + "/sendMessage", data={"chat_id": chat_id, "text": text})

  def main():
      offset = None
      print("Bot started...")
      while True:
          updates = get_updates(offset)
          if updates.get("ok"):
              for u in updates["result"]:
                  offset = u["update_id"] + 1
                  if "message" in u and "text" in u["message"]:
                      chat_id = u["message"]["chat"]["id"]
                      text = u["message"]["text"]
                      print(f"Received: {text}")
                      send_message(chat_id, f"You said: {text}")
          time.sleep(1)

  if __name__ == "__main__":
      main()
  ```
- Started in background via `hermes` tool (process ID 16270).
- User later requested to stop it; process was killed via `process kill proc_da4b159ea96d`.

## Key Learnings / Pitfalls
- **Privacy Mode**: Bots in groups only see messages that start with `/` or mention the bot unless privacy is disabled. For private chats, this is not an issue.
- **Initial Contact Required**: `getUpdates` returns empty until the user has sent at least one message to the bot (or the bot has sent a message and the user replied). Sending `/start` ensures the bot sees the user.
- **Token Security**: Treat the token like a password; if leaked, revoke via BotFather `/revoke` or `/token`.
- **Rate Limits**: Stay under ~30 messages per second to avoid HTTP 429.
- **Long Polling**: The `timeout` parameter in `getUpdates` (set to 30 seconds) helps reduce unnecessary requests.

## Reference Commands for Future Sessions
```bash
# Verify token
curl -s "https://api.telegram.org/bot<TOKEN>/getMe"

# Get updates (after user has messaged bot)
curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates" | jq

# Send message
curl -s -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
     -d chat_id=<CHAT_ID> \
     -d text="Your message"

# Set webhook (alternative to polling)
curl -s -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
     -d url="https://your.domain.com/bot<TOKEN>"
```

## Cleanup
- To stop any running polling scripts, identify the process (e.g., via `ps aux | grep telegram_bot.py`) and kill it.
- To remove the bot entirely, use BotFather's `/deletebot` command.

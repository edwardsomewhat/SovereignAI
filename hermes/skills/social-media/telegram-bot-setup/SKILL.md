---
name: telegram-bot-setup
description: Create and configure a Telegram bot via BotFather, obtain token, and use the Telegram Bot API for sending/receiving messages.
category: social-media
---

# Telegram Bot Setup

This skill covers creating a Telegram bot using @BotFather, securing the bot token, and using the Telegram Bot API to send messages, get updates, and perform basic bot operations.

## Prerequisites

- A Telegram account (via mobile app or web.telegram.org)
- Ability to chat with @BotFather
- Optional: `curl` or HTTP client for testing API calls
- Optional: `jq` for parsing JSON responses

## Steps

### 1. Create the Bot

1. Open Telegram and search for `@BotFather`.
2. Start a chat and send `/newbot`.
3. Follow the prompts:
   - Provide a display name for your bot (e.g., `My Test Bot`).
   - Provide a username ending in `bot` (e.g., `my_test_bot` or `my_test_bot`).
4. BotFather will reply with a message containing your bot token. Save this token securely.

   Example token format: `123456789:AAHdqTcvCH1vGWXxfSeofSAs0K5PALDsaw`

   > **Important:** Treat the token like a password. Anyone with the token can control your bot. Do not share it publicly or commit it to source control.

### 2. Save the Token (Optional but Recommended)

For reuse in scripts or skills, you can store the token in an environment variable or a secure vault. In this Hermes session, you can save it to memory:

```bash
# Example: saving to Hermes memory (done automatically by agent)
# memory add --target memory --content "Telegram bot token: <your_token_here>"
```

### 3. Test the Token

Use `getMe` to verify the token is valid:

```bash
curl -s "https://api.telegram.org/bot<TOKEN>/getMe" | jq
```

Expected response (simplified):

```json
{
  "ok": true,
  "result": {
    "id": 123456789,
    "is_bot": true,
    "first_name": "My Test Bot",
    "username": "my_test_bot",
    ...
  }
}
```

### 4. Send a Message

To send a message, you need the `chat_id` of the recipient. You can get this by:

- Having the bot send a message to a group or person and checking updates (see next step), or
- Using your own user ID (you can get it by chatting with @userinfobot or checking updates after sending a message to the bot).

Send a message:

```bash
curl -s -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
     -d chat_id=<CHAT_ID> \
     -d text="Hello from Hermes!"
```

Replace `<CHAT_ID>` with the target chat's numeric ID (can be negative for groups/channels).

### 5. Receive Updates (Polling)

To receive messages sent to your bot, use `getUpdates`:

```bash
curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates" | jq
```

This returns an array of update objects. Each update contains a `message` object with `chat.id` (the sender's chat ID) and `text`.

> **Note:** For production bots, consider using webhooks instead of polling. See the Telegram Bot API documentation for setting up a webhook.

### 6. Common BotFather Commands

After bot creation, you can manage it with BotFather:

- `/token` – Generate a new token (invalidates the old one).
- `/revoke` – Revoke the current token (use if compromised).
- `/setname` – Change the bot's display name.
- `/setdescription` – Set a short description.
- `/setabouttext` – Set the bot's "about" info.
- `/setuserpic` – Upload a profile picture.
- `/setcommands` – Define bot commands (shown in Telegram's menu).
- `/deletebot` – Delete the bot and revoke its token.

## Pitfalls & Troubleshooting

- **Invalid token:** Double-check you copied the entire token correctly (no extra spaces).
- **Chat ID not found:** Ensure the bot has been started by the user (they sent `/start` or any message) before trying to get updates. Privacy mode may hide group messages unless the bot is mentioned or a command is used.
- **Rate limits:** Telegram imposes limits on API calls. Stay below 30 messages per second.
- **HTTPS required:** All API calls must be made to `api.telegram.org` over HTTPS.
- **Token leakage:** If you accidentally expose the token, revoke it immediately via BotFather (`/revoke`) or by generating a new token (`/token`).

## Testing

After setting up your bot, you can run a quick end-to-end test:

1. Send `/start` to your bot from your Telegram account.
2. Run `curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates"` to see the update.
3. Extract the `chat.id` from the update.
4. Send a test message using `sendMessage` with that chat ID.
5. Verify you receive the message in Telegram.


## Integrating with Hermes Agent (Advanced)

The simple echo/polling bot is useful for testing, but to have the bot act as an interface to the Hermes agent, you need to forward incoming messages to Hermes and send back the agent's responses.

### Option 1: Use Hermes Skills
Create or use a skill that:
- Polls `getUpdates` (or sets up a webhook)
- For each new message, calls `delegate_task` (or the Hermes agent's internal API) to get a response
- Sends the response back via `sendMessage`

### Option 2: External Script with Hermes CLI
If you have the `hermes` CLI installed and configured to talk to the same agent instance, your polling script can shell out to `hermes` to get a response for each message.

### Example Pseudocode
```python
# In your message loop:
if "message" in u and "text" in u["message"]:
    chat_id = u["message"]["chat"]["id"]
    user_text = u["message"]["text"]
    # Forward to Hermes agent (pseudo-code)
    hermes_response = delegate_task(prompt=user_text, ...)  # or use hermes CLI
    send_message(chat_id, hermes_response)
```

> **Note:** The user expressed preference for a direct link to speak with the Hermes agent rather than an echo bot. This section captures that workflow.


## Maintenance

The simple echo/polling bot is useful for testing, but to have the bot act as an interface to the Hermes agent, you need to forward incoming messages to Hermes and send back the agent's responses.

### Option 1: Use Hermes Skills
Create or use a skill that:
- Polls `getUpdates` (or sets up a webhook)
- For each new message, calls `delegate_task` (or the Hermes agent's internal API) to get a response
- Sends the response back via `sendMessage`

### Option 2: External Script with Hermes CLI
If you have the `hermes` CLI installed and configured to talk to the same agent instance, your polling script can shell out to `hermes` to get a response for each message.

### Example Pseudocode
```python
# In your message loop:
if "message" in u and "text" in u["message"]:
    chat_id = u["message"]["chat"]["id"]
    user_text = u["message"]["text"]
    # Forward to Hermes agent (pseudo-code)
    hermes_response = delegate_task(prompt=user_text, ...)  # or use hermes CLI
    send_message(chat_id, hermes_response)
```

> **Note:** The user expressed preference for a direct link to speak with the Hermes agent rather than an echo bot. This section captures that workflow.


## Maintenance
- To rotate the token, use BotFather's `/token` command.
- To update the bot's description or commands, use the respective BotFather commands.
- If you no longer need the bot, delete it via BotFather's `/deletebot`.

## References

- Official Telegram Bot API: https://core.telegram.org/bots/api
- BotFather introduction: https://core.telegram.org/bots#6-botfather
- Session-specific notes and troubleshooting: See `references/session-2026-05-12-telegram-bot.md` and `references/session-2026-05-13-telegram-bot.md` for detailed environment info, pitfalls encountered, and working command sequences from this session.
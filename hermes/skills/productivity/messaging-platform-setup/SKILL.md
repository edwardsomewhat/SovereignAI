---
name: messaging-platform-setup
description: "Set up messaging platforms (Signal CLI, Telegram Bot API) for use with Hermes Agent — install dependencies, authenticate/link accounts, verify, and send test messages."
version: 1.0.0
author: Hermes Agent (consolidated from signal-cli-setup + telegram-bot-setup)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [messaging, signal, telegram, setup, communication, bot]
---

# Messaging Platform Setup

Set up messaging platforms on this machine so Hermes Agent can send and receive messages through them.

## Common Pattern

All messaging platforms follow the same setup flow:

1. **Install dependencies** — language runtimes, CLI tools, or SDKs
2. **Authenticate** — link to an existing account or register a new one
3. **Verify** — confirm the connection works (list accounts, get bot info)
4. **Test** — send a test message to yourself

---

## Signal (signal-cli)

Signal CLI is a Java command-line interface for Signal. Supports linking as a secondary device or registering a new phone number.

### Prerequisites

- A Linux system with `sudo` access
- A smartphone with Signal installed (for linking) OR a phone number capable of receiving SMS/voice calls (for registration)
- Java runtime 17+ (OpenJDK recommended)

### Installation

```bash
# 1. Install Java
sudo apt update
sudo apt install -y openjdk-25-jre-headless   # or openjdk-21-jre-headless
java -version

# 2. Download and extract signal-cli
mkdir -p ~/signal-cli && cd ~/signal-cli
VERSION="0.14.3"  # replace with latest from https://github.com/AsamK/signal-cli/releases
curl -L -O https://github.com/AsamK/signal-cli/releases/download/v${VERSION}/signal-cli-${VERSION}.tar.gz
tar --no-same-owner --no-same-permissions -xzf signal-cli-${VERSION}.tar.gz
```

### Link to Existing Account (Recommended)

```bash
~/signal-cli/signal-cli-${VERSION}/bin/signal-cli link
```

This outputs a `sgnl://linkdevice?...` URL. On your phone:
1. Signal → Settings → Linked Devices → Link New Device
2. Scan the QR code
3. Wait for linking to complete

Verify:
```bash
~/signal-cli/signal-cli-${VERSION}/bin/signal-cli listAccounts
~/signal-cli/signal-cli-${VERSION}/bin/signal-cli listDevices
```

### Register a New Phone Number (Optional)

```bash
# -a/--account flag must come BEFORE the subcommand
~/signal-cli/signal-cli-${VERSION}/bin/signal-cli -a +15551234567 register
```

If "Captcha required" error:
1. Visit https://signalcaptchas.org/registration/generate.html
2. Solve the captcha, copy the `captcha=TOKEN_VALUE` from the URL
3. Retry: `~/signal-cli/.../bin/signal-cli -a +15551234567 register --captcha YOUR_TOKEN`

Complete registration:
```bash
~/signal-cli/signal-cli-${VERSION}/bin/signal-cli verify +15551234567
```

### Test

```bash
~/signal-cli/signal-cli-${VERSION}/bin/signal-cli -u +15551234567 send -m "Hello from signal-cli!" +15559876543
```

### Signal Pitfalls

- The `-a/--account` flag is a GLOBAL argument and must appear BEFORE the subcommand (register, verify, link, send), not after it
- During linking, do NOT specify an account: `signal-cli link` alone (not `signal-cli -a +NUMBER link`)

---

## Telegram (Bot API)

Create a Telegram bot via @BotFather and use the Bot API to send/receive messages.

### Prerequisites

- A Telegram account (mobile app or web.telegram.org)
- Ability to chat with @BotFather
- `curl` and `jq` for API testing

### Create the Bot

1. Open Telegram, search for `@BotFather`, send `/newbot`
2. Provide a display name (e.g., `My Test Bot`)
3. Provide a username ending in `bot` (e.g., `my_test_bot`)
4. Save the token BotFather returns (format: `123456789:AAHdqTcvCH1...`)
   > Treat the token like a password. Anyone with it can control your bot.

### Verify the Token

```bash
curl -s "https://api.telegram.org/bot<TOKEN>/getMe" | jq
```

Expected: `{"ok": true, "result": {"is_bot": true, "username": "my_test_bot", ...}}`

### Send a Message

You need the recipient's `chat_id`. Get it by having them send a message to the bot, then:

```bash
curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates" | jq
```

Extract `message.chat.id` from the response, then:

```bash
curl -s -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
     -d chat_id=<CHAT_ID> \
     -d text="Hello from Hermes!"
```

### BotFather Management Commands

- `/token` — Generate new token (invalidates old one)
- `/revoke` — Revoke current token (use if compromised)
- `/setname` — Change display name
- `/setdescription` — Set short description
- `/setabouttext` — Set "about" info
- `/setuserpic` — Upload profile picture
- `/setcommands` — Define bot commands shown in Telegram menu
- `/deletebot` — Delete bot and revoke token

### Hermes Integration

To have the bot act as an interface to Hermes Agent, forward incoming messages to Hermes and send back responses. Two approaches:

1. **Hermes Skills**: Create a skill that polls `getUpdates`, calls `delegate_task` for each new message, and sends the response via `sendMessage`
2. **External Script + Hermes CLI**: A polling script that shells out to the `hermes` CLI for each message

### Telegram Pitfalls

- **Chat ID not found**: The bot must be started by the user (they sent `/start` or any message) before you can get updates
- **Rate limits**: Stay below 30 messages per second
- **HTTPS required**: All API calls must go to `api.telegram.org` over HTTPS
- **Token leakage**: If token is exposed, revoke immediately via BotFather `/revoke` or `/token`
- **Privacy mode**: May hide group messages unless the bot is mentioned or a command is used

---

## Verification Checklist

- [ ] Platform CLI/tools installed and in PATH
- [ ] Authentication/linking successful
- [ ] Account/device listing confirms the link
- [ ] Test message sent and received

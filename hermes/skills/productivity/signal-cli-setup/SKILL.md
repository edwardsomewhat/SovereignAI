---
name: signal-cli-setup
description: Install and configure signal-cli for linking to an existing Signal account or registering a new number.
category: productivity
---

# Signal CLI Setup

This skill covers installing Signal CLI (a command-line interface for Signal) on Ubuntu/Debian systems and linking it to an existing Signal account (via QR code) or registering a new phone number.

## Prerequisites

- A Linux system with `sudo` access (Ubuntu/Debian used in examples).
- A smartphone with Signal installed (for linking) OR a phone number capable of receiving SMS/voice calls (for new registration).
- Java runtime (signal-cli requires Java 17+; we use OpenJDK 25 in the example, but any recent LTS works).

## Installation Steps

### 1. Install Java

Signal CLI is a Java application. Install a recent OpenJDK (e.g., 21 or 25):

```bash
sudo apt update
sudo apt install -y openjdk-25-jre-headless   # or openjdk-21-jre-headless
```

Verify installation:

```bash
java -version
# Should show openjdk version "25.0.3" or similar
```

### 2. Download and Extract Signal CLI

Choose a directory for installation (we use `~/signal-cli`):

```bash
mkdir -p ~/signal-cli
cd ~/signal-cli

# Fetch the latest release version from https://github.com/AsamK/signal-cli/releases
# Here we use v0.14.3 as an example; replace with the latest.
VERSION="0.14.3"
curl -L -O https://github.com/AsamK/signal-cli/releases/download/v${VERSION}/signal-cli-${VERSION}.tar.gz

# Extract (use --no-same-owner --no-same-permissions to avoid harmless permission warnings)
tar --no-same-owner --no-same-permissions -xzf signal-cli-${VERSION}.tar.gz
```

After extraction, you’ll have `~/signal-cli/signal-cli-${VERSION}/` with `bin/signal-cli`.

### 3. Link to an Existing Signal Account (Recommended)

If you already use Signal on your phone, link this device:

```bash
~/signal-cli/signal-cli-${VERSION}/bin/signal-cli link
```

The command outputs a URL (and implicitly a QR code) like:

```
sgnl://linkdevice?uuid=...&pub_key=...
```

**On your phone:**
1. Open Signal → Settings → Linked Devices → Link New Device
2. Scan the QR code (or copy the URL into a QR scanner app).
3. Wait for the linking to complete (the terminal command will finish when done).

### 4. Verify the Link

After linking, list your accounts and devices:

```bash
~/signal-cli/signal-cli-${VERSION}/bin/signal-cli listAccounts
~/signal-cli/signal-cli-${VERSION}/bin/signal-cli listDevices
```

You should see your phone number and the newly listed device.

### 5. (Optional) Register a New Phone Number

If you do not have an existing Signal account, you can register a new one:

```bash
# Replace +15551234567 with your phone number in E.164 format
# Note: The -a/--account flag is GLOBAL and must come BEFORE the subcommand
~/signal-cli/signal-cli-${VERSION}/bin/signal-cli -a +15551234567 register
```

You will receive an SMS or voice call with a verification code. Complete registration with:

```bash
~/signal-cli/signal-cli-${VERSION}/bin/signal-cli verify +15551234567
```

> **Note**: During registration, you may encounter a "Captcha required" error. If so:
> 1. Visit https://signalcaptchas.org/registration/generate.html in a browser
> 2. Solve the captcha puzzle
> 3. Right-click the "Open Signal" link and copy the link address
> 4. Extract the token from `captcha=TOKEN_VALUE` in the URL
> 5. Retry registration with: `~/signal-cli/signal-cli-${VERSION}/bin/signal-cli -a +15551234567 register --captcha YOUR_TOKEN_HERE`
> 
> You can also use voice verification by adding the `-v` flag before `register`:
> `~/signal-cli/signal-cli-${VERSION}/bin/signal-cli -a +15551234567 register -v`
> 
> **Important**: The `-a/--account` flag is a GLOBAL argument and must appear BEFORE the subcommand (register, verify, link, etc.), not after it.
## Testing

Send a test message to yourself or a contact (replace numbers with your own and the recipient’s):

```bash
~/signal-cli/signal-cli-${VERSION}/bin/signal-cli -u +15551234567 send -m "Hello from signal-cli!" +15559876543
```

{'in': 'You cannot specify a account (phone number) when linking\n```\nUse `signal-cli link` alone', 'GitHub': 'https://github.com/AsamK/signal-cli\n- Release notes: Check the `CHANGELOG.md` in each release for version-specific notes.\n- Session-specific notes and troubleshooting: See `references/session-2026-05-12-signal-setup.md` for detailed environment info'}
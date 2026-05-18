# Signal CLI Setup Session Notes - 2026-05-12

## Environment
- OS: Linux (Ubuntu-based, likely 24.04 or similar)
- User: fated
- Initial Java: OpenJDK 17 (insufficient for signal-cli v0.14.3)
- Final Java: OpenJDK 25.0.3-ea (required for signal-cli v0.14.3)

## Key Learnings & Fixes

### 1. Java Version Requirement
Signal CLI v0.14.3 requires Java with class file version 69.0 (Java 25).
- Error: `UnsupportedClassVersionError: org/asamk/signal/Main has been compiled by a more recent version of the Java Runtime (class file version 69.0), this version of the Java Runtime only recognizes class file versions up to 65.0`
- Fix: Install OpenJDK 25
  ```bash
  sudo apt install -y openjdk-25-jre-headless
  ```

### 2. Signal CLI Command Syntax
Global flags like `-a/--account` MUST come BEFORE the subcommand.
- Incorrect: `signal-cli register -a +1234567890`
- Correct: `signal-cli -a +1234567890 register`
- This applies to all subcommands: register, verify, link, send, etc.

### 3. Captcha Handling During Registration
When registering a new number, Signal often requires captcha solving:
- Error: `Captcha required for verification, use --captcha CAPTCHA`
- Solution process:
  1. Visit https://signalcaptchas.org/registration/generate.html
  2. Solve the captcha puzzle
  3. Right-click the "Open Signal" link and copy the link address
  4. Extract token from `captcha=TOKEN_VALUE` in the URL
  5. Use with: `signal-cli -a +1234567890 register --captcha YOUR_TOKEN`
- Alternative: Add `-v` flag for voice verification (may still require captcha)

### 4. Linking Process
The `link` command outputs a `sgnl://linkdevice?...` URL that serves as both:
- A link URL for QR code scanners
- Contains embedded QR code data
- Can be rendered as ASCII QR using `qrencode` tool

### 5. Working Command Sequence
```bash
# Install Java 25
sudo apt update
sudo apt install -y openjdk-25-jre-headless

# Install signal-cli
mkdir -p ~/signal-cli
cd ~/signal-cli
curl -L -O https://github.com/AsamK/signal-cli/releases/download/v0.14.3/signal-cli-0.14.3.tar.gz
tar --no-same-owner --no-same-permissions -xzf signal-cli-0.14.3.tar.gz

# Link to existing Signal account (recommended)
~/signal-cli/signal-cli-0.14.3/bin/signal-cli link
# Scan QR code with phone: Signal → Settings → Linked Devices → Link New Device

# OR register new number (if no existing Signal)
~/signal-cli/signal-cli-0.14.3/bin/signal-cli -a +13094898785 register --captcha YOUR_TOKEN
~/signal-cli/signal-cli-0.14.3/bin/signal-cli verify +13094898785 CODE_RECEIVED

# Verify setup
~/signal-cli/signal-cli-0.14.3/bin/signal-cli listAccounts
~/signal-cli/signal-cli-0.14.3/bin/signal-cli listDevices
```

## Pitfalls Encountered
1. **Java version mismatch** - Required upgrading from OpenJDK 17 to 25
2. **Command syntax confusion** - Global flags placement is critical
3. **Captcha requirement** - New registrations often require manual captcha solving
4. **Tar extraction warnings** - Harmless "Cannot utime" errors can be silenced with `--no-same-owner --no-same-permissions`
5. **Java native access warnings** - When running signal-cli, warnings about restricted methods appear:
   ```
   WARNING: A restricted method in java.lang.System has been called
   WARNING: java.lang.System::load has been called by org.signal.libsignal.internal.Native in an unnamed module (file:/.../libsignal-client-*.jar)
   WARNING: Use --enable-native-access=ALL-UNNAMED to avoid a warning for callers in this module
   ```
   These warnings do not affect functionality but can be silenced by setting:
   ```bash
   export JAVA_TOOL_OPTIONS="--enable-native-access=ALL-UNNAMED"
   ```
   or by adding the flag directly to the java command:
   ```bash
   java --enable-native-access=ALL-UNNAMED -jar ...
   ```
6. **Link command timeout** - The `link` command will wait indefinitely for a device to scan the QR code. If you need to abort, press `Ctrl+C`. The command does not accept an account flag (`-u`/`--account`); attempting to do so yields the error:
   ```
   You cannot specify a account (phone number) when linking
   ```
   Use `signal-cli link` alone, then scan the QR code with your phone.

## Verification Steps
After linking/registering:
- `listAccounts` should show your phone number
- `listDevices` should show your linked device(s)
- Test messaging: `signal-cli -u +1234567890 send -m \"Test\" +0987654321`

## References Used
- Signal CLI GitHub: https://github.com/AsamK/signal-cli
- Captcha service: https://signalcaptchas.org/
- OpenJDK packages: Ubuntu repositories
# Playwright on Ubuntu 26.04 (Resolute Raccoon)

## The problem

Playwright 1.57.0+ detects Ubuntu 26.04 and refuses to install Chromium:

```
Failed to install browsers
Error: ERROR: Playwright does not support chromium on ubuntu26.04-x64
```

## Root cause

The detected host platform is `ubuntu26.04-x86_64`, which maps to:
```
{ hostPlatform: "ubuntu" + distroInfo.version + archSuffix, isOfficiallySupportedPlatform: false }
```
(source: playwright/driver/package/lib/server/utils/hostPlatform.js)

Playwright officially supports: 18.04, 20.04, 22.04, 24.04. Version 26.04 falls through to the unsupported path, and the install script refuses to download browsers for unsupported platforms.

## The fix

**Pin Playwright to version 1.49.0** — this version's browser downloader doesn't perform this platform check:

```bash
uv pip install 'playwright==1.49.0' --python ~/.hermes/hermes-agent/venv/bin/python3
~/.hermes/hermes-agent/venv/bin/python3 -m playwright install chromium
```

## What gets installed

| Artifact | Size | Location |
|----------|------|----------|
| Chromium 131.0.6778.33 | 161.3 MB | ~/.cache/ms-playwright/chromium-1148/ |
| Chromium Headless Shell | 100.9 MB | ~/.cache/ms-playwright/chromium_headless_shell-1148/ |
| FFMPEG | 2.3 MB | ~/.cache/ms-playwright/ffmpeg-1010/ |

## When to remove the pin

When Playwright publishes upstream support for Ubuntu 26.04 (check their releases at https://github.com/microsoft/playwright/releases), upgrade:

```bash
uv pip install --upgrade playwright --python ~/.hermes/hermes-agent/venv/bin/python3
~/.hermes/hermes-agent/venv/bin/python3 -m playwright install chromium
```

---
name: tailscale-mcp
description: "Set up the Tailscale MCP server on a Hermes node — provides 8 tools for tailnet management: status, node details, SSH, file send/receive, ping, manage, and REST API access."
version: 1.0.0
author: Hermes Agent + Nick Schweska
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [tailscale, mcp, networking, tailnet, ssh, file-sharing]
---

# Tailscale MCP Server

Installs an MCP server that wraps Tailscale CLI and REST API into 8 tools accessible to Hermes. Enables programmatic tailnet management — list nodes, SSH to peers, transfer files, ping, and more — all from within agent conversations.

## Quick Setup

```bash
# 1. Ensure Python MCP SDK is installed in Hermes venv
~/.hermes/hermes-agent/venv/bin/python -m ensurepip
~/.hermes/hermes-agent/venv/bin/pip3 install mcp

# 2. Create the MCP server directory and copy the script
mkdir -p ~/.hermes/mcp-servers/tailscale-mcp
# Copy server.py from the SovereignAI repo or from another Hermes node

# 3. Register with Hermes
echo "y" | hermes mcp add tailscale \
  --command ~/.hermes/hermes-agent/venv/bin/python \
  --args ~/.hermes/mcp-servers/tailscale-mcp/server.py

# 4. Start a new session (/reset) to use the tools
```

## Tools Provided

| Tool | Description |
|------|-------------|
| `tailscale_status` | Full tailnet map (online/offline, IPs, OS, users) |
| `tailscale_node` | Detailed info on a specific node by hostname or IP |
| `tailscale_ping` | Connectivity check and latency test |
| `tailscale_ssh` | Run commands on any tailnet node (Tailscale SSH) |
| `tailscale_file_send` | Push files to any node via Taildrop |
| `tailscale_file_receive` | List or download incoming Taildrop files |
| `tailscale_manage` | Status, netcheck, whois, version, IP |
| `tailscale_api` | Call official Tailscale REST API (needs TS_API_KEY) |

## Requirements

- Tailscale installed and authenticated on the node
- `python-mcp` package in Hermes venv
- `curl` for local API queries
- Taildrop: `sudo tailscale set --operator=$USER` for file operations without sudo
- REST API: `TAILSCALE_API_KEY` or `TS_API_KEY` env var in `~/.hermes/.env`

## Server Location

The canonical server script lives at `~/.hermes/mcp-servers/tailscale-mcp/server.py`. It's also stored in the SovereignAI git repo under `hermes/mcp-servers/tailscale-mcp/` for cross-node sync.

## Pitfalls

### `tailscale_ssh` host key verification failure

Both the MCP `tailscale_ssh` tool and `tailscale ssh <host>` CLI can fail with:

```
No ED25519 host key is known for <host>.tail01322f.ts.net.
Host key verification failed.
```

`ssh-keyscan` on the Tailscale FQDN may return nothing because the FQDN resolves via Tailscale DNS but the SSH daemon may only bind to the raw IP.

**Fallback — `sshpass` + Tailscale IP (always works):**

```bash
sshpass -p '<password>' ssh -o StrictHostKeyChecking=accept-new <user>@<tailscale-ip> "<command>"
```

Use the raw Tailscale IPv4 (e.g. `100.84.226.78`) instead of the FQDN. This bypasses the MCP tool entirely in favor of direct SSH with password auth — useful when the node doesn't have Tailscale SSH enabled or key-based auth configured.

## Verification

```bash
# Check MCP server is registered
hermes mcp list

# Should show 'tailscale' with 8 tools enabled
```

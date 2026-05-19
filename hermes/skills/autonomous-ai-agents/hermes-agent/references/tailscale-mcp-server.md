# Tailscale MCP Server

## Overview

A custom MCP server that wraps the `tailscale` CLI and local API to expose
tailnet management tools to Hermes. Built because no standard Tailscale MCP
server exists in the MCP registry.

**Location:** `~/.hermes/mcp-servers/tailscale-mcp/server.py`

## Tools Provided (8)

| Tool | Description |
|------|-------------|
| `tailscale_status` | Full tailnet map — online/offline nodes, IPs, OS |
| `tailscale_node` | Detailed info on a specific node (hostname/IP lookup) |
| `tailscale_ssh` | Run commands on any tailnet node via Tailscale SSH |
| `tailscale_file_send` | Push files to any node via Taildrop |
| `tailscale_file_receive` | Check/download Taildrop files on this node |
| `tailscale_ping` | Ping a tailnet node for connectivity/latency |
| `tailscale_manage` | Status, netcheck, whois, IP, version queries |
| `tailscale_api` | Official Tailscale REST API (needs TAILSCALE_API_KEY) |

## Installation

```bash
# Install MCP Python SDK
/home/fated/.hermes/hermes-agent/venv/bin/python -m ensurepip
/home/fated/.hermes/hermes-agent/venv/bin/pip3 install mcp

# Copy the server script
mkdir -p ~/.hermes/mcp-servers/tailscale-mcp
# ... copy server.py to that directory ...

# Register with Hermes
echo "y" | hermes mcp add tailscale \
  --command /home/fated/.hermes/hermes-agent/venv/bin/python \
  --args /home/fated/.hermes/mcp-servers/tailscale-mcp/server.py
```

## Prerequisites

- `tailscale` CLI installed and authenticated
- Tailscale SSH enabled on target nodes for `tailscale_ssh`
- Taildrop operator permissions for file tools:
  ```bash
  sudo tailscale set --operator=$USER
  ```
- For `tailscale_api` (REST API): set `TAILSCALE_API_KEY` in `~/.hermes/.env`
  Get a key at https://login.tailscale.com/admin/settings/keys

## Architecture

The server uses the official `mcp` Python SDK. Communication is JSON-RPC over stdio.
It wraps three data sources:

1. **Tailscale CLI** (`subprocess.run(["tailscale", ...])`) — for status, ping, whois, file operations, SSH
2. **Local API** (`curl --unix-socket /var/run/tailscale/tailscaled.sock`) — for structured node data
3. **REST API** (`curl https://api.tailscale.com`) — for tailnet management (ACLs, DNS, device approval)

## Multi-Node Deployment

The server is self-contained — copy `server.py` to any Hermes node on the tailnet,
run the install steps above, and register. Each node gets its own view of the
tailnet through its local `tailscale` daemon.

## Known Quirks

- The local API Unix socket requires read access. May need sudo if permissions
  are restricted.
- `tailscale file get` without operator permissions returns "Access denied."
  The server auto-retries with sudo using the stored password.
- The REST API tool requires a separate API key — local CLI operations don't
  need it.

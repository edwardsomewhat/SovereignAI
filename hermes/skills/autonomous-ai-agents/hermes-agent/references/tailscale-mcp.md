# Tailscale MCP Server

Custom MCP server at `~/.hermes/mcp-servers/tailscale-mcp/server.py` that exposes 8 tools for tailnet management. Registered as `tailscale` in Hermes MCP config.

## Tools

| Tool | Description |
|------|-------------|
| `tailscale_status` | Full tailnet map — online/offline nodes, IPs, OS |
| `tailscale_node` | Details on a specific node by hostname or IP |
| `tailscale_ssh` | SSH to any tailnet node, run a command |
| `tailscale_file_send` | Taildrop files to any node |
| `tailscale_file_receive` | List/download received Taildrop files |
| `tailscale_ping` | Ping a node for connectivity check |
| `tailscale_manage` | Status, netcheck, whois, version, ip |
| `tailscale_api` | Official Tailscale REST API (needs API key from admin console) |

## Installation

```bash
# Copy server.py to target
mkdir -p ~/.hermes/mcp-servers/tailscale-mcp
cp server.py ~/.hermes/mcp-servers/tailscale-mcp/
chmod +x ~/.hermes/mcp-servers/tailscale-mcp/server.py

# Install MCP SDK in Hermes venv
~/.hermes/hermes-agent/venv/bin/python -m ensurepip
~/.hermes/hermes-agent/venv/bin/pip3 install mcp

# Register with Hermes
echo "y" | hermes mcp add tailscale \
  --command ~/.hermes/hermes-agent/venv/bin/python \
  --args ~/.hermes/mcp-servers/tailscale-mcp/server.py
```

## Requirements

- Tailscale installed and authenticated on the host
- MCP Python SDK (`pip install mcp`)
- For `tailscale_file_receive`: operator permissions (`sudo tailscale set --operator=$USER`)
- For `tailscale_api`: API key from https://login.tailscale.com/admin/settings/keys

## Sudo for Taildrop

```bash
echo '<password>' | sudo -S tailscale set --operator=$USER
```

## Pitfalls

- **`tailscale file get .` access denied without operator**: Set operator permissions once via sudo.
- **DERP relay instead of direct connection**: Some nodes may connect via relay — SSH still works but with higher latency.
- **API key for tailscale_api tool**: Set `TAILSCALE_API_KEY` or `TS_API_KEY` in `.env`.

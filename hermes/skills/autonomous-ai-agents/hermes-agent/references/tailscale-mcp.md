# Tailscale MCP Server

An MCP server at `~/.hermes/mcp-servers/tailscale-mcp/server.py` that exposes 8 Tailscale tools to Hermes.

## Tools

| Tool | Description |
|------|-------------|
| `tailscale_status` | Full tailnet map (online/offline/IPs/OS) |
| `tailscale_node` | Details on a specific node |
| `tailscale_ssh` | Run commands on any tailnet node |
| `tailscale_file_send` | Push files to any node (Taildrop) |
| `tailscale_file_receive` | Check/download Taildrop files |
| `tailscale_ping` | Connectivity check |
| `tailscale_manage` | Status, netcheck, whois, version |
| `tailscale_api` | Official Tailscale REST API (needs API key) |

## Register

```bash
# Install MCP SDK
/home/fated/.hermes/hermes-agent/venv/bin/pip3 install mcp

# Register server
echo "y" | hermes mcp add tailscale \
  --command /home/fated/.hermes/hermes-agent/venv/bin/python \
  --args /home/fated/.hermes/mcp-servers/tailscale-mcp/server.py
```

Tools available after `/reset` or new session.

## Taildrop Setup

```bash
# Set operator to avoid sudo for file operations
sudo tailscale set --operator=$USER

# Send files
tailscale file cp <file> <target-node>:

# Receive files
tailscale file get <target-dir>
```

## Tailscale API Key

Get from https://login.tailscale.com/admin/settings/keys for the `tailscale_api` tool. Set as `TAILSCALE_API_KEY` in `~/.hermes/.env`.

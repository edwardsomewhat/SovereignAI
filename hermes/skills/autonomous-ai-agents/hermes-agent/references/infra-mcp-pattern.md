# Infrastructure MCP Server Pattern

Pattern for building MCP servers that wrap system CLI tools (Tailscale, Docker, kubectl, etc.) into Hermes-callable tools.

## Why MCP over built-in tools

- MCP servers live outside Hermes — no PR needed, no restart to iterate
- Tools auto-discover on registration (`hermes mcp add`)
- Same server works across profiles and sessions
- The CLI tool's output format is the API contract — wrap, don't re-implement

## Architecture

```
Hermes → MCP stdio transport → Python server → subprocess → CLI tool
                                                         ↘ Unix socket / local API
```

## Boilerplate (worked example: Tailscale)

See `~/.hermes/mcp-servers/tailscale-mcp/server.py` for the full Tailscale server. Key patterns:

### Tool shapes

| Pattern | Tool name | Inputs | Implementation |
|---------|-----------|--------|---------------|
| List/status all resources | `tailscale_status` | `json_output?` | Local API + CLI fallback |
| Get one resource detail | `tailscale_node` | `hostname` | Search peers dict + whois |
| Execute on remote | `tailscale_ssh` | `hostname, command, timeout?` | `subprocess.run(["tailscale", "ssh", ...])` |
| File transfer | `tailscale_file_send` | `target, file_path` | `tailscale file cp` + sudo fallback |
| File receive | `tailscale_file_receive` | `action, target_dir?` | `tailscale file get` |
| Connectivity check | `tailscale_ping` | `hostname, count?` | `tailscale ping -c N` |
| Manage self | `tailscale_manage` | `action, target?` | Multiplex to status/netcheck/whois/ip/version |
| REST API proxy | `tailscale_api` | `method, path, body?` | `curl` to api.tailscale.com |

### Sudo pattern

When CLI commands need root (Taildrop, operator mode), try without sudo first, fall back on failure:

```python
result = subprocess.run(["tailscale", "file", "cp", ...], ...)
if result.returncode != 0:
    result = subprocess.run(
        ["sudo", "-S", "tailscale", "file", "cp", ...],
        input="PASSWORD\n", ...  # from memory
    )
```

### Venv setup (Hermes stripped venv)

```bash
~/.hermes/hermes-agent/venv/bin/python -m ensurepip
~/.hermes/hermes-agent/venv/bin/pip3 install mcp
```

### Registration

```bash
hermes mcp add <name> --command ~/.hermes/hermes-agent/venv/bin/python --args /path/to/server.py
# Pipe 'y' to auto-enable all tools:
echo "y" | hermes mcp add <name> --command ... --args ...
```

Tools are available after `/reset`.

## Adapting to other CLI tools

1. Identify the resource types (nodes, containers, pods, etc.)
2. Create one tool per CRUD verb + a status/health tool
3. For shell commands: `subprocess.run(cmd, capture_output=True, text=True, timeout=30)`
4. For local APIs: `curl --unix-socket /path/to/socket http://...`
5. For REST APIs: `curl -s -H "Authorization: Bearer $TOKEN" https://api.example.com/...`
6. Always include a `timeout` parameter on commands that can hang
7. Return JSON — the agent parses structured output better than raw text

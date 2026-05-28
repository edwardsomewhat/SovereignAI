---
name: tailscale-mcp
description: "Set up the Tailscale MCP server on a Hermes node — provides 8 tools for tailnet management: status, node details, SSH, file send/receive, ping, manage, and REST API access."
version: 1.1.0
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

## ACL Editing Workflow

The `tailscale_api` tool calls the Tailscale REST API. Common ACL operations:

### Read the current ACL
```bash
curl -s "https://api.tailscale.com/api/v2/tailnet/<tailnet>.ts.net/acl" \
  -u "$TAILSCALE_API_KEY:" -o acl.json
```

### Pitfall: HuJSON (JSON with comments)

Tailscale's ACL format is **HuJSON** — JSON with `//` comments and trailing commas.
Python's `json.load()` will choke. Workarounds:

**Simple changes (one field):** Use `sed`:
```bash
sed -i 's/"action": "check"/"action": "accept"/' acl.json
```

**Complex changes (multiple rules):** Strip comments before parsing, or use
`python3` with a pre-processor. The safest pattern is `sed` for targeted
replacements — avoids corrupting the comment structure that Tailscale expects back.

### Push the modified ACL
```bash
curl -s -w "\nHTTP:%{http_code}" -X POST \
  "https://api.tailscale.com/api/v2/tailnet/<tailnet>.ts.net/acl" \
  -u "$TAILSCALE_API_KEY:" \
  -H "Content-Type: application/json" \
  --data-binary @acl.json
```

Success returns HTTP 200 with the new ACL echoed back. ACL changes propagate
to all nodes within seconds.

### Common ACL Fix: SSH "check" → "accept"

When `tailscale ssh` returns browser re-auth prompts or "failed to look up local
user", the SSH ACL is in `"check"` mode. Change to `"accept"` for frictionless
keyless SSH:

```json
// In the "ssh" array, change:
{"action": "check", "src": ["autogroup:member"], ...}
// to:
{"action": "accept", "src": ["autogroup:member"], ...}
```

With `"accept"`, Tailscale SSH creates users on-the-fly — no local account needed
on target machines, no browser re-auth prompts.

### API Key Setup

The `tailscale_api` tool reads `TAILSCALE_API_KEY` or `TS_API_KEY` from the
environment. Add to `~/.hermes/.env`:

```bash
echo 'TAILSCALE_API_KEY=tskey-api-...' >> ~/.hermes/.env
```

**Important:** The MCP server process reads the env var at startup. If you add
the key mid-session, the MCP server won't see it until restarted. Use `curl`
directly (as shown above) for immediate ACL operations, or restart the MCP
server with `hermes mcp test tailscale` to pick up the new env var.

## Verification

```bash
# Check MCP server is registered
hermes mcp list

# Should show 'tailscale' with 8 tools enabled
```

## Pitfalls

### `tailscale ssh` ED25519 Host Key Mismatch

The `tailscale ssh` wrapper validates ED25519 host keys from the Tailscale coordination server, NOT standard SSH host keys from port 22. If you see:

```
No ED25519 host key is known for <host>.tail01322f.ts.net. and you have requested strict checking.
Host key verification failed.
```

**Root cause**: Tailscale SSH (keyless auth) must be enabled on the TARGET node with `tailscale up --ssh`. Without it, the `tailscale ssh` wrapper fails because the coordination server has no ED25519 key to advertise. Regular `ssh` falls through to password auth on port 22 — this is NOT the same as Tailscale SSH failing, it's Tailscale SSH not being set up.

**Diagnosis steps**:
1. `ssh-keyscan -H <host>.tail01322f.ts.net` — gets ecdsa/rsa from port 22 (useless for `tailscale ssh` which wants ED25519 from the coordination server)
2. `ssh-keygen -F <host>.tail01322f.ts.net` — check what's in known_hosts
3. The MCP `tailscale_ssh` tool uses its own known_hosts, not `~/.ssh/known_hosts` — host keys added via `ssh-keyscan` to the user file won't help the MCP tool
4. The MCP tool resolves hostnames to MagicDNS internally (e.g., `omega` → `omega.tail01322f.ts.net`)

**Fix**: On each target node, run `tailscale up --ssh` once. This advertises the ED25519 key via the coordination server and `tailscale ssh` works.

**`tailscale ssh` wrapper limitations**:
- Does NOT pass flags through to system `ssh` (no `-v`, no `-o`, no `-hostkey-check`)
- Always does strict host key checking against coordination server keys
- Resolves MagicDNS internally even if `--accept-dns=false` on the node

### MCP Server Env Var Staleness

When you add or change an env var in `~/.hermes/.env` that the MCP server needs (like `TAILSCALE_API_KEY`), the running MCP server process won't pick it up — it was started with the old environment. The `tailscale_api` tool will report "No Tailscale API key found" even though `.env` has it.

**Fix:** restart or reload the MCP server. The fastest way is a new session (`/reset` in chat). If you're mid-session and need the API immediately, fall back to curl with `export $(grep -v '^#' ~/.hermes/.env | grep VARNAME | xargs)` to pull the var into the current shell before each curl call.

### Tailscale ACL Format (HuJSON)

Tailscale ACLs use **HuJSON** — JSON with `//` and `/* */` comments. Python's `json.load()` silently fails (returns empty, no error on some versions) because the leading `//` comments are not valid JSON tokens.

**Workaround for read-only:** `python3 -c "import json,re; json.loads(re.sub(r'//.*|/\*[\s\S]*?\*/', '', raw))"` — but this is fragile with nested string contents.

**Preferred approach for edits:** use `sed` for targeted `"check"` → `"accept"` swaps instead of a JSON round-trip. The ACL schema is stable enough that string replacement on known keys is safer than comment-stripping. Full recipe in `references/acl-editing.md`.

### SSH ACL: "check" vs "accept"

The SSH section of the ACL controls how Tailscale SSH authenticates:

| Mode | Behavior |
|------|----------|
| `"check"` | Requires local user to exist on target machine + periodic browser re-auth |
| `"accept"` | Tailscale handles auth entirely — creates user on-the-fly, no re-auth |

Symptoms of `"check"` mode:
- `ssh edward@host` → `"failed to look up local user 'edward'"` (user doesn't exist locally)
- `ssh root@host` → `"Tailscale SSH requires an additional check. Visit: https://login.tailscale.com/a/..."` (triggers browser re-auth)

**Fix:** change the member rule's action from `"check"` to `"accept"`. Common pattern after fix:
```json
{
    "action": "accept",
    "src": ["autogroup:admin"],
    "dst": ["autogroup:self"],
    "users": ["root"]
},
{
    "action": "accept",  // ← was "check", now frictionless
    "src": ["autogroup:member"],
    "dst": ["autogroup:self"],
    "users": ["autogroup:nonroot", "root"]
}
```
See `references/acl-editing.md` for the full curl/sed recipe.

## Multi-Node Inspection Without SSH

When SSH is blocked, these HTTP APIs work across the Tailscale mesh from any node:

### Ollama HTTP API (port 11434)
```bash
# Check version (also reveals llama.cpp version underneath)
curl -s http://<tailscale-ip>:11434/api/version

# List all models with sizes
curl -s http://<tailscale-ip>:11434/api/tags | python3 -c "
import sys,json; d=json.load(sys.stdin)
print('Version:', d.get('version','?'))
for m in d.get('models',[]): print(f'  {m[\"name\"]:40s} {m[\"size\"]/1e9:.1f}GB')
"
```

### Dockhand API (port 3001)
```bash
# List all registered compute environments
curl -s http://<dockhand-host>:3001/api/environments | python3 -c "
import sys,json
for e in json.load(sys.stdin):
    print(f'  ID:{e[\"id\"]} {e[\"name\"]:20s} type={e[\"connectionType\"]}')
"

# List containers on an environment (uses lowercase field names: id, name, state, status)
curl -s "http://<dockhand-host>:3001/api/containers?env=<id>" | python3 -c "
import sys,json
for c in json.load(sys.stdin):
    print(f'  [{c[\"id\"][:12]}] {c[\"name\"]:30s} {c[\"state\"]:10s} {c[\"status\"]}')
"
```

### Combined network discovery pattern
Use `tailscale_status` (MCP) for node list → Ollama API for model inventory → Dockhand API for container health. This gives full network visibility — node list, container states, Ollama models/versions — without a single SSH connection.

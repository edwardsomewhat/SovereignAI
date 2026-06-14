---
name: network-file-access
description: "Access files on remote machines in the local network or Tailscale tailnet — Windows (SMB), Linux (SSH/SFTP), file shares, and Tailscale MCP server setup. Use when the user provides a remote machine IP/hostname/password or file path on another machine."
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [networking, file-transfer, SMB, SSH, tailscale, Windows-access, remote-files, taildrop, tailscale-api, mcp]
    related_skills: [github-auth, obsidian]
---

# Network File Access

Access files on remote machines across the local network or Tailscale tailnet. Covers Windows (SMB), Linux (SSH/SFTP), Tailscale-specific access (Tailscale SSH, Taildrop, local daemon API), and generic file shares.

## Prerequisites

Before attempting any remote access, check what's available:

```bash
# Connectivity and identity information
```

Detection flow:

```bash
# Check remote machine reachability
ping -c 1 -W 2 <remote-ip> 2>&1 | head -5

# Check what access methods are available on THIS machine
which ssh sshpass smbclient mount.cifs 2>/dev/null || echo "available check"
python3 -c "import smbprotocol" 2>&1 || echo "smbprotocol not installed"

# Check common remote ports
for port in 22 445 3389 5985 5986; do
  timeout 2 bash -c "echo >/dev/tcp/<ip>/$port" 2>/dev/null && echo "Port $port open"
done
```

## Method 1: SMB — Windows Machine Access

Best for reaching Windows machines on a local network or Tailscale tailnet.

### Step 1: Connect and Authenticate

```bash
# Try SSH first (port 22)
sshpass -p '<password>' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 <user>@<ip> "hostname && whoami" 2>&1
```

If SSH is not available (port 22 closed, typical for Windows without OpenSSH Server), fall back to SMB:

### Step 2: SMB Authentication via smbprotocol

Install the Python library:

```bash
pip3 install --user --break-system-packages smbprotocol
```

Connect and authenticate:

```python
import uuid
from smbprotocol.connection import Connection, Dialects
from smbprotocol.session import Session

host = '<ip>'
username = '<user>'
password = '<password>'

conn = Connection(uuid.uuid4(), host, 445)
conn.connect(Dialects.SMB_3_1_1)

sess = Session(conn, username, password)
sess.connect()
```

### Step 3: Enumerate Available Shares

```python
# Try admin shares (require admin; often access denied for non-admin users)
shares_to_try = ['C$', 'D$', 'ADMIN$', 'IPC$', 'Users', 'Public', 'Documents']
for share in shares_to_try:
    from smbprotocol.tree import TreeConnect
    t = TreeConnect(sess, rf"\\{host}\{share}")
    try:
        t.connect()
        print(f"SHARE: {share}")
    except:
        pass
```

### Step 4: List and Read Files

```python
from smbprotocol.tree import TreeConnect
from smbprotocol.open import Open, FilePipePrinterAccessMask, ImpersonationLevel

tree = TreeConnect(sess, rf"\\{host}\C$")   # or another discovered share
tree.connect()

folder_path = r"\Users\user\OneDrive\Documents\TargetFolder"

o = Open(sess, tree, folder_path)
o.create(
    FilePipePrinterAccessMask.FILE_LIST_DIRECTORY,
    file_attributes=0,
    share_access=0x7,
    create_disposition=1,
    impersonation_level=ImpersonationLevel.Impersonation,
)
files = o.query_directory("*")
for f in files:
    name = f.get('file_name', '')
    name and name not in ('.', '..', 'desktop.ini'):
        size = f.get('end_of_file', 0)
        is_dir = f.get('file_attributes', 0) & 0x10
        typ = "<DIR>" if is_dir else f"{size:,} bytes"
        print(f"  {name} - {typ}")
o.close()
```

### Step 5: Read File Contents

To read a file's contents over SMB, open it with `FILE_READ_DATA` access and read the stream:

```python
from smbprotocol.open import Open, FilePipePrinterAccessMask
from smbprotocol.create_contexts import CreateContextName

o = Open(sess, tree, r"\Users\user\path\to\file.txt")
o.create(
    FilePipePrinterAccessMask.FILE_READ_DATA,
    file_attributes=0,
    share_access=0x7,
    create_disposition=1,  # FILE_OPEN
)
# Read the file
data = o.read(0, 65536)
content = data.decode('utf-16-le') if data else ""  # Windows often uses UTF-16
o.close()
```

## Method 2: Linux/SSH Access

### SSH with Password

```bash
sshpass -p '<password>' ssh -o StrictHostKeyChecking=no <user>@<ip> "<command>"
```

### SCP File Transfer

```bash
sshpass -p '<password>' scp -o StrictHostKeyChecking=no <user>@<ip>:"<remote-path>/<file>" <local-dest>/
```

### SFTP Directory Listing

```bash
sshpass -p '<password>' sftp -o StrictHostKeyChecking=no <user>@<ip> <<< "ls -la <remote-path>"
```

## Method 3: Tailscale Tailnet Access

For networks connected via Tailscale. All nodes are reachable by their Tailscale IP (100.x.y.z) regardless of physical location.

### Node Discovery

```bash
# Human-readable list
tailscale status

# JSON for programmatic use
tailscale status --json | python3 -c "
import sys, json
d = json.load(sys.stdin)
self_node = d.get('Self', {})
print(f\"This node: {self_node.get('HostName')} ({', '.join(self_node.get('TailscaleIPs', []))})\")
for k, v in d.get('Peer', {}).items():
    status = 'ONLINE' if v.get('Online') else 'offline'
    ips = ', '.join(v.get('TailscaleIPs', []))
    print(f'  {v.get(\"HostName\", k):20s} {v.get(\"OS\", \"?\"):8s} {status:7s} {ips}')
"
```

### Local Daemon API (read-only)

Tailscaled exposes a local API on a Unix socket. Useful for checking connectivity from within scripts:

```bash
# Status (same as tailscale status --json)
curl -s --unix-socket /var/run/tailscale/tailscaled.sock \
  http://local-tailscaled.sock/localapi/v0/status

# WhoIs (resolve IP to node info)
curl -s --unix-socket /var/run/tailscale/tailscaled.sock \
  "http://local-tailscaled.sock/localapi/v0/whois?ip=100.69.153.16"
```

Note: `execute_code` cannot access Unix sockets directly. Use `terminal()` to call curl and parse the JSON in the script.

### Tailscale SSH

If Tailscale SSH is enabled on the tailnet (check with `tailscale status --json` — look for `ssh` in capabilities), you can SSH to any node using its Tailscale IP **without** setting up SSH keys or passwords:

```bash
ssh <tailscale-ip> "hostname && whoami"
```

This works because Tailscale manages the SSH session. No password prompt. For file transfers:

```bash
scp <tailscale-ip>:/path/to/file ./local-dest/
```

### Taildrop (File Sharing)

Taildrop lets you send files between Tailscale nodes. Requires operator permissions on the receiving node:

```bash
# One-time setup on the receiving node (needs sudo)
sudo tailscale set --operator=$USER

# Send a file from any node to this one:
tailscale file cp /path/to/local/file <tailscale-ip>:

# Check for incoming files on the receiving node:
tailscale file get ~/Downloads/
```

Without operator permissions, `tailscale file get` returns "Access denied." The fix is the `--operator` command above.

## Method 4: Tailscale MCP Server

For programmatic tailnet management from within Hermes Agent conversations, you can install an MCP server that wraps the Tailscale CLI and local API into 8 discoverable tools. Once registered, the agent gains `mcp_tailscale_*` tools for status, SSH, file transfer, ping, and REST API access — no more raw `tailscale` CLI calls needed.

### Quick Setup

```bash
# 1. Ensure Python MCP SDK is installed in Hermes venv
~/.hermes/hermes-agent/venv/bin/python -m ensurepip
~/.hermes/hermes-agent/venv/bin/pip3 install mcp

# 2. Create the MCP server directory and copy server.py
mkdir -p ~/.hermes/mcp-servers/tailscale-mcp
# Copy scripts/server.py from this skill's scripts/ directory
cp ~/.hermes/skills/devops/network-file-access/scripts/server.py ~/.hermes/mcp-servers/tailscale-mcp/server.py

# 3. Register with Hermes
echo "y" | hermes mcp add tailscale \
  --command ~/.hermes/hermes-agent/venv/bin/python \
  --args ~/.hermes/mcp-servers/tailscale-mcp/server.py

# 4. Start a new session (/reset) to use the tools
```

### Tools Provided

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

### Requirements

- Tailscale installed and authenticated on the node
- `python-mcp` package in Hermes venv
- `curl` for local API queries
- Taildrop: `sudo tailscale set --operator=$USER` for file operations without sudo
- REST API: `TAILSCALE_API_KEY` or `TS_API_KEY` env var in `~/.hermes/.env`

### Verification

```bash
# Check MCP server is registered
hermes mcp list
# Should show 'tailscale' with 8 tools enabled
```

The server script is at `scripts/server.py` in this skill's directory. It wraps the same Tailscale CLI and local daemon API covered in Method 3 above into structured MCP tools.


## Reference files

- `references/smb-protocol-reference.md` — Detailed SMB protocol usage with smbprotocol library
- `references/agent-knowledge-transfer.md` — Pattern for sharing working knowledge with other Hermes agents on the tailnet

## Using Credentials

- The user may provide passwords in freeform text. Multiple options may be given; try them in order
- Passwords may contain special characters — wrap in single quotes for shell commands
- When using smbprotocol from Python, pass the password as a plain string
- Save discovered passwords and usernames for network hosts in memory so future sessions don't need to re-establish them

## Common Pitfalls

1. **Admin shares (C$, D$, ADMIN$) require administrator privileges on the target Windows machine.** Non-admin users get STATUS_ACCESS_DENIED. Check with the user or try alternative non-admin shares
2. **Windows machines often don't run SSH out of the box.** Port 22 timeout usually means OpenSSH Server is not installed. Fall back to SMB immediately rather than retrying SSH
3. **TTL in ping response reveals OS type.** TTL=128 → Windows, TTL=64 → Linux. Use this to decide SMB vs SSH approach
4. **Editing a fine-grained GitHub PAT regenerates the token.** If you get 401 / Bad credentials after the user said they edited permissions, ask for the new token value
5. **smbprotocol installed to user site-packages is not visible in execute_code sandbox.** Write SMB scripts to files and run them via `python3 /path/to/script.py` instead
6. **Tailscale local API requires Unix socket access.** The `execute_code` sandbox cannot access Unix sockets directly. Use `terminal()` to run curl and parse the JSON output separately
7. **Tailscale SSH host key verification failure.** `tailscale ssh <host>` can fail with "No ED25519 host key is known" if the FQDN resolves via Tailscale DNS but the SSH daemon only binds to the raw IP. Fallback: `sshpass -p '<password>' ssh -o StrictHostKeyChecking=accept-new <user>@<tailscale-ip> "<command>"` using the raw Tailscale IPv4 (e.g., `100.84.226.78`) instead of the FQDN

8. **Tailscale SSH "failed to look up local user".** `tailscale ssh <host>` fails with "failed to look up local user \"<username>\"" when the target node hasn't authorized that Tailscale user for SSH. This is a per-node ACL setting — not something you can fix mid-session. Fallback immediately to password-based SSH: `sshpass -p '<password>' ssh -o StrictHostKeyChecking=accept-new <user>@<tailscale-ip> "<command>"`.

9. **Taildrop unreliability.** `tailscale file cp` may report success but the file never appears in the target's Taildrop inbox, or `tailscale file get` returns nothing despite a successful send. This is a known intermittent issue. When delivering files to another agent/node, prefer `sshpass -p '<password>' scp` as the primary path. Use Taildrop only as a convenience when neither side has SSH credentials available.

## Verification Checklist

- [ ] Remote host is reachable (ping succeeds)
- [ ] SMB port 445 is open OR SSH port 22 is open
- [ ] Authentication succeeds (not "logon is invalid")
- [ ] At least one file share is accessible (not "access denied")
- [ ] Target folder path is confirmed to exist
- [ ] File contents can be read or transferred successfully

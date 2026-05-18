---
name: network-file-access
description: "Access files on remote machines in the local network or Tailscale tailnet — Windows (SMB), Linux (SSH/SFTP), and file shares. Use when the user provides a remote machine IP/hostname/password or file path on another machine."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [networking, file-transfer, SMB, SSH, tailscale, Windows-access, remote-files]
    related_skills: [github-auth, obsidian]
---

# Network File Access

Access files on remote machines across the local network or Tailscale tailnet. Covers Windows (SMB), Linux (SSH/SFTP), and generic file shares.

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

## Method 1: SMB: Windows Machine Access (SMB)

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

## Verification Checklist

- [ ] Remote host is reachable (ping succeeds)
- [ ] SMB port 445 is open OR SSH port 22 is open
- [ ] Authentication succeeds (not "logon is invalid")
- [ ] At least one file share is accessible (not "access denied")
- [ ] Target folder path is confirmed to exist
- [ ] File contents can be read or transferred successfully

---
name: tailscale-ssh-enable
description: "Enable Tailscale SSH on nodes for keyless agent access — fix the ED25519 host key verification failure and configure tailscale up --ssh."
---

# Tailscale SSH — Enable Keyless Access on All Nodes

When Hermes (or the MCP tailscale_ssh tool) fails with "No ED25519 host key is known for <host>.tail01322f.ts.net. and you have requested strict checking", the root cause is one or both of:

1. **Tailscale SSH not enabled** on the target node (`tailscale up --ssh` was never run)
2. **ED25519 host key not in known_hosts** on the source node

## Enable on Target Node (run ON the target)

```bash
# Enable Tailscale SSH (keyless auth via Tailscale coordination server)
sudo tailscale up --ssh

# Verify
tailscale status | grep -i ssh
```

## Seed Host Keys on Source Node (run ON Hermes/source)

```bash
# Get the MagicDNS name (check tailscale status on source: tailscale status)
# Example MagicDNS names from this network:
#   omega.tail01322f.ts.net
#   hq-ai.tail01322f.ts.net
#   nano-box.tail01322f.ts.net

# For each target:
ssh-keyscan -H <host>.tail01322f.ts.net >> ~/.ssh/known_hosts

# Verify ED25519 key was added:
ssh-keygen -F <host>.tail01322f.ts.net | grep ed25519
```

## Verify Access

```bash
tailscale ssh fated@<host> 'hostname && uptime'
```

## Fleet-Wide SSH Audit

Check which nodes have Tailscale SSH enabled across the entire tailnet:

```bash
tailscale status --json | python3 -c "
import json, sys
data = json.load(sys.stdin)
peers = data.get('Peer', {})
self = data.get('Self', {})
self_ssh = self.get('Hostinfo', {}).get('SSHEnabled', False)
print(f'SELF ({self.get(\"HostName\",\"?\")}): TS SSH = {self_ssh}')
print()
for ip, peer in sorted(peers.items()):
    name = peer.get('HostName', '?')
    online = peer.get('Online', False)
    ssh = peer.get('Hostinfo', {}).get('SSHEnabled', False)
    status = '🟢' if online else '⚫'
    ssh_str = 'SSH ✓' if ssh else 'SSH ✗'
    print(f'{status} {name:30s} {ssh_str}')
"
```

This parses the `Hostinfo.SSHEnabled` field for every node. A node showing
`SSH ✗` needs `sudo tailscale up --ssh` run on it. Note: the field reports
whether the Tailscale SSH daemon is running (can you SSH INTO it), not whether
the node can SSH out.

## Pitfalls

- `tailscale ssh` wrapper validates ED25519 keys against the Tailscale coordination server — regular `ssh-keyscan` by IP gets ecdsa/rsa, NOT the ED25519 key. Always scan by MagicDNS name, not IP.
- Each new node needs this done — it's not automatic.
- The `SSH_FLAGS` env var is overridden by `tailscale ssh`'s strict checking; you can't bypass it with `-o StrictHostKeyChecking=no`.
- If you get "Connection closed by UNKNOWN port 65535" or "502 Bad Gateway", Tailscale SSH is not enabled on the target.
- Known_hosts hashing is fine; `tailscale ssh` reads the same `~/.ssh/known_hosts` file.
- **ACL rule ordering matters.** Tailscale ACLs are first-match-wins. If a `"check"` rule for `autogroup:member` appears before an `"accept"` rule for `autogroup:admin`, admins still get checked because they're also members. Put the admin `"accept"` rule first.
- **Agent cannot run `sudo tailscale up --ssh` when sudo needs a password.** Hermes blocks `echo <pw> | sudo -S` as a brute-force attack vector. When the target node has password-protected sudo and no Tailscale API key is configured, the agent MUST tell the user to run the command manually. Workaround: SCP a setup script to the target that bundles `sudo tailscale up --ssh` with any other sudo-required steps, then have the user run it once. After Tailscale SSH is enabled, the agent can SSH in keylessly going forward.
- **API-based enablement is preferred when available.** If a Tailscale API key is configured (oAuth or personal access token), enable SSH via `POST /api/v2/device/<nodeID>/ssh` with body `{"enabled":true}` — no sudo needed. Check with `tailscale_api(method='POST', path='/api/v2/device/<id>/ssh', body={'enabled':true})`. This only works when `TS_API_KEY` or `TAILSCALE_API_KEY` is set in the environment.

## Recurring Re-Auth Problem & Root Causes

**Problem:** SSH to a Tailscale IP triggers a browser re-auth prompt:

```
# Tailscale SSH requires an additional check.
# To authenticate, visit: https://login.tailscale.com/a/...
```

This can happen on BOTH `tailscale ssh` AND direct `ssh <tailscale-ip>` — when Tailscale
SSH is enabled on the target, it intercepts ALL port 22 connections through the tailnet.
Direct IP SSH does NOT bypass it. All SSH paths (CLI, MCP tailscale_ssh, gateway plugins)
go through the same Tailscale SSH check.

There are TWO independent causes, and they stack:

### Cause 1 — ACL `"check"` Action (daily browser re-auth)

Tailscale SSH ACLs support two actions: `"check"` (default) and `"accept"`.

- **`"check"`** — requires periodic browser re-auth (~24h). This is the default
  for new tailnets and is the #1 cause of recurring "requires an additional
  check" prompts.
- **`"accept"`** — one-time auth, permanent thereafter. Trusts Tailscale identity
  without periodic re-verification.

**Critical: ACL rules are FIRST-MATCH-WINS.** If you have BOTH a `"check"` rule
and an `"accept"` rule, the one that appears FIRST in the JSON array wins. If
your member rule uses `"check"` and appears before your admin rule with
`"accept"`, admins still get checked because they're also members. Fix: put the
admin `"accept"` rule ABOVE the member `"check"` rule.

```json
"ssh": [
  {
    "action": "accept",                              // ← admins FIRST = permanent
    "src":    ["autogroup:admin"],
    "dst":    ["autogroup:self"],
    "users":  ["fated", "edwar", "root"],
  },
  {
    "action": "check",                               // ← everyone else = periodic
    "src":    ["autogroup:member"],
    "dst":    ["autogroup:self"],
    "users":  ["autogroup:nonroot", "fated", "edwar", "root"],
  }
]
```

**Fix for permanent access:** Change `"action": "check"` → `"action": "accept"` in
the Tailscale dashboard → Access Controls. For mixed-trust setups (admins permanent,
members periodic), use the two-rule pattern above with admins first.

**Fix for this session's prompt:** Visit the URL in a browser, authenticate with your
Tailscale account, and approve the source device. This is a one-click approval. You
CANNOT bypass this from the CLI — it requires human browser interaction.

**`checkPeriod` may be rejected** by the Tailscale policy editor. If it won't save,
omit it — the `"accept"` action is the reliable fix.

### Cause 2 — User Mapping (wrong user)

If the target node's SSH config only lists `root` but you're connecting as `fated`,
Tailscale SSH rejects the connection. This manifests as the same re-auth prompt
because Tailscale can't map your identity to an allowed user.

**Fix (two places, both required):**

**A) Tailscale Dashboard → Machines → <node> → SSH settings:**
- Add `fated` to the SSH users list on the machine page.
- If you only see `root`, fated isn't configured — the browser SSH button
  will default to root, confirming the mapping gap.

**B) Access Controls → Edit policy JSON (raw editor):**

The ACL `dst` field for SSH rules only accepts `autogroup:self` in current Tailscale
versions. Bare `*`, `*:*`, `autogroup:admin`, `autogroup:member` are all rejected with
"invalid dst". Since the same Google account owns all nodes in this tailnet,
`autogroup:self` is sufficient — it means "any device signed into the same account."

```json
"ssh": [
  {
    "action": "accept",
    "src":    ["autogroup:member"],
    "dst":    ["autogroup:self"],
    "users":  ["autogroup:nonroot", "root", "fated"]
  }
]
```

The `"users"` array controls which LOCAL usernames are allowed on the target.
Also add `fated` on each machine's page: **Machines → <node> → SSH settings → SSH users**.

**`checkPeriod` may be rejected** by older Tailscale versions ("unknown time" error).
If it won't save, omit it. The fix for persistent re-auth prompts is to register
an SSH public key with your Tailscale account: `tailscale configure ssh --add-key ~/.ssh/id_ed25519.pub`.

### TLS Certificates vs SSH Keys

**TLS certificates** (shown on the machine page as "No certificate found") are for
mTLS/API access — completely unrelated to SSH. A "no certificate" status is normal
and can be ignored for SSH purposes.

**SSH public keys** for Tailscale SSH are registered with your Tailscale ACCOUNT
(not per-machine) via CLI: `tailscale configure ssh --add-key ~/.ssh/id_ed25519.pub`.
This enables key-based auth instead of check-mode, eliminating browser prompts entirely.
Do this once on the source machine after Tailscale SSH is working.

**Seed all MagicDNS host keys at once (run on sovereign):**
```bash
for host in hq-ai.tail01322f.ts.net conchai.tail01322f.ts.net \
    nano-box.tail01322f.ts.net charlotte.tail01322f.ts.net \
    omega.tail01322f.ts.net cs.tail01322f.ts.net \
    csweb.tail01322f.ts.net world-of-cats.tail01322f.ts.net; do
  ssh-keyscan -H "$host" >> ~/.ssh/known_hosts 2>/dev/null
done
```

**SSH fails on a previously-working node?** The node may need `sudo tailscale up --ssh`
re-run (dual-boot into Windows, OS reinstall, or Tailscale update can reset this).
If `ssh <IP>` returns "Permission denied (publickey,password)", Tailscale SSH is
NOT enabled on the target.

**Watchdog:** A cron job at `~/.hermes/scripts/tailscale-watchdog.sh` monitors all
Linux nodes every 15min and alerts @SovereignHQbot on Telegram when nodes go
up/down. See `references/watchdog-setup.md`.

## Re-auth Watchdog (Proactive Monitoring)

To avoid discovering auth is dead mid-session, run a cron job that probes
SSH to all nodes and alerts you when state changes.

Template script at `scripts/watchdog.sh` — checks all nodes via direct IP SSH,
tracks UP/DOWN state, and sends Telegram alerts only on state transitions.

Set up with Hermes cron:
```
cronjob create --name tailscale-watchdog --schedule "*/15 * * * *" \\
    --no-agent --script tailscale-watchdog.sh
```

This catches auth expiry before your session does — you'll get a Telegram
message the moment any node becomes unreachable, with the re-auth URL.

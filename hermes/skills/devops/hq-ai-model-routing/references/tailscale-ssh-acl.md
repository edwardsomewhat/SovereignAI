# Tailscale SSH ACL — Cross-Device Setup

## Minimal working ACL (agent-to-agent SSH)

```json
"ssh": [
  {
   "action": "check",
   "src":    ["autogroup:member"],
   "dst":    ["autogroup:self"],
   "users":  ["autogroup:nonroot", "root", "fated"],
  },
],
```

**Constraints (as of May 2026):**
- `dst` only accepts `autogroup:self` — bare `*`, `*:*`, `autogroup:member`, and `autogroup:admin` are all rejected with "invalid dst"
- Cross-device SSH works when BOTH nodes are signed into the SAME tailnet account (same user column in machine list) — `autogroup:self` matches because the account owns both
- The target machine page (Machines > [node] > SSH) must list the connecting username under SSH users

## Common errors

| Error | Cause | Fix |
|-------|-------|-----|
| re-auth URL (`login.tailscale.com/a/...`) | check-mode expired | Visit URL to re-approve device |
| "invalid dst" on save | Using `*`, `*:*`, or `autogroup:member` in dst | Use only `autogroup:self` |
| SSH still fails after ACL fix | Target machine page doesn't list user | Add user in Machines > [node] > SSH users |
| "Permission denied (publickey)" | Tailscale SSH expects key, none registered | Fall back to check-mode or register key |

## Eliminating re-auth (key-based)

Register an SSH public key with your Tailscale identity (run on the connecting machine):

```bash
tailscale configure ssh --add-key ~/.ssh/id_ed25519.pub
```

This switches Tailscale SSH from check-mode to key-based auth — no more browser prompts. Works across devices on the same tailnet.

## Device re-approval URL

When you see:
```
# Tailscale SSH requires an additional check.
# To authenticate, visit: https://login.tailscale.com/a/l1e447f2f32e7c2
```

This is a one-time device authorization. Visit the URL in a browser, log into Tailscale, approve the device. The node is cached for future connections.

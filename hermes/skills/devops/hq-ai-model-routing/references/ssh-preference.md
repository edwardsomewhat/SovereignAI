# SSH Preference — Direct Over Tailscale MCP

When interacting with remote SovereignAI nodes, use direct SSH from the terminal tool instead of the Tailscale MCP SSH tool.

## Why

The Tailscale MCP `tailscale_ssh` tool has consistent issues:
- Timeout errors on long-running commands (120s hard limit)
- Host key verification failures requiring re-auth
- `ClosedResourceError` dropping connections mid-session
- `requiretty` friction with sudo commands

## Pattern

```bash
ssh fated@100.x.x.x "command"
```

Use the Tailscale IP directly. All nodes are on the tailnet with static IPs. SSH keys and host keys should be pre-configured for passwordless access.

## Node IPs

| Node | IP |
|------|-----|
| hq-ai | 100.84.92.74 |
| conchai | 100.69.153.16 |
| TheConch | 100.64.45.87 |
| nano (Fat-Eds-Eyes) | 100.81.229.44 |
| charlotte | 100.70.223.108 |
| csweb | 100.71.6.98 |
| omega | 100.84.226.78 |
| cs | 100.79.117.119 (hypervisor — do not touch) |

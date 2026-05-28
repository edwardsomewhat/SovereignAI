# Tailscale ACL Editing via REST API

Full recipe for reading, editing, and pushing Tailscale ACLs using curl + sed.
Use when the `tailscale_api` MCP tool is unavailable (missing env var, stale MCP process)
or when you need to modify HuJSON ACLs that Python's `json.load` can't parse.

## Prerequisites

`TAILSCALE_API_KEY` in `~/.hermes/.env`. Get one at https://login.tailscale.com/admin/settings/keys.
The `.env` file is credential-protected — use `sed` or `echo >>` via terminal to add it:

```bash
echo 'TAILSCALE_API_KEY=tskey-api-...' >> ~/.hermes/.env
```

## Reading the ACL

```bash
export $(grep -v '^#' ~/.hermes/.env | grep TAILSCALE_API_KEY | xargs)
curl -s "https://api.tailscale.com/api/v2/tailnet/tail01322f.ts.net/acl" \
  -u "${TAILSCALE_API_KEY}:" \
  -o /tmp/tailscale_acl.json
cat /tmp/tailscale_acl.json
```

HTTP 200 = success. The response is HuJSON (JSON with `//` comments) — do NOT pipe into `python3 -m json.tool`.

## Finding Target Lines

```bash
grep -n '"action"' /tmp/tailscale_acl.json
```

Sample output:
```
54:    "action": "accept",   // admins
60:    "action": "check",    // members — this is the one to change
```

## Editing (sed — preferred)

```bash
# Change check → accept on member SSH rule
sed -i 's/"action": "check"/"action": "accept"/' /tmp/tailscale_acl.json

# Verify
grep -n '"action"' /tmp/tailscale_acl.json
```

If only one specific rule should change, use a tighter pattern with surrounding context.
For this tailnet, the member rule has the comment `// ← everyone else = periodic re-auth`.

## Pushing Back

```bash
export $(grep -v '^#' ~/.hermes/.env | grep TAILSCALE_API_KEY | xargs)
curl -s -w "\nHTTP:%{http_code}" \
  -X POST \
  "https://api.tailscale.com/api/v2/tailnet/tail01322f.ts.net/acl" \
  -u "${TAILSCALE_API_KEY}:" \
  -H "Content-Type: application/json" \
  --data-binary @/tmp/tailscale_acl.json
```

Tailscale's ACL endpoint uses **POST** (not PUT). `--data-binary` preserves the HuJSON comments
— using `-d` would strip newlines and break the format.

HTTP 200 with the full ACL echoed back = success.

## Verification

After pushing, test SSH to any online node immediately — ACL changes propagate within seconds:

```bash
tailscale ssh <hostname> 'hostname && whoami'
```

## Common ACL Patterns

### SSH — Frictionless for All Members

```json
"ssh": [
    {
        "action": "accept",
        "src": ["autogroup:admin"],
        "dst": ["autogroup:self"],
        "users": ["root"]
    },
    {
        "action": "accept",    // ← "check" → "accept" eliminates re-auth
        "src": ["autogroup:member"],
        "dst": ["autogroup:self"],
        "users": ["autogroup:nonroot", "root"]
    }
]
```

### SSH — Admin Only, No Member Access

```json
"ssh": [
    {
        "action": "accept",
        "src": ["autogroup:admin"],
        "dst": ["autogroup:self"],
        "users": ["autogroup:nonroot", "root"]
    }
]
```

(Remove the member rule entirely — members get no SSH at all.)

## Tailnet Name

This tailnet: `tail01322f.ts.net`. Replace in URLs above if using a different tailnet.
Find yours: `tailscale status` → look at the MagicDNS suffix on any node.

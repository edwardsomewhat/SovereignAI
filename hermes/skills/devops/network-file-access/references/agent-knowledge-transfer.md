# Agent-to-Agent Knowledge Transfer

Pattern for sharing working knowledge (scripts, commands, configurations, pitfalls) with another Hermes agent on the tailnet.

## When to Use

- Partner/teammate's agent is struggling with something you already solved
- You want to hand off a working setup to another node without live coordination
- Sharing discovered hardware quirks, tool configurations, or platform-specific gotchas

## Workflow

### 1. Write a Self-Contained Brief

Create a markdown file with everything the other agent needs — no reliance on your session context:

```markdown
# Topic — Brief Title

Prepared by Hermes (<source-node>) for <target-agent> (<target-node>). Date.

---

## Context (1-2 sentences)
What this covers and why.

## Hardware / Environment
- Model, USB IDs, file paths, IPs

## Commands / Code
- Exact copy-paste-ready commands
- Python snippets if relevant

## Pitfalls / Quirks
- What will silently fail
- Platform-specific gotchas (Windows vs Linux, etc.)

## Verification
- How to confirm it works
```

Key principle: the other agent has zero context from your conversation. Include everything.

### 2. Deliver via sshpass + scp (Primary)

Taildrop is unreliable (see pitfalls in SKILL.md). Use password-based SSH:

```bash
sshpass -p '<password>' scp -o StrictHostKeyChecking=accept-new \
  /path/to/brief.md <user>@<tailscale-ip>:~/brief-name.md
```

### 3. Verify

```bash
sshpass -p '<password>' ssh -o StrictHostKeyChecking=accept-new \
  <user>@<tailscale-ip> 'ls -la ~/brief-name.md && head -3 ~/brief-name.md'
```

### 4. Save Credentials

Store the node's SSH credentials in memory so future deliveries don't require re-asking:

```
memory add: "<node> (<ip>): SSH as <user>/<password>. Taildrop unreliable, use sshpass scp."
```

## Example: Obsbot Camera Brief

The brief delivered in the originating session (`obsbot-camera-brief.md`) is an example of this pattern — it covered:
- Hardware identification (USB ID, model detection)
- Full PTZ control table with ranges and step values
- The camera sleep/wake quirk
- Python wrapper snippet
- The Windows problem (v4l2-ctl doesn't exist on Windows, 4 solution options)
- Verification steps

## Anti-Patterns

- Don't assume the other agent knows your context — spell out file paths, tool names, and discovery commands
- Don't use Taildrop as the primary delivery path — it's unreliable
- Don't omit platform differences — if your setup is Linux and theirs touches Windows, call out the incompatibilities

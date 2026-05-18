# Direct SSH Bootstrap (No Git Repo Intermediary)

Use this when bootstrapping a remote node that already has SSH access — no need to create a git repo first.

## Prerequisites

- SSH access to target node (password or key)
- `sshpass` installed on source if using password auth
- Target node has internet access for the install script

## Full Bootstrap Sequence

### 1. Check disk space

```bash
ssh user@target "df -h / && lsblk -o NAME,SIZE,TYPE,MOUNTPOINT"
```

Hermes itself is small (<500MB including deps) but skills DB and session store grow. 5GB free is comfortable minimum.

### 2. Run Hermes install script

```bash
ssh user@target 'curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash'
```

**Pitfall:** This requires a PTY for sudo prompts during build-tools install. Use `ssh -t` or, if scripting, pipe the password via `sshpass -p '...' ssh`. Without a PTY the sudo step fails — the install continues without build tools but the main package still installs.

### 3. Configure provider and model

After install, `hermes` may not be on PATH yet (shell hasn't been reloaded). Use full path or export:

```bash
ssh user@target 'export PATH="$HOME/.local/bin:$PATH" && \
  hermes config set model.default deepseek-v4-pro && \
  hermes config set model.provider deepseek && \
  hermes config set model.base_url https://api.deepseek.com/v1 && \
  hermes config set agent.max_turns 110'
```

### 4. Copy API keys

```bash
# Copy DeepSeek key from source
source_key=$(grep "^DEEPSEEK_API_KEY=" ~/.hermes/.env)
ssh user@target "echo '$source_key' >> ~/.hermes/.env"

# Copy GitHub token for skills hub access
source_gh=$(grep "^GITHUB_TOKEN=" ~/.hermes/.env)
ssh user@target "echo '$source_gh' >> ~/.hermes/.env"
```

### 5. Copy persona (SOUL.md)

```bash
cat ~/.hermes/SOUL.md | ssh user@target 'cat > ~/.hermes/SOUL.md'
```

### 6. Install system packages

```bash
ssh user@target 'echo "password" | sudo -S apt install -y ripgrep ffmpeg'
```

### 7. Install MCP SDK and mirror MCP servers

The Hermes venv has no pip by default (stripped for install size):

```bash
ssh user@target '~/.hermes/hermes-agent/venv/bin/python -m ensurepip && \
  ~/.hermes/hermes-agent/venv/bin/pip3 install mcp'
```

Then copy MCP server files and register them. Example for a Tailscale MCP server:

```bash
# Copy server file
ssh user@target 'mkdir -p ~/.hermes/mcp-servers/tailscale-mcp'
cat ~/.hermes/mcp-servers/tailscale-mcp/server.py | \
  ssh user@target 'cat > ~/.hermes/mcp-servers/tailscale-mcp/server.py && \
  chmod +x ~/.hermes/mcp-servers/tailscale-mcp/server.py'

# Register with Hermes (pipe "y" to auto-enable tools)
ssh user@target 'export PATH="$HOME/.local/bin:$PATH" && \
  echo "y" | hermes mcp add tailscale --command ~/.hermes/hermes-agent/venv/bin/python --args ~/.hermes/mcp-servers/tailscale-mcp/server.py'
```

**Pitfall:** `hermes mcp add` prompts interactively to enable tools. In non-interactive SSH, pipe `echo "y"` to auto-accept. The `hermes mcp configure` command requires an interactive terminal and cannot be scripted.

### 8. Verify the install

```bash
ssh user@target 'export PATH="$HOME/.local/bin:$PATH" && hermes doctor'
```

Key checks: API connectivity to your provider passes, config version is current, tools are loading.

## Decision: Clean Slate vs Mirror

When bootstrapping a node with a **different role** (e.g., orchestrator vs image-gen node):

- **DO mirror:** config, skills, persona, MCP servers, API keys, GitHub token
- **DON'T mirror:** memory (MEMORY.md, USER.md), session store (state.db), gateway config, cron jobs

The new node should build its own memory and user profile around its specific role. Skills and persona are reusable across roles.

## Decision: Git Repo vs Direct SSH

| | Git Repo Pattern | Direct SSH Pattern |
|---|---|---|
| Best for | Fleet management, DR, repeatable provisioning | One-off bootstraps, rapid prototyping |
| Requires | Git repo with setup script | SSH access + credentials |
| Idempotent | Yes (re-run setup.sh) | No (manual steps) |
| Skills sync | Via git push/pull | Via scp or cat pipe |
| Config drift | Repo is source of truth | Source node is source of truth |

For a fleet of 3+ nodes, prefer the git repo pattern (see SKILL.md main body). For 1-2 nodes, direct SSH is faster.

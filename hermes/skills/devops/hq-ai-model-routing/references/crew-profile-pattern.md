# Crew Agent Profile Creation

Recipe for turning a CrewAI agent definition into a fully functional Hermes profile with compute, tools, personality, and memory.

## Step 1 — Clone from default

```bash
hermes profile create <agent-name> --clone-from default
```

This gives the agent the same starting toolkit the supervisor has. No tool drift.

## Step 2 — Assign compute

Edit `~/.hermes/profiles/<agent-name>/config.yaml`:

```yaml
model:
  default: hermes3:8b                    # model name
  provider: custom:hq-ollama              # custom provider key
  base_url: http://100.84.92.74:11434/v1  # tailnet IP
  api_key: ollama
  context_length: 131072                  # max per model capability

providers:
  hq-ollama:
    base_url: http://100.84.92.74:11434/v1
    api_key: ollama

fallback_providers: '[''deepseek/deepseek-v4-flash'']'
```

Pattern: point base_url at the compute node on the tailnet. Hermes routes LLM calls there. Agent execution (tools, terminal) still happens on sovereign.

For llama.cpp compute, use `provider: custom:hq-llama` with `base_url: http://100.84.92.74:8080/v1`.

## Step 3 — Trim toolsets for model capacity

8B models (hermes3, qwen3.5, gemma4) have limited context. Trim tools to essentials:

```yaml
toolsets: '[''terminal'',''file'',''web'',''skills'']'
```

Infra needs terminal+file+web+skills. Coders would add search. Creative would add image_gen. Match the role.

Disable compression for small models to avoid context thrash:

```yaml
compression:
  enabled: false
```

Adjust max_turns:

```yaml
agent:
  max_turns: 60       # lower for 8B models (default 90)
```

## Step 4 — Write SOUL.md

Create `~/.hermes/profiles/<agent-name>/SOUL.md`. Pattern:

```markdown
# <Agent Name> — <Role>

You are <one-sentence identity>. You know every node: <key nodes>.

You report to Vern, the crew supervisor.

## Style
- Be human and conversational by default.
- When asked for a report, switch to dense, scannable format.
- Be direct about problems.

## What you do
- <3-5 specific responsibilities>
- <cadence: proactive pulse? reactive on-demand?>
- <autonomous scope>

## What you don't do
- <boundaries>
- <other agents' territory>

## Playbook (grows over time)
- <trigger> → <action>
```

## Step 5 — Create wrapper script

```bash
cat > ~/.local/bin/<agent-name> << 'EOF'
#!/bin/bash
exec hermes --profile <agent-name> "$@"
EOF
chmod +x ~/.local/bin/<agent-name>
```

Now `infra chat -q "run health pulse"` spawns the agent from cron, scripts, or terminal.

## Step 6 — Wire cron (optional, for proactive agents)

```bash
hermes cron create "30m" \
  --name "infra-pulse" \
  --prompt "Run the 30-minute health pulse across all SovereignAI nodes and report to Vern." \
  --profile infra
```

## Reference: Infra's Full Config

- Profile: `~/.hermes/profiles/infra/`
- Compute: hermes3:8b on hq-ai Ollama (:11434/v1, 128K context)
- Toolsets: terminal, file, web, skills
- Wrapper: `/home/fated/.local/bin/infra`
- Sudo: passwordless on all Linux nodes except cs (see hq-ai-model-routing skill for sudo setup command)

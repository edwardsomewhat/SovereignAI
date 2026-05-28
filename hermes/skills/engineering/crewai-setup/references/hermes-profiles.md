# Hermes Profiles for CrewAI Agents

How to build role-specific Hermes profiles so CrewAI agents have real tools, memory, and compute — not just YAML brains.

## When to use

When CrewAI agents need terminal access, SSH, Docker, file system, web access, or any real tooling — not just LLM reasoning. Each worker agent gets a Hermes profile cloned from the default profile (same starting toolkit), then specialized.

## Creating a Profile

```bash
hermes profile create <agent-name> --clone-from default
```

This creates `~/.hermes/profiles/<agent-name>/` with the same config, tools, and skills as the default profile.

## Assigning Compute (Local LLM)

Point the profile to a local inference server (Ollama, llama.cpp, etc.):

```bash
# Using providers dict (v12+ format)
HERMES_HOME=~/.hermes/profiles/<agent> hermes config set model.default <model-name>
HERMES_HOME=~/.hermes/profiles/<agent> hermes config set model.provider custom:<name>
HERMES_HOME=~/.hermes/profiles/<agent> hermes config set model.base_url http://<ip>:<port>/v1
HERMES_HOME=~/.hermes/profiles/<agent> hermes config set model.api_key <key>
```

Then define the provider in `providers` (not `custom_providers` — that's a list format, error-prone):

```yaml
providers:
  my-provider-name:
    base_url: http://100.84.92.74:11434/v1
    api_key: ollama
```

### Set context_length override

Hermes requires 64K minimum context. If your model only reports 32K (or 8K from a server `-c` flag):

```bash
HERMES_HOME=~/.hermes/profiles/<agent> hermes config set model.context_length 65536
HERMES_HOME=~/.hermes/profiles/<agent> hermes config set auxiliary.compression.context_length 65536
HERMES_HOME=~/.hermes/profiles/<agent> hermes config set auxiliary.vision.context_length 65536
HERMES_HOME=~/.hermes/profiles/<agent> hermes config set auxiliary.session_search.context_length 65536
```

### Fallback

```bash
HERMES_HOME=~/.hermes/profiles/<agent> hermes config set fallback_providers "['deepseek/deepseek-v4-flash']"
```

## Writing SOUL.md

Each profile gets its own `SOUL.md` at `~/.hermes/profiles/<agent>/SOUL.md`. This is the agent's identity — slot #1 in the system prompt.

Good SOUL.md covers:
- Role and domain knowledge
- Communication style (tone, verbosity, format preferences)
- What the agent does and doesn't do
- Escalation path (who it reports to)
- Any operational constraints or playbooks

See `templates/agent-soul.md` for a starter template.

## Trimming Toolsets

Most agents don't need the full default toolkit. Trim to what the role actually uses:

```bash
HERMES_HOME=~/.hermes/profiles/<agent> hermes config set toolsets "['terminal','file','web']"
```

Common subsets:
- **Ops/infra**: `terminal, file, web` (+ `skills` for procedure reference)
- **Coder**: `terminal, file, web, skills, delegation`
- **Creative**: `terminal, file, web, image_gen`
- **QA**: `terminal, file, web, skills`

Lowering max_turns helps with context pressure on small models:

```bash
HERMES_HOME=~/.hermes/profiles/<agent> hermes config set agent.max_turns 60
```

## Sudo Setup

Agents that need Docker, systemctl, or GPU commands need passwordless sudo:

```bash
echo 'user ALL=(ALL) NOPASSWD: /usr/bin/docker, /usr/bin/systemctl, /usr/sbin/nvidia-smi, /usr/bin/journalctl, /usr/bin/ollama' | sudo tee /etc/sudoers.d/hermes-<agent> && sudo chmod 440 /etc/sudoers.d/hermes-<agent>
```

Run on each node the agent manages. Scope to the specific commands the role needs.

## Pitfalls

### Qwen3.5-9B-MTP on llama.cpp generates reasoning tokens first
The MTP variant with the coding chat template emits `reasoning_content` tokens before visible `content`. With a full Hermes system prompt, this can cause 60s+ timeouts. Prefer Ollama qwen2.5-coder models (14b for reasoning, 7b for speed) — both support tools, have 128K context, and do not flood reasoning tokens.

### Model selection for agent profiles
Not all models work. Requirements: tool calling support, ≥64K context, and no reasoning-token flooding.

- ✅ **qwen2.5-coder:14b** — recommended for reasoning/architecture coder
- ✅ **qwen2.5-coder:7b** — recommended for fast/dispatch coder
- ⚠️ **hermes3:8b** — works but too small; hallucinates identity, misses instructions
- ❌ **deepseek-r1:14b** — no tool support (HTTP 400 "does not support tools")
- ❌ **gemma4-coder** — floods reasoning tokens before content, causes timeouts

### llama.cpp -c flag caps context
Check the server launch command for `-c` — many setups default to `-c 8192` (8K). Qwen models support 32K-128K natively. Bump to at least 65536.

### custom_providers must be a list, not dict
If you accidentally write `custom_providers` as a dict, Hermes errors with "custom_providers is a dict — it must be a YAML list." Use the `providers` dict key instead (v12+ format), which accepts a dict naturally.

### Small models + full toolkit = context overflow
8B-9B models with 32K context will fail to fit the full Hermes system prompt. Trim toolsets aggressively, disable compression, and consider 14B+ or 128K-context models.

## Verification

```bash
timeout 60 <agent> chat -q "What is your role? One sentence." --quiet
```

Expect a response in ~5-30 seconds depending on model size and context. Slower than 60s = investigate model/toolset.

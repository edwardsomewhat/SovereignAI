# Worked Example: Infra Agent (Hermes Profile)

Full walkthrough of defining and building the Infrastructure & DevOps agent
using the C+D hybrid pattern — CrewAI as brain, Hermes profile as hands.

## 5-Question Framework Applied

### Compute
- **Primary:** `hermes3:8b` on hq-ai Ollama (:11434) — 128K context, lightweight
- **Fallback:** `deepseek/deepseek-v4-flash` via API
- **Why not Qwen3.5-9B-MTP on llama.cpp:** 32K context fails Hermes 64K minimum

### Tools
- **Terminal:** SSH to all nodes (direct IP), Docker CLI, systemctl, nvidia-smi,
  df/du, ping/curl, log analysis, Dockhand dashboard
- **File:** reading logs, config inspection
- **Web:** health-check endpoints (ComfyUI, Ollama, Open WebUI)
- **Skills:** for reusable procedures
- **NOT needed:** browser, vision, session_search, image_gen

### Access
- **sudo:** all Linux nodes except cs (hypervisor, never touch)
- **QC-gated:** process killing, destructive restarts (until playbook-trusted)
- **Autonomous per playbook:** restart known services, clear logs, swap models

### Cadence
- **30-min health pulse** → reports to supervisor, silent unless issues found
- **Reactive on-demand** → Vern or user says "check X" → immediate investigation
- **Autonomous per playbook** → known issues trigger known responses
- **No freelancing** — novel problems escalate, don't experiment

### Voice
- **Default:** conversational, human, colleague-like
- **Pulse/report:** dense scannable format (`PULSE HH:MM | X/Y healthy ⚠ node: issue`)
- **Escalation:** hands conversation thread to supervisor when beyond scope

## Profile Build Commands

```bash
# Create
hermes profile create infra --clone-from default

# Configure LLM backend
hermes --profile infra config set model.provider custom:hq-ollama
hermes --profile infra config set model.default hermes3:8b
hermes --profile infra config set model.base_url http://100.84.92.74:11434/v1
hermes --profile infra config set model.api_key ollama
hermes --profile infra config set model.context_length 65536

# Fallback
hermes --profile infra config set fallback_providers "['deepseek/deepseek-v4-flash']"

# Auxiliary context overrides (all default to main model)
hermes --profile infra config set auxiliary.compression.context_length 65536
hermes --profile infra config set auxiliary.vision.context_length 65536
hermes --profile infra config set auxiliary.session_search.context_length 65536

# Trim to needed toolsets only
hermes --profile infra config set toolsets "['terminal','file','web','skills']"

# Lower max turns for worker agents
hermes --profile infra config set agent.max_turns 60

# Disable compression (tight context window)
hermes --profile infra config set compression.enabled false
```

## providers Config Block

Must use `providers` dict format, NOT `custom_providers` list:

```yaml
providers:
  hq-ollama:
    base_url: http://100.84.92.74:11434/v1
    api_key: ollama
```

## SOUL.md Structure

Saved to `~/.hermes/profiles/infra/SOUL.md`. Injected as slot #1 in the system prompt.
Key sections: role definition, style guide, scope (what you do / don't do), playbook.

## Verification

```bash
infra chat -q "What is your role? One sentence." --quiet
```

Expect: conversational response identifying as infrastructure operator,
mentioning specific nodes it monitors.

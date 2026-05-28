---
name: opencode
description: "Delegate coding to OpenCode CLI (features, PR review)."
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Coding-Agent, OpenCode, Autonomous, Refactoring, Code-Review]
    related_skills: [claude-code, codex, hermes-agent]
---

# OpenCode CLI

Use [OpenCode](https://opencode.ai) as an autonomous coding worker orchestrated by Hermes terminal/process tools. OpenCode is a provider-agnostic, open-source AI coding agent with a TUI and CLI.

## When to Use

- User explicitly asks to use OpenCode
- You want an external coding agent to implement/refactor/review code
- You need long-running coding sessions with progress checks
- You want parallel task execution in isolated workdirs/worktrees
- User asks about OpenCode vs other coding agents — see `references/pi-agent-comparison.md` for the Pi Agent comparison

## Prerequisites

- OpenCode installed: `npm config set prefix ~/.local && npm i -g opencode-ai@latest` (system install may need sudo; local prefix avoids it)
- For Ollama backends: `npm install -g @ai-sdk/openai-compatible` (required for custom provider)
- Auth configured: `opencode auth login` or set provider env vars (OPENROUTER_API_KEY, etc.)
- Provider config for Ollama: `~/.config/opencode/opencode.jsonc` with custom provider block (see Ollama Provider Setup below)
- Verify: `opencode auth list` should show at least one provider
- Git repository for code tasks (recommended)
- `pty=true` for interactive TUI sessions
- Ensure `~/.local/bin` is in PATH: `export PATH="$HOME/.local/bin:$PATH"`

## Binary Resolution (Important)

Shell environments may resolve different OpenCode binaries. If behavior differs between your terminal and Hermes, check:

```
terminal(command="which -a opencode")
terminal(command="opencode --version")
```

If needed, pin an explicit binary path:

```
terminal(command="$HOME/.opencode/bin/opencode run '...'", workdir="~/project", pty=true)
```

## One-Shot Tasks

Use `opencode run` for bounded, non-interactive tasks:

```
terminal(command="opencode run 'Add retry logic to API calls and update tests'", workdir="~/project")
```

Attach context files with `-f`:

```
terminal(command="opencode run 'Review this config for security issues' -f config.yaml -f .env.example", workdir="~/project")
```

Show model thinking with `--thinking`:

```
terminal(command="opencode run 'Debug why tests fail in CI' --thinking", workdir="~/project")
```

Force a specific model:

```
terminal(command="opencode run 'Refactor auth module' --model openrouter/anthropic/claude-sonnet-4", workdir="~/project")
```

## Interactive Sessions (Background)

For iterative work requiring multiple exchanges, start the TUI in background:

```
terminal(command="opencode", workdir="~/project", background=true, pty=true)
# Returns session_id

# Send a prompt
process(action="submit", session_id="<id>", data="Implement OAuth refresh flow and add tests")

# Monitor progress
process(action="poll", session_id="<id>")
process(action="log", session_id="<id>")

# Send follow-up input
process(action="submit", session_id="<id>", data="Now add error handling for token expiry")

# Exit cleanly — Ctrl+C
process(action="write", session_id="<id>", data="\x03")
# Or just kill the process
process(action="kill", session_id="<id>")
```

**Important:** Do NOT use `/exit` — it is not a valid OpenCode command and will open an agent selector dialog instead. Use Ctrl+C (`\x03`) or `process(action="kill")` to exit.

### TUI Keybindings

| Key | Action |
|-----|--------|
| `Enter` | Submit message (press twice if needed) |
| `Tab` | Switch between agents (build/plan) |
| `Ctrl+P` | Open command palette |
| `Ctrl+X L` | Switch session |
| `Ctrl+X M` | Switch model |
| `Ctrl+X N` | New session |
| `Ctrl+X E` | Open editor |
| `Ctrl+C` | Exit OpenCode |

### Resuming Sessions

After exiting, OpenCode prints a session ID. Resume with:

```
terminal(command="opencode -c", workdir="~/project", background=true, pty=true)  # Continue last session
terminal(command="opencode -s ses_abc123", workdir="~/project", background=true, pty=true)  # Specific session
```

## Common Flags

| Flag | Use |
|------|-----|
| `run 'prompt'` | One-shot execution and exit |
| `--continue` / `-c` | Continue the last OpenCode session |
| `--session <id>` / `-s` | Continue a specific session |
| `--agent <name>` | Choose OpenCode agent (build or plan) |
| `--model provider/model` | Force specific model |
| `--format json` | Machine-readable output/events |
| `--file <path>` / `-f` | Attach file(s) to the message |
| `--thinking` | Show model thinking blocks |
| `--variant <level>` | Reasoning effort (high, max, minimal) |
| `--title <name>` | Name the session |
| `--attach <url>` | Connect to a running opencode server |
| `--dangerously-skip-permissions` | Auto-approve all tool calls (use only in controlled environments) |

## Procedure

1. Verify tool readiness:
   - `terminal(command="opencode --version")`
   - `terminal(command="opencode auth list")`
2. For bounded tasks, use `opencode run '...'` (no pty needed).
3. For iterative tasks, start `opencode` with `background=true, pty=true`.
4. Monitor long tasks with `process(action="poll"|"log")`.
5. If OpenCode asks for input, respond via `process(action="submit", ...)`.
6. Exit with `process(action="write", data="\x03")` or `process(action="kill")`.
7. Summarize file changes, test results, and next steps back to user.

## PR Review Workflow

OpenCode has a built-in PR command:

```
terminal(command="opencode pr 42", workdir="~/project", pty=true)
```

Or review in a temporary clone for isolation:

```
terminal(command="REVIEW=$(mktemp -d) && git clone https://github.com/user/repo.git $REVIEW && cd $REVIEW && opencode run 'Review this PR vs main. Report bugs, security risks, test gaps, and style issues.' -f $(git diff origin/main --name-only | head -20 | tr '\n' ' ')", pty=true)
```

## Parallel Work Pattern

Use separate workdirs/worktrees to avoid collisions:

```
terminal(command="opencode run 'Fix issue #101 and commit'", workdir="/tmp/issue-101", background=true, pty=true)
terminal(command="opencode run 'Add parser regression tests and commit'", workdir="/tmp/issue-102", background=true, pty=true)
process(action="list")
```

## Session & Cost Management

List past sessions:

```
terminal(command="opencode session list")
```

Check token usage and costs:

```
terminal(command="opencode stats")
terminal(command="opencode stats --days 7 --models anthropic/claude-sonnet-4")
```

## Ollama Provider Setup (Local Models)

OpenCode connects to Ollama via a custom provider in `~/.config/opencode/opencode.jsonc`. The `@ai-sdk/openai-compatible` npm package must be installed globally:

```bash
npm install -g @ai-sdk/openai-compatible
```

Config example (`~/.config/opencode/opencode.jsonc`):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "ollama-hq": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Ollama (HQ-AI)",
      "options": { "baseURL": "http://100.84.92.74:11434/v1" },
      "models": {
        "laguna-xs.2:q4_K_M": { "name": "Laguna XS.2" },
        "nemotron3:33b": { "name": "Nemotron 3 33B" }
      }
    }
  }
}
```

Then use: `opencode run "..." -m ollama-hq/laguna-xs.2:q4_K_M`

Do NOT rely on env vars alone (`OPENAI_BASE_URL`, `OPENAI_API_KEY`) — they only register credentials, not a working provider for Ollama. The custom provider block is required.

## Ollama Context Window (Critical)

Ollama's OpenAI-compatible endpoint defaults to **4096 tokens** regardless of what the model supports. OpenCode's system prompt + tool definitions easily exceed 4K, causing the model to produce no output (step_start only, then silent exit).

**Symptoms:**
- `opencode run` emits `step_start` JSON event but no `text` events follow
- Model works fine with raw `curl` (light prompts) but hangs inside OpenCode
- Token usage shows `input: 4096, output: <tiny number>` — context completely full

**Fix on the Ollama server:**
```bash
sudo sed -i '/^\[Service\]/a Environment="OLLAMA_CONTEXT_LENGTH=65536"' /etc/systemd/system/ollama.service
sudo systemctl daemon-reload && sudo systemctl restart ollama
```

**Verify:** `curl http://<host>:11434/api/ps | jq '.models[0].context_length'` should show 65536.

**Workaround if server restart isn't possible:** Create a model variant with `num_ctx` baked in:
```bash
curl http://<host>:11434/api/create -d '{
  "name": "laguna-xs.2:64k",
  "from": "laguna-xs.2:q4_K_M",
  "parameters": {"num_ctx": 65536}
}'
```
Note: this may not take effect through the OpenAI-compatible endpoint if the server default overrides it. Server-level `OLLAMA_CONTEXT_LENGTH` is the reliable fix.

## Pitfalls

- Interactive `opencode` (TUI) sessions require `pty=true`. The `opencode run` command does NOT need pty.
- `/exit` is NOT a valid command — it opens an agent selector. Use Ctrl+C to exit the TUI.
- PATH mismatch can select the wrong OpenCode binary/model config.
- If OpenCode appears stuck, inspect logs before killing:
  - `process(action="log", session_id="<id>")`
- Avoid sharing one working directory across parallel OpenCode sessions.
- Enter may need to be pressed twice to submit in the TUI (once to finalize text, once to send).
- **Large local models (>8B) often fail with `@ai-sdk/openai-compatible` provider.**
  Models like laguna-xs.2 (33B) and nemotron3:33b hang or time out through OpenCode
  even when the raw Ollama `/api/chat` endpoint works perfectly. The compatibility
  layer is the bottleneck, not the model. For large local models, bypass OpenCode
  and use Ollama's native API directly.
- **Ollama defaults to 4096 context** even when the model supports 128K+. OpenCode's
  system prompt + tool definitions overflow this immediately, causing silent failures.
  Set `OLLAMA_CONTEXT_LENGTH=131072` in the Ollama systemd service or create model
  variants with baked `num_ctx`.
- OpenCode denies file writes outside the project directory by default. Use `--dangerously-skip-permissions` in controlled/cron environments. Without it, OpenCode auto-rejects external directory access.
- Some models don't support tool calling through Ollama's OpenAI-compatible endpoint (e.g., deepseek-coder-v2:16b returns "does not support tools"). Test with a simple file-create prompt first. Models known to work: granite4.1:8b, hermes3:8b, laguna-xs.2 (with sufficient context).
- **Large local models (>16B) hang silently** with @ai-sdk/openai-compatible. nemotron3:33b and laguna-xs.2 produce only `step_start` JSON events — no text, no error, no timeout message. The models respond fine to raw curl. Root cause: the ai-sdk layer sends streaming options or request fields the Ollama OpenAI-compatible endpoint mishandles for certain architectures. **Workaround:** for models ≥16B, use direct Ollama /api/chat (see crewai-setup skill → Direct Ollama API).
- **Model tool-call format varies by architecture.** Ollama's native /api/chat returns tool_calls differently per model: nemotron3:33b → JSON tool_calls ✅; granite4.1:8b → JSON tool_calls ✅; laguna-xs.2 → XML in content field ❌; deepseek-coder-v2:16b → "does not support tools" ❌. Test before wiring: `curl /api/chat` with tools array and inspect response format.

## Verification

Smoke test:

```
terminal(command="opencode run 'Respond with exactly: OPENCODE_SMOKE_OK'")
```

Success criteria:
- Output includes `OPENCODE_SMOKE_OK`
- Command exits without provider/model errors
- For code tasks: expected files changed and tests pass
- For Ollama backends: `curl http://<host>:11434/api/ps | jq '.models[0].context_length'` shows ≥ 65536. If it shows 4096, OpenCode will silently fail on any non-trivial task — fix OLLAMA_CONTEXT_LENGTH first.

## Rules

1. Prefer `opencode run` for one-shot automation — it's simpler and doesn't need pty.
2. Use interactive background mode only when iteration is needed.
3. Always scope OpenCode sessions to a single repo/workdir.
4. For long tasks, provide progress updates from `process` logs.
5. Report concrete outcomes (files changed, tests, remaining risks).
6. Exit interactive sessions with Ctrl+C or kill, never `/exit`.

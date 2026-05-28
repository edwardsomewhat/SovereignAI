---
name: crewai-setup
description: Build and configure CrewAI 1.x multi-agent systems — hierarchical crews, YAML-based agent/task configs, OpenRouter LLM wiring, C+D hybrid architecture (CrewAI as brain + Hermes profiles as execution layer), 5-question agent definition framework, common pitfalls (context minimums, provider formats, profile configuration).
---

# CrewAI Setup

Build CrewAI multi-agent crews from scratch. Covers 1.x API (≥1.14): YAML configs, `@CrewBase` decorator, hierarchical process, OpenRouter as LLM backend.

## Prerequisites

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install crewai crewai-tools python-dotenv
pip install -e .              # install project package in editable mode
```

## Project Structure

```
project/
├── .venv/
├── .env                  # API keys (OPENROUTER_API_KEY, etc.)
├── pyproject.toml
├── .gitignore
└── src/
    └── crew_package/
        ├── __init__.py
        ├── main.py
        ├── crew.py        # @CrewBase class
        └── config/
            ├── agents.yaml
            └── tasks.yaml
```

## Step 1 — agents.yaml

Each agent gets a named block with `role`, `goal`, `backstory`:

```yaml
researcher:
  role: "Senior Researcher"
  goal: "Find and synthesize information on {topic}"
  backstory: >
    You are a meticulous researcher with deep domain knowledge.
    You leave no stone unturned.
```

CrewAI replaces `{variable}` placeholders from `kickoff(inputs={...})`.

## Step 2 — tasks.yaml

Each task block: `description`, `expected_output`, `agent` (name matching agent key):

```yaml
research_task:
  description: "Research {topic} thoroughly"
  expected_output: "A list of 10 key findings"
  agent: researcher
```

## Step 3 — crew.py with @CrewBase

```python
import os
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from dotenv import load_dotenv

load_dotenv()

def _get_llm(model_override=None):
    model = model_override or os.getenv("CREW_MODEL", "deepseek/deepseek-chat")
    return f"openrouter/{model}"

@CrewBase
class MyCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def researcher(self) -> Agent:
        return Agent(config=self.agents_config["researcher"], llm=_get_llm())

    @task
    def research_task(self) -> Task:
        return Task(config=self.tasks_config["research_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[self.researcher(), self.writer()],   # call each method explicitly
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
```

## Step 4 — Hierarchical Crew (Manager + Workers)

For hierarchical mode, the manager is SEPARATE from the worker agent list:

```python
@crew
def crew(self) -> Crew:
    supervisor = self.supervisor()   # manager agent
    workers = [                      # NOT including supervisor
        self.researcher(),
        self.writer(),
    ]
    return Crew(
        agents=workers,
        tasks=self.tasks,
        process=Process.hierarchical,
        manager_agent=supervisor,
        manager_llm=f"openrouter/{os.getenv('MANAGER_MODEL', 'anthropic/claude-sonnet-4')}",
        verbose=True,
        planning=True,
        memory=True,
    )
```

## Step 5 — OpenRouter LLM Wiring

Use the `openrouter/` prefix with LiteLLM:

```python
from crewai import LLM

llm = LLM(
    model="openrouter/deepseek/deepseek-chat",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)
```

Or pass model string directly to `Agent(llm="openrouter/deepseek/deepseek-chat")` — CrewAI resolves API creds from env vars (`OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`).

Two-tier model strategy: weaker/cheaper model for workers, stronger model for the hierarchical manager. Set `manager_llm=` on the Crew for the manager; set `llm=` on each Agent for workers.

**Three-tier model strategy** (when using coding backends + QA):

| Tier | Model | Agent(s) | Purpose |
|------|-------|----------|---------|
| Manager | deepseek-v4-flash | Supervisor | Orchestrate, decompose, delegate |
| QA | deepseek-v4-flash | QA agent | Independent judgment, PASS/FLAG/REJECT |
| Router | deepseek-chat | Coders (thin wrapper) | Format tasks, route to backends |
| Compute | nemotron3:33b (local) | ollama_code tool | Actual code generation |

**Three-tier model strategy** (when using coding backends + QA):

| Tier | Model | Agent(s) | Purpose |
|------|-------|----------|---------|
| Manager | deepseek-v4-flash | Supervisor | Orchestrate, decompose, delegate |
| QA | deepseek-v4-flash | QA agent | Independent judgment, PASS/FLAG/REJECT |
| Router | deepseek-chat | Coders (thin wrapper) | Format tasks, route to backends |
| Compute | nemotron3:33b (local) | ollama_code tool | Actual code generation |

QA runs at the same tier as the Supervisor for independent judgment — catches
what delegation blind spots miss. Coders stays cheap because it never writes
code; the local model (nemotron3:33b) does the heavy lifting.

**Local Ollama helpers** (for non-coding workers like scouts, creative agents):

Use `ollama/<model>` prefix to route lightweight agents to local models on hq-ai.
No API cost, no latency, fully sovereign. Add helper functions per agent class:

```python
def _get_local_llm(model: str = "ministral-3:14b") -> str:
    """Lightweight read-only agents: scouts, inventory keepers."""
    return f"ollama/{model}"

def _get_creative_llm(model: str = "gpt-oss:20b") -> str:
    """Creative agents: workflow reasoning, copy, orchestration."""
    return f"ollama/{model}"

def _get_review_llm(model: str = "qwen3-vl:8b") -> str:
    """Vision review agent — needs VL capability."""
    return f"ollama/{model}"
```

Proven assignment (SovereignAI May 2026):

| Agent Class | Helper | Model | Size | Cost |
|------------|--------|-------|------|------|
| Scouts, inventory | `_get_local_llm()` | ministral-3:14b | 9.1GB | $0 |
| Creative (director, image, video, copy) | `_get_creative_llm()` | gpt-oss:20b | 13GB | $0 |
| Review/QC (vision) | `_get_review_llm()` | qwen3-vl:8b | 6.1GB | $0 |

All run on hq-ai P5000 16GB via Ollama. Models share VRAM — Ollama handles loading/unloading.
Keep OpenRouter for supervisor, QA, coders router, and infra where heavier reasoning earns its keep.

```python\ndef _get_manager_llm() -> str:\n    model = os.getenv(\"MANAGER_MODEL\", \"deepseek/deepseek-v4-flash\")\n    return f\"openrouter/{model}\"\n\ndef _get_qa_llm() -> str:\n    \"\"\"Same tier as manager for independent judgment.\"\"\"\n    model = os.getenv(\"QA_MODEL\", os.getenv(\"MANAGER_MODEL\", \"deepseek/deepseek-v4-flash\"))\n    return f\"openrouter/{model}\"\n\n@agent\ndef qa(self) -> Agent:\n    return Agent(config=self.agents_config[\"qa\"], llm=_get_qa_llm())\n```

## Entry Point (main.py)

```python
from dotenv import load_dotenv; load_dotenv()
from crew_package.crew import MyCrew

result = MyCrew().crew().kickoff(inputs={"topic": user_input})
print(result)
```

## Step 6 — Agent Execution Layer (Two Patterns)

The execution layer for crew agents uses TWO patterns depending on agent type:

### Pattern A: Thin Wrapper + Local LLM Tool (Coders)

For coding agents, skip Hermes profiles. Use a thin CrewAI agent with a tool
that calls a local LLM directly via Ollama's native API. The agent's YAML is
~200 tokens — just routing. The real work happens in the tool.

```python
class OllamaCodeTool(BaseTool):
    name = "ollama_code"
    # Calls hq-ai Ollama /api/chat with file tools
    # Handles text-embedded tool calls (laguna XML format)
    # Fuzzy typo matching for tool names
    # Configurable model, context, timeout
```

Key infrastructure required:
- `OLLAMA_CONTEXT_LENGTH=131072` in Ollama systemd service (default 4096 is too small)
- Model variants with baked context via `ollama create`
- Text-embedded tool call parser for models that don't produce structured JSON

### Pattern B: Hermes Profile (Infra, Ops)

For agents that need real tool access (SSH, Docker, systemd), use Hermes profiles.
Same as the original C+D pattern described above.

See `references/cd-hybrid-pattern.md` for the full architecture diagram.
See `references/coding-tool-patterns.md` for tool implementation, model compatibility,
context configuration, and text parser details.

### Creating a Worker Profile

```bash
hermes profile create <agent-name> --clone-from default
```

Then configure the profile's `config.yaml`:

```yaml
model:
  default: hermes3:8b
  provider: custom:hq-ollama
  base_url: http://100.84.92.74:11434/v1
  api_key: ollama
  context_length: 65536       # must be ≥ 64K for Hermes

providers:
  hq-ollama:
    base_url: http://100.84.92.74:11434/v1
    api_key: ollama
```

Configure via CLI:

```bash
# Point to local LLM
hermes --profile infra config set model.provider custom:hq-ollama
hermes --profile infra config set model.default hermes3:8b
hermes --profile infra config set model.base_url http://100.84.92.74:11434/v1
hermes --profile infra config set model.api_key ollama
hermes --profile infra config set model.context_length 65536

# Set auxiliary context overrides (all auxiliary models default to main model)
hermes --profile infra config set auxiliary.compression.context_length 65536
hermes --profile infra config set auxiliary.vision.context_length 65536
hermes --profile infra config set auxiliary.session_search.context_length 65536

# Trim toolsets to only what the agent needs
hermes --profile infra config set toolsets "['terminal','file','web','skills']"

# Lower max turns for worker agents (saves context)
hermes --profile infra config set agent.max_turns 60
```

### Agent Definition Framework

Define each crew agent with the 5-question framework before building the profile:

| Dimension | Question |
|-----------|----------|
| **Compute** | Which node + model? Does it meet Hermes' 64K context minimum? Fallback? |
| **Tools** | Beyond default Hermes toolkit: SSH, Docker, sudo, ComfyUI checks, etc. |
| **Access** | sudo scope (which nodes), restricted nodes (never touch), QC-gated destructive actions |
| **Cadence** | Proactive (cron health pulses)? Reactive (on-demand only)? Autonomous (playbook-driven)? |
| **Voice** | Conversational default? Ops-report on request? Escalation behavior? |

Write the SOUL.md from the answers — it's slot #1 in the system prompt for that profile.

### Fallback Providers

Set API fallback for when local compute is down:

```bash
hermes --profile infra config set fallback_providers "['deepseek/deepseek-v4-flash']"
```

### 7a — External Protocol Tool (Shinobi Pattern)

When the coding backend is a full protocol rather than a single API call (packager →
spawner → sub-agents → QA → vanish), build the protocol as a standalone Python package
and wire it in as a CrewAI `BaseTool`. The tool imports the external package and calls
its lifecycle methods — the CrewAI agent is a thin router, the protocol is the engine.

```python
# tools/shinobi_tool.py
import json, os, sys, time, uuid
from pathlib import Path
from crewai.tools import BaseTool

SHINOBI_HOME = os.getenv("SHINOBI_HOME", str(Path.home() / "repos" / "shinobi"))
if SHINOBI_HOME not in sys.path:
    sys.path.insert(0, SHINOBI_HOME)

class ShinobiTool(BaseTool):
    name = "shinobi_code"

    def _run(self, task, target="", model="", all_api=False):
        from packager.spec import TaskSpec
        from packager.models import ModelRegistry
        from packager.generator import generate_payload
        from spawner.dispatcher import Dispatcher

        spec = TaskSpec(
            mission_id=f"shinobi-{uuid.uuid4().hex[:8]}",
            goal=task, target_dir=target or os.getcwd(),
            model_preferences={"coder": model} if model else {},
        )
        payload_dir = generate_payload(spec, ModelRegistry(), f"/tmp/shinobi-payload-{int(time.time())}")

        # run_and_vanish() already includes vanish — no separate run_engine() import needed
        intel = Dispatcher(payload_dir=str(payload_dir), all_api=all_api).run_and_vanish(
            target_dir=target, purge=True,
        )

        # Intel uses "subtasks" with "agent", not "packets" with "role"
        st_list = intel.get("subtasks") or []
        return json.dumps({
            "mission_id": intel.get("mission_id"), "status": intel.get("status"),
            "subtasks": [{"agent": s["agent"], "model": s["model"], "status": s["status"]} for s in st_list],
            "recovery": intel.get("recovery"),
        }, indent=2)
```

The protocol package lives outside the CrewAI project — set `SHINOBI_HOME` env var
(or add to `sys.path`). This keeps the protocol testable independently (70 tests in
the Shinobi case) and reusable outside CrewAI.

**Bridge verification**: always verify the tool's imports match actual signatures with
`inspect.signature()` before declaring the bridge complete. Common failures: signature
mismatches, nonexistent functions, missing return values, wrong dict key names.
See `references/shinobi-tool-pattern.md` for the full protocol architecture and
the bridge verification checklist.

### 7b — Direct Ollama API (Thin Wrapper)

When local models are too large for the Hermes system prompt or produce incompatible
tool calls, replace the Hermes profile entirely with a **thin CrewAI agent + custom
BaseTool** that calls Ollama's native `/api/chat` endpoint directly.

### When to use this pattern

- Local coding models are 16B+ (nemotron3:33b, laguna) — too large for Hermes' 8K
  system prompt overhead
- Model produces tool calls in a format Ollama's native API handles but OpenCode's
  `@ai-sdk/openai-compatible` layer drops (JSON tool_calls ✓, XML tool_calls ✗)
- You want zero Hermes system prompt in the coding loop — the model sees only the
  coding task + a minimal tool instruction block

### Architecture

```
CrewAI Supervisor (API model, coordinating)
  └─→ coders agent (200-token YAML, cheap API model)
       └─→ OllamaCodeTool._run(task)
            └─→ POST hq-ai:11434/api/chat → nemotron3:33b @ 128K ctx
                 └─→ file read/write/search/execute on sovereign
```

The coders agent is ~200 tokens of YAML (`role` + `goal` + `backstory`). It does not
write code — it formats the task and calls the tool. The supervisor delegates to it
like any other crew agent.

### Building the BaseTool

See `references/direct-ollama-code-tool.md` for the full `OllamaCodeTool` implementation.
Key design points:

- **Native `/api/chat` endpoint** — not `/v1/chat/completions`. Ollama's native API
  handles `num_ctx`, `tools`, and large models reliably.
- **Tool-call loop** — model responds with tool_calls → execute locally → feed results
  back → model continues. Max 15 turns.
- **File tools**: `read_file`, `write_file`, `search_files` (rg), `run_command`, `list_files`
- **Docker/web tools**: `web_search` (SearXNG at csweb), `docker_pull`, `docker_run`
- **Default model**: configurable via `OLLAMA_CODE_MODEL` env var
- **Timeout**: 300s per API call (sufficient for 33B models spilling to system RAM)
- **System prompt**: minimal — tool list + action-first instructions, ~500 tokens total
- **Token cap**: `num_predict: 1024` prevents infinite rambling per turn (~100s at 10 tok/s)
- **Max turns**: 25 (was 15, bumped for multi-tool workflows)

### Ollama context window requirement

Ollama defaults to **4096 tokens** context. Coding agents need 64K+ (recommended 128K).
Set in the systemd service:

```bash
sudo sed -i '/^\[Service\]/a Environment="OLLAMA_CONTEXT_LENGTH=131072"' \
  /etc/systemd/system/ollama.service
sudo systemctl daemon-reload && sudo systemctl restart ollama
```

Also create model variants with baked-in context:

```bash
curl -s http://localhost:11434/api/create -d '{
  "name": "nemotron3:128k",
  "from": "nemotron3:33b",
  "parameters": {"num_ctx": 131072}
}'
```

### Model compatibility for tool calling

Local models vary in tool-call format. Test before wiring:

| Model | Tool format | Works? | SNES test | Notes |
|-------|------------|--------|-----------|-------|
| nemotron3:33b | JSON `tool_calls` | ✅ | 5 files, working file mgr (v10) | Action-first prompt critical. Can return empty after 10+ turns. |
| granite4.1:8b | JSON `tool_calls` | ✅ | 2 files, hallucinates completion | Too small for complex orchestration. Prematurely declares victory. |
| laguna-xs.2 | XML in `content` | ❌ | 0 files | XML parser needed, not yet built |
| deepseek-coder-v2:16b | None | ❌ | — | "does not support tools" |

Full benchmark: `references/coding-benchmark-snes-2026-05.md`

Test with: `curl -s http://hq-ai:11434/api/chat -d '{"model":"<model>","messages":[{"role":"user","content":"Say hi"}],"tools":[...], "stream":false}'`

### Nemotron3 analysis paralysis — and the fix

Nemotron3:33b has a binary response pattern to task framing:

| Prompt style | Behavior | Output |
|-------------|----------|--------|
| "First research/explore X, then build" | Loops forever searching | 0 files, 15 turns |
| "Search for existing solutions" | Loops forever searching | 0 files, 15 turns |
| **"BUILD IT NOW. No planning. Write code immediately."** | ✅ Produces | 8 files, functional components |

The action-first approach produced a working Flask file manager with HTML template,
Docker setup, and shared volumes. But even at its best, nemotron3 cannot build a
real emulation core — it produces stubs for domain-specific architecture tasks.

**Key principle: never give nemotron3 an exploration directive.** It will burn all
15 turns searching. Use imperative, action-first language in the system prompt:

```
CRITICAL: Use tools IMMEDIATELY. Do not plan, do not reason, do not explain.
Just do it — call write_file NOW. Explain only AFTER the code is written.
```

Also cap token generation with `num_predict: 1024` to prevent infinite rambling
per turn. Max turns bumped to 25 for multi-tool workflows.

### Docker image hallucination

Models invent plausible but nonexistent Docker image names (e.g. `snes9x/bsnes`).
Always verify with `docker pull` before trusting model output. Real images discovered:
`danniel/snes9x`, `pheonix991/bsnes-plus`. See `references/coding-benchmark-snes-2026-05.md`.

### Nemotron3 empty response (context saturation)

After 10+ turns with large context, nemotron3 sometimes returns no content and no
tool_calls. The tool returns "Model returned empty response." Likely cause: context
window filling up with long tool call histories + 8 tool definitions.

### When NOT to use this pattern

- **Infrastructure agents** (SSH, Docker, systemd) — keep as Hermes profiles.
  They need real tool access and benefit from Hermes' system prompt context.
- **Simple API-only agents** — if a CrewAI agent only needs web_search or basic
  reasoning, the thin YAML pattern is fine without a custom tool.

See `references/coding-benchmark-snes-2026-05.md` for standardized model comparison results (SNES emulator task, 4 backends, 3 prompt variants).

## Pitfalls

### DO NOT run agy directly from terminal — use the crew tool

When you need Antigravity/Gemini to execute a coding task, do NOT construct
`ssh hq-ai 'agy -p "task"'` in the terminal. The multi-layer shell quoting
(bash → SSH → bash → agy) mangles prompts — `$` signs, `--` flags, and quotes
get swallowed. Four attempts in one session all failed this way.

The correct path: use the `AntigravityTool` already wired into the coders agent
in `hermes_crew/crew.py`. Call `agy_code(task="...")` — the tool's `_shell_quote()`
handles all escaping via `subprocess.run` with no shell interpolation.

### agy -p has no streaming output — don't kill prematurely

`agy -p` buffers all output and dumps it at completion. An empty `output_preview`
or a `wait` timeout without visible text is normal. Let it run the full
`--print-timeout` window.

### Hermes 64K context minimum — local models often fail this check

Hermes refuses to initialize if the model reports < 64K context. Many local models
(Qwen3.5 9B, Gemma 4B, etc.) only support 32K. Set `model.context_length` to 65536
and also set ALL auxiliary context overrides (compression, vision, session_search).
The model will truncate at its real limit but Hermes will initialize.

The context check runs on EVERY model — main, compression, vision, session_search.
If any fall through, you get a cascading series of "below minimum" errors.

**Models known to work with Hermes profiles:**
- `hermes3:8b` (Ollama) — 128K context ✅
- `deepseek-r1:14b` (Ollama) — 128K context ✅
- Qwen3.6-27B (llama.cpp) — 128K context ✅
- Qwen3.5-9B-MTP (llama.cpp) — 32K only, fails Hermes minimum ❌

### providers vs custom_providers format

Use the `providers` dict format (v12+), NOT `custom_providers` list (legacy):

```yaml
# ✅ Correct (v12+)
providers:
  my-backend:
    base_url: http://...
    api_key: ...

# ❌ Wrong (legacy, causes "must be a YAML list" error)
custom_providers:
  my-backend:
    base_url: http://...
```

### Even trimmed profiles may hit context limits

With 32K models, the full Hermes system prompt (SOUL.md + tool defs + AGENTS.md +
memory) often exceeds the window even after 3 compression attempts. Symptoms:
`Context length exceeded: max compression attempts (3) reached`. Fixes:
- Trim toolsets aggressively (only what the agent needs)
- Disable compression if it's fighting a losing battle
- Set `agent.max_turns` lower (60 for workers)
- Skip AGENTS.md context if the profile runs from a bare directory
- Use a 128K model instead of 32K

### Local models may produce tool calls in text/XML, not structured JSON (CRITICAL)

Not all models that claim "tool support" work with Hermes' tool loop. Hermes needs
structured OpenAI-format `tool_calls` in the API response, not tool-call JSON
embedded in the `content` field. Local models on Ollama/llama.cpp have varying
compatibility:

| Model | Tool Support | Works with Hermes? |
|-------|-------------|-------------------|
| llama3.1:8b | ✅ Structured | ❌ Produces tool_calls in simple tests, but falls back to text under Hermes' full ~8K context |
| hermes3:8b | ✅ Structured | ⚠️ Yes, but too small for coding — misses instructions |
| qwen2.5-coder:14b/7b | ✅ (text JSON) | ❌ Formats calls as text — Hermes ignores |
| deepseek-r1:14b | ❌ | ❌ No tool support |
| gemma4-coder | ✅ but reasons first | ❌ Reasoning tokens flood context |

**For local coding agents, skip the Hermes tool loop.** Use a thin CrewAI wrapper
with a tool that calls Ollama's native `/api/chat` directly. The tool handles
text-embedded tool calls via regex parsing and fuzzy typo matching. Models tested:
- laguna-xs.2 (33B): Produces text-embedded calls like `write_file({"path":...})` — needs parser
- nemotron3:33b: Produces clean JSON `tool_calls` — no parser needed
- granite4.1:8b: Produces clean JSON `tool_calls` but too small for complex coding
- deepseek-coder-v2:16b: No tool support at all

**Do NOT use OpenCode's `@ai-sdk/openai-compatible` provider for large local models.**
It fails silently (hang/timeout) with models >8B on Ollama. The raw `/api/chat`
endpoint works reliably at 128K context.
   tool definitions. The tool handles the tool-call loop in Python. This avoids the
   `@ai-sdk/openai-compatible` compatibility layer which hangs with models >16B.
   See `references/direct-ollama-code-tool.md` for the full implementation.

2. **OpenCode CLI (for ≤8B models with tool support):** `opencode run` with a
   custom provider in `opencode.jsonc` using `@ai-sdk/openai-compatible`. Works for
   granite4.1:8b but not for nemotron3:33b or laguna (times out). Requires
   `--dangerously-skip-permissions` in controlled environments.

### Full crew kickoff times out when launched via terminal tool

When launching the full crew via `terminal(background=True)`, the CrewAI
initialization (loading 11 agents, YAML configs, tool imports) can exceed the
terminal tool's startup timeout. The command is blocked before any output appears.

**Workaround:** call the tool directly from Python instead of launching the full crew:

```python
# Instead of: .venv/bin/python -m hermes_crew.main "task"
# Use direct tool invocation:
from hermes_crew.tools.antigravity_tool import AntigravityTool
t = AntigravityTool()
print(t._run("detailed task description"))
```

This bypasses crew initialization entirely. Use for single-agent tasks that only
need one tool. Reserve the full crew for multi-agent orchestration where the
supervisor needs to decompose and delegate across multiple agents.

### AntigravityTool verified: SSH → agy → remote Docker deployment

The tool pipeline was verified end-to-end on 2024-05-24:
- `AntigravityTool._run()` SSHs to hq-ai, runs `agy -p "task"`
- `_quote()` properly escapes complex task strings (no shell mangling)
- `export PATH=$HOME/.local/bin:$PATH` fixes the command-not-found issue
- agy successfully deployed services to Omega via SSH (OnlyOffice, emulatorjs,
  ROM manager) and cleaned them up on request
- No artifacts left on hq-ai — agy acts as a pure pass-through, all work
  happens on the target node

### Bridge verification discipline (CRITICAL — Shinobi lesson)

When wiring an external protocol package as a CrewAI `BaseTool`, the tool's imports
MUST match the actual signatures of the external package. Do NOT write the tool against
the interface you *expect* — verify with `inspect.signature()`.

Four failures hit the ShinobiTool bridge (all fixed in SovereignAI `17e08a5`, PiNinja
`69ec908`):

1. **Signature mismatch**: `generate_payload(spec, registry, output_dir)` — tool was
   calling `generate_payload(task=..., target_dir=..., coder_model=...)`
2. **Nonexistent import**: `from vanish.engine import run_engine` — function is
   `vanish()`, not `run_engine()`. Actually, `Dispatcher.run_and_vanish()` already
   calls `vanish()` internally — the tool just needed the Dispatcher call.
3. **Missing return**: `generate_payload()` wrote files but never returned the
   payload directory path — `return output_dir` was missing.
4. **Wrong dict keys**: Intel packet uses `"subtasks"` with `"agent"`, not
   `"packets"` with `"role"`.

**Checklist before declaring a bridge complete:**
```python
import inspect
# For each imported function:
sig = inspect.signature(external_func)
print(f"{func_name} expects: {list(sig.parameters.keys())}")
# Compare against what the tool passes — fix any mismatch
```

### Never silently switch a profile's compute backend

When the primary compute is down (node unreachable, model failing to load), do NOT
unilaterally change the profile to use an API fallback. The user configured local-first
for a reason. Instead:

1. **Report the issue** — what's broken, what you tried
2. **Ask** whether to switch to API temporarily or wait for the fix
3. **If the user is actively fixing the node**, wait — don't make config changes they'll have to undo

This applies to ALL agent profiles, not just Coders. The user handles model selection;
the agent operates within the chosen compute.

### manager_agent must not be in agents list
In `Process.hierarchical`, if the manager agent also appears in `agents=`, CrewAI raises:
```
ValidationError: Manager agent should not be included in agents list.
```
Fix: remove the manager from the worker agents list. The manager is set via `manager_agent=` only.

### @CrewBase does not expose .agents as a list
`self.agents` is NOT available on the @CrewBase instance. Each agent is only accessible via its decorated method (e.g., `self.researcher()`). Collect workers explicitly by calling each method.

### Symlinked .env files
If `project/.env` is a symlink to a shared `.env`, writing to it overwrites the shared file. Check `ls -la` before writing. Merge new vars into existing content rather than replacing.

### YAML multiline strings
Use `>` (folded) for long descriptions — newlines become spaces. Use `|` (literal) only when you need to preserve line breaks. The `>` style is preferred for agent backstories and task descriptions.

### fallback_providers only triggers on connection failures, not HTTP errors

When a profile's primary provider is a local server (e.g. `custom:hq-ollama`), and that server responds with HTTP 500 (model failed to load, binary missing, etc.), the `fallback_providers` list does NOT engage. Fallback only triggers on connection-level failures (timeout, refused, DNS resolution). If the server is reachable but returning errors, the profile will fail every retry.

**Symptom:** `API call failed after 3 retries: HTTP 500: ...` — fallback never attempted.

**Fix:** Switch the primary provider to a working backend temporarily:
```bash
hermes --profile <agent> config set model.provider deepseek
hermes --profile <agent> config set model.default deepseek-chat
```
Or fix the local server first, then switch back.

### QA agent benefits from manager-tier model

When a QA agent evaluates crew outputs for correctness/completeness/security
(rather than just running test suites), use the same model tier as the manager.
A QA agent on a cheap model will rubber-stamp; same-tier gives independent judgment.
Set via env: `QA_MODEL=deepseek/deepseek-v4-flash`.

### providers: {} must be explicitly populated after clone

When you create a profile with `--clone-from default`, `config.yaml` gets `providers: {}` (empty dict). Setting `model.provider: custom:<name>` does NOT auto-create the provider entry. You must add it yourself:

```yaml
# ❌ After clone — missing provider (will fail)
model:
  provider: custom:hq-ollama
providers: {}

# ✅ After manual fix
model:
  provider: custom:hq-ollama
providers:
  hq-ollama:
    base_url: http://100.84.92.74:11434/v1
    api_key: ollama
```

The `hermes config set` CLI only sets `model.*` values — it doesn't populate the `providers` block. Use `patch` or manual editing to add it.

## Step 8 — Infra Agent (Multi-Node SSH + Docker)

Infrastructure agents need SSH access to all nodes and Docker management.
Build as thin CrewAI agents with `@tool`-decorated functions (not BaseTool subclasses).

### Node SSH Tool

```python
# tools/node_ssh_tool.py
KNOWN_NODES = {
    "sovereign": {"host": "100.124.230.56", "user": "fated"},
    "hq-ai":     {"host": "100.84.92.74",  "user": "fated"},
    "omega":     {"host": "100.84.226.78", "user": "fated"},
    # ... all nodes
}

@tool("Run Command on Node")
def run_node_command(node: str, command: str) -> str:
    """SSH into any SovereignAI node and run a command."""
    # paramiko SSH with key-based auth, 15s timeout, blocked-command denylist

@tool("Health Check All Nodes")
def health_check_all() -> str:
    """Fleet-wide audit: disk, memory, uptime, Docker containers on all nodes."""
```

### Dockhand Docker Tools

Dockhand provides a REST API for Docker management across nodes:

```python
@tool("List Docker Containers")
def list_containers(env_id: int) -> str  # Docker ps on a specific node

@tool("Manage Docker Container")
def manage_container(env_id: int, container_id: str, action: str) -> str  # start/stop/restart

@tool("Deploy Docker Stack")
def deploy_stack(env_id: int, stack_name: str, compose_yaml: str) -> str
```

### Wiring into CrewAI

```python
from hermes_crew.tools import run_node_command, health_check_all, \\
    list_environments, list_containers, manage_container, deploy_stack

@agent
def infra(self) -> Agent:
    return Agent(
        config=self.agents_config["infra"],
        llm=_get_llm(),
        tools=[run_node_command, health_check_all,
               list_environments, list_containers,
               manage_container, deploy_stack],
    )
```

### agents.yaml — Infra backstory

The backstory should list the tools the agent has and all known nodes:

```yaml
infra:
  role: "Infrastructure & DevOps Engineer"
  goal: >
    Maintain and monitor all 9 Tailscale-connected nodes. Manage Docker containers,
    SSH access, system updates, GPU drivers, and resource allocation.
    Your tools: run_node_command (SSH into any node), health_check_all (fleet audit),
    list_environments/containers (Docker via Dockhand), manage_container (start/stop/restart),
    deploy_stack (deploy Docker Compose stacks).
  backstory: >
    You know every node: sovereign (lead), conchai (GPU/ComfyUI), hq-ai (P5000/Ollama),
    nano (edge/Ollama/Coral TPU), charlotte (N8N), cs, csweb (web+DB), omega (sandbox),
    theconch (dual-boot 3090). You SSH into nodes, check disk/memory/GPU, manage Docker
    via Dockhand API, deploy stacks, and run fleet-wide health audits.
```

### QA Agent — 5-Point Evaluation Framework

QA agents are judgment-only (no tools). The evaluation framework goes in the `goal:` section
of agents.yaml so the agent sees it as its primary instruction:

1. **SPEC FAITHFULNESS** — output matches what was asked
2. **CORRECTNESS** — does it actually work? (bugs, broken logic, invalid configs)
3. **EDGE CASES** — what breaks it? (empty inputs, offline nodes, auth failures)
4. **SECURITY** — hardcoded creds? injection vectors? destructive without safeguards?
5. **PRODUCTION READINESS** — error handling, logging, timeouts, codebase patterns

Verdicts: PASS (ship it), FLAG (specific fixable issues), REJECT (fundamental flaws).
Every verdict must have a summary, findings (bullet list), and recommendation.

See `references/qa-evaluation-framework.md` for the full prompt.

```bash
cd project && .venv/bin/python -c "
from dotenv import load_dotenv; load_dotenv()
from crew_package.crew import MyCrew
c = MyCrew().crew()
print(f'Process: {c.process}, Agents: {len(c.agents)}, Tasks: {len(c.tasks)}')
# For hierarchical: print(f'Manager: {c.manager_agent.role}')
"
```

See `references/shinobi-tool-pattern.md` for the full external protocol pattern (Shinobi — 6 phases, sub-agent swarm, fallback+retry, all-API 'USB mode', protocol validation discipline).
See `references/voice-integration-research.md` for Qwen3-TTS/ASR voice integration research — local models, VRAM requirements, Hermes voice mode integration path.
See `references/api-notes.md` for field-level Agent/Task/Crew attribute tables sourced from CrewAI 1.14 docs.

See `references/sovereign-crew-architecture.md` for the SovereignAI C+D hybrid architecture — Hermes profiles as CrewAI workers, one install on sovereign, compute distributed across nodes.
See `references/cd-hybrid-pattern.md` for the updated architecture with Pattern A (thin wrapper + local LLM tool) and Pattern B (Hermes profile).
See `references/coding-tool-patterns.md` for OllamaCodeTool implementation details, model compatibility matrix, context configuration, and text-embedded tool call parser.
See `references/hermes-profiles.md` for step-by-step profile creation, compute wiring, SOUL.md authoring, toolset trimming, and common pitfalls. Starter SOUL.md template: `templates/agent-soul.md`.
See `references/infra-agent-example.md` for a full worked example of the 5-question agent definition framework and Hermes profile build — compute, tools, access, cadence, voice, and the exact CLI commands to create and configure a worker profile.
Starter Ollama-native tool template: `templates/ollama_code_tool.py` — copy and customize for local LLM coding agents.

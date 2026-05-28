# Direct Ollama Code Tool — Full Implementation

`OllamaCodeTool` — a CrewAI `BaseTool` that calls Ollama's native `/api/chat` endpoint
with tool support. Bypasses OpenCode's `@ai-sdk/openai-compatible` provider layer
(which hangs with models >16B).

Location: `src/hermes_crew/tools/ollama_code_tool.py`

## Architecture

```
CrewAI Supervisor → coders agent (200-token YAML) → OllamaCodeTool._run()
  → POST hq-ai:11434/api/chat → local model @ 64K ctx
    → model calls tools → execute locally → results fed back → loop
```

## Tools (8)

| Tool | Description |
|------|-------------|
| `read_file(path)` | Read a file with line numbers |
| `write_file(path, content)` | Create/overwrite a file |
| `search_files(pattern, path)` | Ripgrep search |
| `run_command(command)` | Shell command (30s timeout) |
| `list_files(path)` | List directory contents |
| `web_search(query)` | Search via local SearXNG (csweb:8080) |
| `docker_pull(image)` | Pull a Docker image |
| `docker_run(image, name, ports, volumes, env_vars)` | Run a container |

SearXNG endpoint: `http://100.71.6.98:8080/search?q=...&format=json`

## Current System Prompt ("Action-First")

```
CRITICAL: Use tools IMMEDIATELY. Do not plan, do not reason, do not explain what you will do.
Just do it — call write_file or web_search NOW. Explain only AFTER the code is written and tested.

When asked to build something:
1. First, web_search for existing solutions, Docker images, or pip packages
2. If you find something: docker_pull it, write a compose file, docker_run it
3. If building from scratch: IMMEDIATELY write_file to create the code
4. Then run_command to test it
5. Only then, briefly summarize what you built

NEVER spend a turn just thinking or planning. Every single turn must include at least one tool call.
Keep responses under 3 sentences — use tools for everything else.
```

## API Call Configuration

```python
"options": {"num_ctx": 65536, "num_predict": 1024}
```

- `num_ctx: 65536` — per-request context (server default is 128K, this is sufficient for coding)
- `num_predict: 1024` — caps token generation per turn (prevents infinite rambling at 10 tok/s)
- `timeout: 300s` — per API call (sufficient for 33B models on P5000)
- `max_turns: 25` — loop ceiling (was 15, bumped for complex multi-tool workflows)

## Model Compatibility

| Model | Tool format | Works? | Notes |
|-------|------------|--------|-------|
| nemotron3:33b | JSON `tool_calls` | ✅ | Binary: imperative prompts work, exploration loops forever. Can return empty mid-session. |
| granite4.1:8b | JSON `tool_calls` | ✅ | Fast, but hallucinates completion. Too small for complex orchestration. |
| laguna-xs.2 | XML in `content` | ❌ | Text parser not yet built for XML format |

## Key Design Decisions

### 1. Action-first system prompt
Original: "Output your reasoning first, then use tools. Explore the codebase..."
This caused analysis paralysis — nemotron3 spent 15 turns planning with 0 files.
Fixed: "Use tools IMMEDIATELY. Do not plan. Do not reason."

### 2. num_predict cap
Without a cap, nemotron3 can generate unlimited tokens per turn — spending entire turns
on reasoning without producing tool calls. 1024 tokens is ~100s at 10 tok/s.

### 3. Docker + web_search tools
File-only tools forced every model to build emulation cores from scratch (impossible
for ≤33B). Adding web_search and Docker tools lets models find real existing solutions
and compose them in. This was the key change that produced the best results.

### 4. 25-turn limit (was 15)
The find-and-integrate workflow needs more turns (search → pull → build → test = 4+
turns per service). 15 turns was insufficient for complex orchestration.

## Failure Modes

### Empty response (nemotron3)
After 10+ turns with large context, nemotron3 sometimes returns a response with
no `content` and no `tool_calls`. The tool returns "Model returned empty response."
and exits. Likely cause: context saturation with long tool call histories.

### Docker image hallucination
Models invent plausible but nonexistent Docker image names. Examples:
- `snes9x/bsnes` — does not exist on Docker Hub
- `ghcr.io/mame/fuse-emulator` — exists but is a ZX Spectrum emulator, not SNES

Always verify images exist with `docker pull` before trusting model output.
Real images discovered: `danniel/snes9x`, `pheonix991/bsnes-plus`, `mariotux/snes9x-gui`.

### GUI-only emulator containers
Most SNES emulator Docker images are desktop GUI apps (Qt/GTK) that crash without
a display (xvfb, VNC, etc.). Web-based options like `linuxserver/emulatorjs` exist
but have platform issues. The emulator domain is inherently hard to headlessly containerize.

## Fuzzy Typo Matcher

The tool includes typo correction for common model mistakes:
- Docker tools: `dockerpull`→`docker_pull`, `dockerrun`→`docker_run`, `start_container`→`docker_run`
- Web: `websearch`→`web_search`, `search_web`→`web_search`
- File: `ist_files`→`list_files`, `wrtie_file`→`write_file`, `raed_file`→`read_file`

## Why Not OpenCode?

OpenCode's `@ai-sdk/openai-compatible` provider hangs with models >16B on Ollama.
The direct `/api/chat` endpoint works reliably at 64K context with nemotron3:33b
and granite4.1:8b.

## Wiring

```python
# crew.py
from hermes_crew.tools import OllamaCodeTool, AntigravityTool

@agent
def coders(self) -> Agent:
    return Agent(
        config=self.agents_config["coders"],
        llm=_get_llm(),
        tools=[AntigravityTool(), OllamaCodeTool()],
    )
```

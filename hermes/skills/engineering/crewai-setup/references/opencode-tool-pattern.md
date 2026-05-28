# OpenCode as CrewAI Tool — Thin Wrapper Pattern

Replace Hermes-profile coding agents with a CrewAI agent that delegates all
code work to OpenCode CLI running on local LLMs. This eliminates the Hermes
system prompt from the coding loop entirely — the local model sees only
OpenCode's minimal coding system prompt, not the Hermes 8K token manifest.

## Architecture

```
CrewAI Supervisor (API model, e.g. deepseek-v4-flash)
  └─→ coders agent (200-token YAML, cheap API model)
       └─→ OpenCodeTool.run_opencode()
            └─→ opencode run "..." → local Ollama → Laguna/Nemotron3
```

The coders agent is a **routing layer only** — it does not write code, review
diffs, or make implementation decisions. It receives the task, formats it for
OpenCode, calls the tool, and reports results.

## CrewAI Tool Implementation

```python
# hermes_crew/tools/opencode_tool.py
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import subprocess, os, json
from pathlib import Path

class OpenCodeInput(BaseModel):
    task: str = Field(description="Detailed coding task description")
    model: str = Field(default="", description="provider/model, e.g. ollama-hq/laguna-xs.2:64k")
    workdir: str = Field(default="", description="Working directory")

class OpenCodeTool(BaseTool):
    name: str = "run_opencode"
    description: str = "Execute a coding task using OpenCode CLI with a local LLM."
    args_schema: type[BaseModel] = OpenCodeInput
    default_model: str = os.getenv("OPENCODE_DEFAULT_MODEL", "ollama-hq/laguna-xs.2:64k")
    timeout: int = int(os.getenv("OPENCODE_TIMEOUT", "600"))

    def _run(self, task: str, model: str = "", workdir: str = "") -> str:
        model = model or self.default_model
        workdir = workdir or os.getenv("OPENCODE_WORKDIR", str(Path.cwd()))
        env = os.environ.copy()
        env["PATH"] = f"{Path.home()}/.local/bin:{env.get('PATH', '')}"

        cmd = ["opencode", "run", task, "-m", model, "--format", "json",
               "--dangerously-skip-permissions"]

        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=self.timeout, cwd=workdir, env=env)

        # Parse JSON lines for text/tool events
        output_parts = []
        errors = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
                if event.get("type") == "text":
                    output_parts.append(event["part"].get("text", ""))
                elif event.get("type") == "error":
                    errors.append(event["error"]["data"]["message"])
            except json.JSONDecodeError:
                output_parts.append(line)

        if errors:
            return f"{''.join(output_parts)}\n\n[WARN: {'; '.join(errors[:3])}]"
        return "".join(output_parts) or "OpenCode completed with no output."
```

## Agent YAML (agents.yaml)

```yaml
coders:
  role: "Code Implementation Agent"
  goal: >
    Execute coding tasks by delegating to OpenCode CLI. You are a thin routing
    layer — do NOT attempt to write code yourself. Always use the run_opencode
    tool for any code implementation, refactoring, or review task.
  backstory: >
    You are a routing agent. Your only job is to receive coding tasks and pass
    them to OpenCode CLI, which runs on local LLMs. You do NOT write code,
    review diffs, or make implementation decisions yourself. You format the
    task clearly, call run_opencode, and report back what happened. The real
    work happens in OpenCode.
```

## Task YAML (tasks.yaml)

```yaml
code_implementation:
  description: >
    Implement the following feature or fix by delegating to OpenCode:
    {code_spec}.
    ALWAYS use the run_opencode tool — never write code directly.
  expected_output: >
    OpenCode execution summary: what files were changed, test results,
    and any issues encountered.
  agent: coders
```

## Wiring in crew.py

```python
from hermes_crew.tools import OpenCodeTool

@agent
def coders(self) -> Agent:
    return Agent(
        config=self.agents_config["coders"],
        llm=_get_llm(),           # cheap API model — just routing
        verbose=True,
        allow_delegation=False,
        tools=[OpenCodeTool()],   # <-- the only tool it needs
    )
```

## OpenCode Provider Config (~/.config/opencode/opencode.jsonc)

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "ollama-hq": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Ollama (HQ-AI)",
      "options": { "baseURL": "http://100.84.92.74:11434/v1" },
      "models": {
        "laguna-xs.2:64k": { "name": "Laguna XS.2 64K" },
        "nemotron3:33b": { "name": "Nemotron 3 33B" },
        "deepseek-coder-v2:16b": { "name": "DeepSeek Coder V2 16B" }
      }
    }
  }
}
```

Install the compatibility package: `npm install -g @ai-sdk/openai-compatible`

## Critical Precondition: Ollama Context Window

Ollama defaults to 4096 tokens through its OpenAI-compatible endpoint.
OpenCode's system prompt exceeds this, causing silent failures (model responds
to raw API but hangs inside OpenCode).

**Must set on the Ollama server:**
```bash
# In /etc/systemd/system/ollama.service, under [Service]:
Environment="OLLAMA_CONTEXT_LENGTH=65536"
sudo systemctl daemon-reload && sudo systemctl restart ollama
```

Verify: `curl http://<host>:11434/api/ps | jq '.models[0].context_length'`

## Pitfalls

- **4K context:** Without `OLLAMA_CONTEXT_LENGTH`, OpenCode produces zero output on any real task. Always verify before diagnosing other issues.
- **Permissions:** OpenCode denies writes outside the project directory. Use `--dangerously-skip-permissions` in controlled/cron environments.
- **Tool support:** Not all models support tool calling through Ollama's OpenAI endpoint. `deepseek-coder-v2:16b` returns "does not support tools". Test with a simple file-create prompt before wiring into the crew.
- **Slow first token:** Big models with VRAM spillover (Laguna 23GB, Nemotron 27GB on P5000 16GB) may take 30-60s for the first token. Set generous timeouts (600s). The pattern works because coding is "think hard, output once" — not streaming chat.

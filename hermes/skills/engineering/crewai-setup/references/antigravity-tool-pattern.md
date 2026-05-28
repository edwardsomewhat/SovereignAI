# Antigravity CLI as CrewAI Tool (SSH Remote)

`AntigravityTool` — wraps `agy -p` via SSH to hq-ai where Antigravity CLI is
installed and signed in. Cloud-backed, fast, handles file operations and command
execution natively.

## Prerequisites

- Antigravity CLI installed on remote node: `curl ... | bash` or npm
- Signed in: `agy auth login` (interactive, do once on the remote node)
- SSH access from sovereign to the remote node (Tailscale)

## Installation on remote node

```bash
# On hq-ai:
npm install -g @antigravity/cli
# or
curl -fsSL https://antigravity.ai/install | bash
agy auth login   # interactive — sign in with browser
```

## Tool implementation

```python
"""Antigravity CLI tool — wraps agy -p via SSH to remote node."""

import os
import subprocess
from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

AGY_HOST = os.getenv("AGY_HOST", "100.84.92.74")
AGY_TIMEOUT = int(os.getenv("AGY_TIMEOUT", "300"))


class AntigravityInput(BaseModel):
    task: str = Field(description="Detailed coding task.")
    workdir: str = Field(default="", description="Working directory on remote.")


class AntigravityTool(BaseTool):
    name: str = "agy_code"
    description: str = (
        "Execute a coding task using Antigravity CLI (cloud, fast). "
        "Handles file ops, commands, testing autonomously."
    )
    args_schema: type[BaseModel] = AntigravityInput

    def _run(self, task: str, workdir: str = "") -> str:
        workdir = workdir or "/home/fated"

        ssh_cmd = [
            "ssh", "-o", "ConnectTimeout=5",
            f"fated@{AGY_HOST}",
            f"export PATH=$HOME/.local/bin:$PATH && cd {workdir} && "
            f"agy -p '{_shell_quote(task)}' --dangerously-skip-permissions "
            f"--print-timeout 5m",
        ]

        result = subprocess.run(
            ssh_cmd, capture_output=True, text=True,
            timeout=AGY_TIMEOUT + 60,
        )

        if result.returncode != 0:
            return f"agy exit {result.returncode}: {result.stdout[:2000]}"
        return result.stdout[:8000] or "No output."


def _shell_quote(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"
```

## Key options

| Flag | Purpose |
|------|---------|
| `-p "task"` | One-shot non-interactive run |
| `--dangerously-skip-permissions` | Auto-approve file writes, commands |
| `--print-timeout 5m` | Max wait time (default 5min) |
| `-c` | Continue last session |
| `--conversation <id>` | Resume specific session |

## When to use vs ollama_code

| Factor | agy_code | ollama_code |
|--------|----------|-------------|
| Speed | Fast (cloud GPU) | Slower (P5000) |
| Cost | Free tier | $0 (own hardware) |
| Sovereignty | Cloud-dependent | Fully local |
| Best tasks | Quick fixes, simple features | Complex logic, security-sensitive |
| Model control | Antigravity's backend | Your model, your context |

## Common failure: "command not found"

SSH non-interactive shells don't source `.bashrc`. Always `export PATH=...`
in the remote command.

## Common failure: `agy -p` appears hung (empty output)

`agy -p` does **not** stream output — it buffers everything and dumps it at
completion. Do NOT kill the process because `output_preview` is empty or because
the `wait` timeout expires without visible output. A 5-minute quiet period is
normal for complex deployment tasks. The tool already handles the full
`--print-timeout 5m` window; let it run to completion.

## NEVER run agy directly from terminal(ssh ...)

Do NOT construct `ssh hq-ai 'agy -p "task"'` commands in the terminal tool.
Multi-layer shell quoting (bash → SSH → bash → agy) mangles the prompt — `$`
signs, backticks, quotes, and `--` flags get interpreted at different layers.

The correct path: use the `AntigravityTool` via the CrewAI coders agent:
  `agy_code(task="deploy emulator on Omega")`
The tool's `_shell_quote()` handles all escaping, and `subprocess.run` avoids
shell interpolation. This is already wired in `hermes_crew/crew.py`.

## Security note

`--dangerously-skip-permissions` bypasses all permission prompts. Only use
in controlled environments with trusted task sources (CrewAI supervisor).

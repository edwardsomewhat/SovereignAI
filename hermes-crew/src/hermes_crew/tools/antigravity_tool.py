"""Antigravity CLI tool for CrewAI — wraps `agy -p` via SSH to hq-ai.

Antigravity is a cloud-backed coding agent. Fast, signed-in, handles file
operations and command execution natively. This tool SSHes to hq-ai to
execute agy since that's where the binary and auth live.
"""

import os
import subprocess
from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

AGY_HOST = os.getenv("AGY_HOST", os.getenv("HQ_AI", "100.84.92.74"))
AGY_TIMEOUT = int(os.getenv("AGY_TIMEOUT", "300"))


class AntigravityInput(BaseModel):
    task: str = Field(
        description="Detailed coding task. Include file paths, language, and expected behavior."
    )
    workdir: str = Field(
        default="",
        description="Working directory on hq-ai. Empty = /home/fated.",
    )


class AntigravityTool(BaseTool):
    """Execute coding tasks using Antigravity CLI on hq-ai (cloud-backed).

    Fast, signed-in coding agent. Handles file creation, editing, command
    execution, and testing autonomously. Use for quick implementation tasks.
    """

    name: str = "agy_code"
    description: str = (
        "Execute a coding task using Antigravity CLI on hq-ai (cloud-backed, fast). "
        "Handles file operations, commands, and testing autonomously. "
        "Use for quick implementation — faster than local models. "
        "Results execute on hq-ai, not the local machine."
    )
    args_schema: type[BaseModel] = AntigravityInput

    def _run(self, task: str, workdir: str = "") -> str:
        workdir = workdir or "/home/fated"

        # Build the remote command
        ssh_cmd = [
            "ssh",
            "-o", "ConnectTimeout=5",
            "-o", "StrictHostKeyChecking=no",
            f"fated@{AGY_HOST}",
            f"export PATH=$HOME/.local/bin:$PATH && cd {workdir} && agy -p {_quote(task)} --dangerously-skip-permissions --print-timeout 5m",
        ]

        try:
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=AGY_TIMEOUT + 60,
            )

            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            if result.returncode != 0:
                return (
                    f"Antigravity exited with code {result.returncode}.\n"
                    f"Output: {stdout[:2000] or '(none)'}\n"
                    f"Error: {stderr[:500] or '(none)'}"
                )

            return stdout[:8000] if stdout else f"Antigravity completed with no output."

        except subprocess.TimeoutExpired:
            return f"Antigravity timed out after {AGY_TIMEOUT}s."
        except Exception as e:
            return f"ERROR: {type(e).__name__}: {e}"


def _quote(s: str) -> str:
    """Single-quote a string for shell, escaping internal single quotes."""
    return "'" + s.replace("'", "'\\''") + "'"

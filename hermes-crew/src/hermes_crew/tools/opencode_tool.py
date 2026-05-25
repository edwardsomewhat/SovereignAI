"""OpenCode CLI tool for CrewAI — thin wrapper around opencode run."""

import os
import subprocess
from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class OpenCodeInput(BaseModel):
    """Input schema for the OpenCode tool."""

    task: str = Field(
        description=(
            "Detailed description of the coding task to perform. "
            "Be specific about what files to create/edit, what the expected "
            "behavior is, and any constraints (language, framework, style)."
        )
    )
    model: str = Field(
        default="",
        description=(
            "Model to use in 'provider/model' format. Leave empty to use "
            "the default (ollama-hq/laguna-xs.2:64k)."
        ),
    )
    workdir: str = Field(
        default="",
        description=(
            "Working directory for the task. Leave empty to use the "
            "current working directory."
        ),
    )


class OpenCodeTool(BaseTool):
    """Execute coding tasks using OpenCode CLI with local LLMs.

    This tool shells out to `opencode run` with the given task description.
    OpenCode handles file editing, testing, and git operations autonomously.
    """

    name: str = "run_opencode"
    description: str = (
        "Execute a coding task using OpenCode CLI with a local LLM. "
        "Provide a detailed description of what code changes are needed. "
        "OpenCode will handle file creation, editing, testing, and commits. "
        "Use this for any non-trivial code implementation or refactoring."
    )
    args_schema: type[BaseModel] = OpenCodeInput

    # Configurable defaults
    default_model: str = os.getenv("OPENCODE_DEFAULT_MODEL", "ollama-hq/laguna-xs.2:128k")
    default_workdir: str = os.getenv("OPENCODE_WORKDIR", str(Path.cwd()))
    timeout: int = int(os.getenv("OPENCODE_TIMEOUT", "600"))  # 10 min default

    def _run(
        self,
        task: str,
        model: str = "",
        workdir: str = "",
    ) -> str:
        """Run OpenCode with the given task and return results."""
        model = model or self.default_model
        workdir = workdir or self.default_workdir

        env = os.environ.copy()
        env["PATH"] = f"{Path.home()}/.local/bin:{env.get('PATH', '')}"

        cmd = [
            "opencode",
            "run",
            task,
            "-m", model,
            "--format", "json",
            "--dangerously-skip-permissions",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=workdir,
                env=env,
            )

            # Parse JSON output lines for meaningful content
            output_parts = []
            errors = []

            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    import json

                    event = json.loads(line)
                    etype = event.get("type", "")

                    if etype == "text":
                        text = event.get("part", {}).get("text", "")
                        if text:
                            output_parts.append(text)
                    elif etype == "error":
                        err_data = event.get("error", {}).get("data", {})
                        msg = err_data.get("message", str(event))
                        errors.append(msg)
                    elif etype in ("tool_use_start", "tool_use_end", "tool_result"):
                        # Tool usage events — include for visibility
                        tool_name = event.get("part", {}).get("tool", "unknown")
                        if etype == "tool_use_start":
                            output_parts.append(f"[tool:{tool_name}]")
                        elif etype == "tool_result":
                            result_text = event.get("part", {}).get("text", "")
                            if result_text:
                                output_parts.append(f"[tool_result: {result_text[:200]}]")
                except json.JSONDecodeError:
                    output_parts.append(line)

            if errors:
                error_summary = "; ".join(errors[:3])
                if output_parts:
                    return (
                        f"{''.join(output_parts)}\n\n"
                        f"[WARN: {error_summary}]"
                    )
                return f"ERROR: {error_summary}"

            if not output_parts:
                if result.stderr.strip():
                    return f"OpenCode exited with no output. Stderr:\n{result.stderr[:1000]}"
                return "OpenCode completed with no output. The task may have been empty or the model produced no text."

            return "".join(output_parts)

        except subprocess.TimeoutExpired:
            return (
                f"ERROR: OpenCode timed out after {self.timeout}s. "
                f"The model ({model}) may be too slow for this task. "
                f"Try a smaller model or a simpler task."
            )
        except FileNotFoundError:
            return (
                "ERROR: opencode CLI not found. Ensure it is installed at "
                "~/.local/bin/opencode or in PATH."
            )
        except Exception as e:
            return f"ERROR: OpenCode failed: {type(e).__name__}: {e}"

"""ShinobiTool — CrewAI tool that wraps the Shinobi protocol.

This is the bridge between CrewAI's coders agent and the Shinobi
execution layer. When the CrewAI supervisor assigns a coding task,
the coders agent calls this tool, which:

1. Packages the task into a Shinobi payload
2. Deploys sub-ninjas to the target directory
3. Runs the full scout-coder-builder-reviewer-QA pipeline
4. Processes the intel (vanish + archive + memory)
5. Returns a structured result to the supervisor
"""

import json
import os
import sys
from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Ensure shinobi package is importable
SHINOBI_HOME = os.getenv("SHINOBI_HOME", str(Path.home() / "repos" / "shinobi"))
if SHINOBI_HOME not in sys.path:
    sys.path.insert(0, SHINOBI_HOME)


class ShinobiCodeInput(BaseModel):
    task: str = Field(description="Detailed coding task. Include constraints, acceptance criteria, and target context.")
    target: str = Field(default="", description="Target directory. Empty = current working directory.")
    model: str = Field(default="", description="Primary coder model. Empty = gpt-oss:20b.")
    all_api: bool = Field(default=False, description="Use all-API mode (OpenRouter). No local hardware required.")


class ShinobiTool(BaseTool):
    """Execute coding tasks via the Shinobi ninja swarm protocol.

    Deploys a self-contained ninja package to the target directory,
    spawns specialized sub-agents (scout/coder/builder/reviewer/QA),
    collects results, and returns a structured intel packet.
    Supports automatic fallback and retry with diagnostics.
    """

    name: str = "shinobi_code"
    description: str = (
        "Execute a coding task using the Shinobi ninja swarm protocol. "
        "Deploys specialized sub-agents (scout-coder-builder-reviewer-QA) "
        "to the target directory, performs the work, runs quality checks, "
        "and returns a structured intel packet. Use this for all code "
        "implementation, refactoring, and debugging tasks."
    )
    args_schema: type[BaseModel] = ShinobiCodeInput

    def _run(self, task: str, target: str = "", model: str = "", all_api: bool = False) -> str:
        """Execute the full Shinobi lifecycle."""
        target = target or os.getcwd()

        try:
            from packager.generator import generate_payload
            from spawner.dispatcher import Dispatcher
            from vanish.engine import run_engine
        except ImportError as e:
            return f"Shinobi import error: {e}. Is SHINOBI_HOME set? Current: {SHINOBI_HOME}"

        # Phase 1: Package the task
        try:
            payload_dir = generate_payload(
                task=task,
                target_dir=target,
                coder_model=model or "gpt-oss:20b",
            )
        except Exception as e:
            return f"Packager failed: {e}"

        # Phase 2: Deploy and execute
        try:
            dispatcher = Dispatcher(
                payload_dir=str(payload_dir),
                all_api=all_api,
            )
            mission = dispatcher.run_and_vanish()
        except Exception as e:
            return f"Dispatcher failed: {e}"

        # Phase 3: Process intel
        try:
            intel = run_engine(mission)
        except Exception as e:
            return f"Vanish engine failed: {e}"

        # Format result for CrewAI supervisor
        status = "PASS" if mission.all_passed() else ("ERROR" if mission.has_errors() else "REJECT")
        subtasks = []
        for pkt in mission.packets:
            subtasks.append({
                "agent": pkt.agent,
                "model": pkt.model,
                "status": pkt.status.value,
                "output_preview": (pkt.output or "")[:200],
            })

        result = {
            "mission_id": mission.mission_id,
            "status": status,
            "subtasks": subtasks,
            "recovery": mission.recovery,
            "summary": mission.summary(),
        }

        return json.dumps(result, indent=2)

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
import time
import uuid
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

        # Phase 1: Package the task
        try:
            from packager.spec import TaskSpec
            from packager.models import ModelRegistry
            from packager.generator import generate_payload
        except ImportError as e:
            return f"Shinobi import error: {e}. Is SHINOBI_HOME set? Current: {SHINOBI_HOME}"

        try:
            spec = TaskSpec(
                mission_id=f"shinobi-{uuid.uuid4().hex[:8]}",
                goal=task,
                target_dir=target,
                model_preferences={"coder": model} if model else {},
            )
            registry = ModelRegistry()
            output_dir = f"/tmp/shinobi-payload-{int(time.time())}"
            payload_dir = generate_payload(spec, registry, output_dir)
        except Exception as e:
            return f"Packager failed: {e}"

        # Phase 2: Deploy, run, and vanish (all-in-one)
        try:
            from spawner.dispatcher import Dispatcher

            dispatcher = Dispatcher(
                payload_dir=str(payload_dir),
                all_api=all_api,
            )
            intel = dispatcher.run_and_vanish(
                target_dir=target,
                purge=True,
            )
        except Exception as e:
            return f"Dispatcher failed: {e}"

        # Format result for CrewAI supervisor
        status = intel.get("status", "ERROR")
        subtasks = []
        st_list = intel.get("subtasks") or []
        for pkt in st_list:
            subtasks.append({
                "agent": pkt.get("agent", "unknown"),
                "model": pkt.get("model", "unknown"),
                "status": pkt.get("status", "unknown"),
                "output_preview": (pkt.get("output", "") or "")[:200],
            })

        # Build summary from subtask results
        passed = sum(1 for s in subtasks if s["status"] == "PASS")
        failed = len(subtasks) - passed
        summary = f"Shinobi mission: {passed}/{len(subtasks)} passed"
        if failed:
            summary += f", {failed} failed"
        if intel.get("recovery", {}).get("attempts", 0) > 0:
            summary += f" (recovery: {intel['recovery']['attempts']} attempts)"

        result = {
            "mission_id": intel.get("mission_id", "unknown"),
            "status": status,
            "subtasks": subtasks,
            "recovery": intel.get("recovery", {}),
            "summary": summary,
            "intel_saved_to": intel.get("intel_saved_to", ""),
        }

        return json.dumps(result, indent=2)

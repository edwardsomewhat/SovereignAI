# Shinobi Tool Pattern — External Protocol as CrewAI Tool

When the coding backend is a full protocol rather than a single API call, build it as a
standalone Python package and wire it in as a CrewAI `BaseTool`.

## Why This Pattern

- The protocol has its own lifecycle (packager → spawner → sub-agents → QA → vanish)
- It needs independent testability (70 tests in the Shinobi case)
- It should work outside CrewAI (standalone CLI, USB deployment)
- The CrewAI agent remains a thin router (~200 tokens of YAML)

## Architecture

```
CrewAI Supervisor (API model, coordinating)
  └─→ Pi Ninja coders agent (thin YAML, cheap API model)
       ├─ PRIMARY: ShinobiTool → packager → spawner → sub-ninjas → QA → vanish
       ├─ FALLBACK: AntigravityTool (cloud Gemini, fast)
       └─ FALLBACK: OllamaCodeTool (local hq-ai models)
```

The coders agent gets three tools and chooses per task. The supervisor doesn't know
or care which backend was used — it just sees the structured result.

## Protocol Package Structure

```
shinobi/                     # Standalone repo, pip-installable
├── pyproject.toml
├── packager/                # Phase 1: TaskSpec → payload/
│   ├── spec.py              #   TaskSpec dataclass + parser
│   ├── models.py            #   ModelRegistry
│   ├── generator.py         #   Payload directory builder
│   └── cli.py               #   CLI: shinobi-pack
├── spawner/                 # Phase 2: Payload → sub-agents
│   ├── config.py            #   Payload config loader
│   ├── packet.py            #   ResultPacket + PacketStatus
│   ├── dispatcher.py        #   Orchestrates scout→coder→builder→reviewer→QA
│   ├── diagnostician.py     #   Failure analysis agent
│   └── runners/             #   Model-specific runners
│       ├── base.py          #     Runner ABC + factory
│       ├── ollama.py        #     Local Ollama
│       ├── agy.py           #     Antigravity CLI
│       ├── openrouter.py    #     API (USB mode)
│       └── fallback.py      #     Primary→fallback chain
├── vanish/                  # Phase 3: Result → intel + archive + purge
│   ├── synopsis.py          #   Rich intel packet builder
│   ├── archive.py           #   Copy artifacts to ~/.hermes/shinobi/archive/
│   └── engine.py            #   Full vanish lifecycle
├── processor/               # Phase 4: Intel → memory + graphify + session
│   ├── parser.py            #   Intel packet parser
│   ├── memory_writer.py     #   Hermes memory entries
│   ├── graphify_updater.py  #   Graphify commands
│   ├── session_archiver.py  #   Session DB entries
│   └── cli.py               #   CLI: shinobi-process
└── tests/                   # 70 tests covering all phases
```

## CrewAI Tool Implementation

```python
# hermes-crew/src/hermes_crew/tools/shinobi_tool.py
"""ShinobiTool — CrewAI tool that wraps the Shinobi protocol."""

import json, os, sys
from pathlib import Path
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

SHINOBI_HOME = os.getenv("SHINOBI_HOME", str(Path.home() / "repos" / "shinobi"))
if SHINOBI_HOME not in sys.path:
    sys.path.insert(0, SHINOBI_HOME)

class ShinobiCodeInput(BaseModel):
    task: str = Field(description="Detailed coding task.")
    target: str = Field(default="", description="Target directory.")
    model: str = Field(default="", description="Primary coder model.")
    all_api: bool = Field(default=False, description="All-API mode (no local hardware).")

class ShinobiTool(BaseTool):
    name: str = "shinobi_code"
    description: str = (
        "Execute a coding task using the Shinobi ninja swarm protocol. "
        "Deploys specialized sub-agents (scout-coder-builder-reviewer-QA) "
        "to the target directory, performs the work, runs quality checks, "
        "and returns a structured intel packet."
    )
    args_schema: type[BaseModel] = ShinobiCodeInput

    def _run(self, task, target="", model="", all_api=False):
        target = target or os.getcwd()

        # Phase 1: Package — build TaskSpec + ModelRegistry
        from packager.spec import TaskSpec
        from packager.models import ModelRegistry
        from packager.generator import generate_payload

        spec = TaskSpec(
            mission_id=f"shinobi-{uuid.uuid4().hex[:8]}",
            goal=task,
            target_dir=target,
            model_preferences={"coder": model} if model else {},
        )
        registry = ModelRegistry()
        output_dir = f"/tmp/shinobi-payload-{int(time.time())}"
        payload_dir = generate_payload(spec, registry, output_dir)

        # Phase 2: Deploy + run + vanish (all-in-one — run_and_vanish() calls vanish())
        from spawner.dispatcher import Dispatcher

        dispatcher = Dispatcher(payload_dir=str(payload_dir), all_api=all_api)
        intel = dispatcher.run_and_vanish(target_dir=target, purge=True)

        # Format for CrewAI supervisor (intel uses "subtasks" with "agent", not "packets" with "role")
        status = intel.get("status", "ERROR")
        st_list = intel.get("subtasks") or []
        passed = sum(1 for s in st_list if s.get("status") == "PASS")
        summary = f"Shinobi mission: {passed}/{len(st_list)} passed"

        return json.dumps({
            "mission_id": intel.get("mission_id", "unknown"),
            "status": status,
            "subtasks": [{
                "agent": s.get("agent", "unknown"),
                "model": s.get("model", "unknown"),
                "status": s.get("status", "unknown"),
                "output_preview": (s.get("output", "") or "")[:200],
            } for s in st_list],
            "recovery": intel.get("recovery", {}),
            "summary": summary,
            "intel_saved_to": intel.get("intel_saved_to", ""),
        }, indent=2)
```

## Wiring in crew.py

```python
# crew.py
from hermes_crew.tools import AntigravityTool, OllamaCodeTool, ShinobiTool

@agent
def coders(self) -> Agent:
    """Pi Ninja — deploys Shinobi swarms for coding tasks."""
    return Agent(
        config=self.agents_config["coders"],
        llm=_get_llm(),
        verbose=True,
        allow_delegation=False,
        tools=[ShinobiTool(), AntigravityTool(), OllamaCodeTool()],
    )
```

The agents.yaml gets updated so the coders agent knows Shinobi is primary:

```yaml
coders:
  role: "Pi Ninja — Coding Orchestrator"
  goal: >
    Execute coding tasks using the Shinobi ninja swarm protocol.
    PRIMARY: shinobi_code — packager → spawner → sub-ninjas → QA → vanish.
    FALLBACK: agy_code (cloud) + ollama_code (local) for quick single-file tasks.
```

## Key Design Decisions

1. **Separate repo** — The protocol is its own pip-installable package. This enables
   independent testing, standalone CLI usage, and USB deployment without CrewAI.

2. **sys.path injection** — The tool adds the protocol package to `sys.path` rather than
   requiring pip install. This keeps the development loop fast.

3. **Lifecycle in tool, not agent** — The CrewAI agent is a router. The tool calls
   `generate_payload()` → `Dispatcher.run_and_vanish()` (which internally calls
   `vanish()`). The agent never sees the sub-agent swarm — it just gets the
   structured intel packet back.

4. **Fallback chain** — The coders agent has three tools. If Shinobi is overkill for
   a one-line fix, it falls back to `agy_code` or `ollama_code`.

5. **All-API "USB mode"** — Setting `all_api=True` routes everything through
   OpenRouter. The protocol works on any machine with Python and internet — no
   local models, no GPU, no Tailscale. This is how the SovereignAI unit ships on
   a USB stick.

## Sub-Agent Specialization

Each sub-ninja is a narrow specialist — different model, different tool set:

| Ninja | Model | Tools | Purpose |
|-------|-------|-------|---------|
| Scout | qwen3.6:9b | grep, read, graphify | Codebase exploration |
| Coder | gpt-oss:20b | write, edit, bash | Implementation |
| Builder | agy/Gemini | bash, docker | Compilation, deployment |
| Reviewer | MiniMax M2.5 | read, diff | Inline QC per step |
| QA | MiniMax M2.5 | read, test | Final verification |

## Recovery & Retry

- Primary model fails → auto-switches to fallback runner
- Subtask ERROR → up to 3 retries, spawning a Diagnostician between attempts
- Subtask REJECT (code is wrong) → stops immediately, no retry
- All retries exhausted → escalates with full recovery data in intel packet

## Bridge API Verification (CRITICAL)

When wiring an external protocol as a CrewAI tool, the tool's `_run()` method is a BRIDGE
between two independently-developed APIs. Verify each call site against the actual function
signatures before declaring the bridge complete:

```python
import inspect
# For each import in the tool's _run():
print(inspect.signature(generate_payload))  # Compare with what _run() passes
print(inspect.signature(thing.__init__))     # For class constructors
print(dir(module))                           # For function existence
```

Common bridge bugs found in the ShinobiTool:
- **Signature mismatch**: `generate_payload(task=, target_dir=, coder_model=)` vs actual
  `generate_payload(spec: TaskSpec, registry: ModelRegistry, output_dir: str)`
- **Missing return value**: `generate_payload()` wrote files but didn't `return output_dir`
- **Nonexistent function**: `from vanish.engine import run_engine` — the function is
  `vanish()`, but `Dispatcher.run_and_vanish()` already calls it, making the import redundant
- **Wrong key names**: intel packet uses `subtasks` with `agent` field, not `packets` with `role`

Always run a full E2E smoke test of the tool's `_run()` method before deploying — the
protocol package itself may pass all its unit tests while the bridge is silently broken.

## When to Use This Pattern

- The coding backend is a multi-phase protocol, not a single API call
- You need independent testability (70+ tests in the protocol package)
- The protocol must work outside CrewAI (standalone CLI, USB deployment)
- You want radical sub-agent specialization (different models per role)

## Protocol Validation Discipline (CRITICAL)

When live-testing a protocol via real coding tasks, the GOAL is to validate the protocol,
not to perfect the artifact. This is a discipline:

1. **Pick an epic task deliberately** — the task should stress sub-agent coordination,
   code inheritance across squads, and recovery. A Game Boy emulator is perfect; an
   auth endpoint isn't.

2. **Deploy squads until the protocol pattern proves itself** — each squad demonstrates
   a different protocol capability (fresh build, codeblind inheritance, input handling,
   bug recovery). 3-4 squads is sufficient.

3. **Stop when the protocol is validated** — once you've demonstrated that squads can
   build, inherit, handle input, and the recovery/diagnostician works, the protocol
   test is COMPLETE. Do NOT chase domain-specific artifact bugs (emulator HALT/STOP/
   joypad timing, missing opcodes, MBC3 support). Those are emulator bugs, not protocol
   bugs. Every real task will have its own domain bugs — fixing them all is infinite.

4. **The proof is structural**:
   - ✅ Sub-agents deployed and executed in sequence (scout→coder→builder→reviewer→QA)
   - ✅ Squads inherited and extended code from prior squads without breaking it
   - ✅ Recovery and fallback engaged on failures
   - ✅ Intel packets preserved results for future sessions
   - ❌ The artifact has bugs — this is NORMAL and EXPECTED for AI-generated code

5. **Artifact bugs are data, not failures** — they prove the protocol catches real
   issues. A QA ninja flagging HALT timing bugs is the protocol WORKING, not failing.
   Most real Shinobi tasks will produce working code on the first pass — an emulator
   is deliberately chosen as a stress test.

Pitfall: The agent may get absorbed in debugging the artifact. If you hear "let me
try one more squad" after the pattern is already proven, it's time to stop. The
protocol earned its 70/70 tests and 4 live squad deployments.

## When NOT to Use

- Simple single-API-call backends (use Pattern A — thin wrapper + local LLM tool)
- Quick one-file fixes (use AntigravityTool or OllamaCodeTool directly)
- The protocol has no independent use case outside the crew

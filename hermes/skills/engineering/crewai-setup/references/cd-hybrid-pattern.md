# C+D Hybrid Architecture for SovereignAI Crew

CrewAI is the brain — it decomposes requests and routes to specialist agents.
The execution layer uses TWO patterns depending on agent type.

## Pattern A: Thin Wrapper + Local LLM Tool (Coders)

For agents that do code generation, skip Hermes profiles entirely. Use a thin
CrewAI agent (~200 tokens of YAML) with a tool that calls a local LLM directly.

```
CrewAI Supervisor (deepseek-v4-flash, API)
  └─→ coders agent (deepseek-chat, ~200 token YAML)
       ├─ ollama_code tool → hq-ai Ollama → laguna-xs.2:128k (sovereign)
       └─ agy_code tool    → Antigravity CLI on hq-ai (cloud, fast)
```

**Why this works:** The Hermes system prompt (~8K tokens) adds massive overhead
for local models. By making the coders agent a thin router with tools, the
actual coding model sees only its task + tool definitions — no orchestration
boilerplate.

**Tool options:**
- `ollama_code`: Direct `/api/chat` calls to Ollama. Full control. Models tested:
  laguna-xs.2 (33B, text-embedded tool calls), nemotron3 (33B, JSON tools),
  granite4.1 (8B, JSON tools, fast but limited).
- `agy_code`: Antigravity CLI via SSH to hq-ai. Cloud-backed, signed-in, fast.

**Critical infrastructure:**
- `OLLAMA_CONTEXT_LENGTH=131072` in Ollama systemd service on hq-ai.
  Default is 4096 — too small for tool definitions + system prompt.
- Create model variants with baked context: `ollama create laguna-xs.2:128k from laguna-xs.2:q4_K_M PARAMETER num_ctx 131072`
- P5000 16GB VRAM + 62GB system RAM. Models up to 27GB spill to RAM — fine for
  coding (think-hard-output-once pattern, not streaming chat).

## Pattern B: Hermes Profile (Infra)

For agents that need real tool access (SSH, Docker, systemd, Tailscale), use
a full Hermes profile.

```
CrewAI supervisor
  └── infra agent → Hermes profile "infra"
       compute: hq-ai or API
       tools: terminal, file, web, skills
```

## QC

QA agent runs on deepseek-v4-flash (same tier as Supervisor) for independent
quality judgment. PASS/FLAG/REJECT verdicts. Does NOT re-run coder tests —
evaluates correctness, completeness, security, production readiness.

The old QC pipeline (coders→handoff→QC, qc-rubric/qc-handoff/qc-process skills)
was dismantled. Coders handle their own quality natively through the tool loop.

# OpenCode Local Delegation — Hybrid API/Local Coding Workflow

When local models can't drive Hermes' tool loop but CAN code well via OpenCode CLI.

## Why This Pattern Exists

As of May 2026, no locally-hosted model on hq-ai (Ollama or llama.cpp) reliably drives the Hermes agent tool loop for coding tasks. qwen2.5-coder models have tool calling but format calls as text JSON instead of structured `tool_calls`. hermes3:8b produces structured calls but is too small. deepseek-r1 has no tool support. gemma4-coder floods reasoning tokens.

But local models ARE excellent at code generation. OpenCode CLI has its own tool execution loop built specifically for coding — it edits files, runs tests, commits, and handles errors better than any general-purpose agent.

## Architecture

```
Hermes coders (API/DeepSeek)     → plans, delegates, reviews
       │
       ▼
OpenCode CLI (local hq-ai GPU)  → writes, tests, commits
```

The Hermes profile stays thin: it understands the task, formulates a prompt for OpenCode, runs `opencode run`, and reviews the result. All heavy coding work happens locally on the GPU.

## Workflow

### Step 1: Plan (Hermes on API)
- Understand the coding task
- Identify files to create/modify
- Formulate a clear prompt for OpenCode

### Step 2: Delegate (terminal call to OpenCode)
```bash
# One-shot task
terminal(command="opencode run 'Write a Python function validate_ip(ip: str) -> bool'", workdir="~/project")

# With context files
terminal(command="opencode run 'Refactor auth module' -f src/auth.py -f tests/test_auth.py", workdir="~/project")
```

### Step 3: Verify (Hermes reviews)
- Check the diff: `git diff`
- Run tests: `python -m pytest`
- Review quality: edge cases covered? clean style?

### Step 4: QC (if gated)
- Produce QC handoff per qc-handoff skill
- Invoke QC agent for code domain review

## When Local Models Work Best

| Model | Best For |
|-------|----------|
| qwen2.5-coder:14b | Complex features, refactoring, debugging |
| qwen2.5-coder:7b | Simple fixes, boilerplate, quick edits |
| Qwopus 9B MTP | Speed-critical tasks (MTP spec decode) |
| DeepSeek-Coder-V2-Lite 16B | Architecture, cross-file changes |

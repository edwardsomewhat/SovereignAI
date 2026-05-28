# Shinobi Deployment via agy on hq-ai

Proven pattern for deploying Shinobi coding missions to remote targets using
agy on hq-ai (gpt-oss:20b) for code generation.

## Verified Results (2026-05-25)

Game Boy emulator deployed to Omega:
- Model: gpt-oss:20b via agy on hq-ai (P5000 16GB)
- Coder: 456s, 762 lines CPU + MMU
- Builder: ~120s, GPU + main loop + integration
- Tests: 14/14 PASSED on target
- Frame 240 rendered with visible Nintendo logo pixels

## agy Deployment Command

```bash
# Write prompt to file first (avoids SSH quoting issues)
scp /tmp/prompt.txt fated@100.84.92.74:/tmp/prompt.txt

# Run agy headless with auto-approve
ssh fated@100.84.92.74 "cat /tmp/prompt.txt | ~/.local/bin/agy -p --dangerously-skip-permissions"
```

## Key Behaviors

- agy is at `~/.local/bin/agy` on hq-ai, NOT in $PATH
- `-p` = headless mode, `--dangerously-skip-permissions` = auto-approve all tool calls
- **No streaming** — agy dumps all output at exit. Expect 2-8 minutes of silence.
- agy writes files locally on hq-ai — SCP results to target after each phase
- agy may time out during test phase but files are already written

## Deployment Sequence

1. Package mission payload on Sovereign
2. SCP payload to target (Omega)
3. agy Coder on hq-ai generates CPU/MMU code
4. SCP coder output from hq-ai to target
5. agy Builder on hq-ai generates GPU/integration code
6. SCP builder output from hq-ai to target
7. Run pytest on target
8. Archive intel + artifacts on Sovereign
9. Clean hq-ai temp files

## Pitfall: One-Shot Runners

The Shinobi spawner runners define tools but don't execute a tool-calling loop.
Until fixed, Hermes acts as orchestrator — dispatching each sub-ninja via agy.
agy has its own tool loop that handles read/write/terminal execution.

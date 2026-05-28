# Coding Tool Patterns for CrewAI + Local LLMs

## OllamaCodeTool (sovereign path)

Direct calls to Ollama's native `/api/chat` endpoint. Bypasses OpenCode's
`@ai-sdk/openai-compatible` layer which fails with large models.

### Architecture
```
CrewAI agent → OllamaCodeTool._run(task)
  → POST http://hq-ai:11434/api/chat {model, messages, tools, options:{num_ctx}}
  → Model responds with tool_calls or text
  → If tool_calls: execute locally, feed results back, loop
  → If text only: return to agent
```

### Text-Embedded Tool Call Parser

Some local models (laguna-xs.2) produce tool calls as text rather than
structured JSON in the `tool_calls` field. The tool call appears as:
```
ist_files({"path": "/tmp"})
write_file({"path": "foo.py", "content": "print('hi')"})
```

The parser (`_parse_text_tool_calls`) uses regex:
```
([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\s*(\{[^}]+\})\s*\)
```

Fuzzy matching (`_fuzzy_tool`) handles typos:
- `ist_files` → `list_files`
- `wrtie_file` → `write_file`
- `exec_command` → `run_command`

### Context Requirements

Ollama defaults to 4096 context. OpenCode's system prompt + tool defs overflow
this immediately. Fix:
```bash
# In /etc/systemd/system/ollama.service, add:
Environment="OLLAMA_CONTEXT_LENGTH=131072"
sudo systemctl daemon-reload && sudo systemctl restart ollama
```

Create model variants with baked context:
```bash
ollama create laguna-xs.2:128k from laguna-xs.2:q4_K_M
# Then set num_ctx in the Modelfile or via API
```

### Model Compatibility

| Model | Size | Tool Format | Works? | Notes |
|-------|------|-------------|--------|-------|
| laguna-xs.2 | 33.4B, 23GB | Text-embedded | ✅ Parser | Fuzzy typos, XML variants |
| nemotron3:33b | 33B, 27GB | JSON structured | ✅ Native | Clean tool_calls |
| granite4.1:8b | 8B, 5.3GB | JSON structured | ✅ Native | Fast, ceiling at complex tasks |
| deepseek-coder-v2 | 16B | None | ❌ | "does not support tools" |
| hermes3:8b | 8B, 4.7GB | Unknown | ❓ | Untested |

## AntigravityTool (cloud path)

Wraps `agy -p` via SSH to hq-ai. Fast, cloud-backed, signed-in.
```python
ssh fated@HQ_AI "export PATH=~/.local/bin:$PATH && agy -p 'task' --dangerously-skip-permissions --print-timeout 5m"
```

Limitations: no model selection flag discovered. One-shot mode times out at
5 minutes for complex tasks.

## Resource Contention

hq-ai's P5000 is shared. Coding models and ComfyUI cannot run simultaneously.
Before heavy coding, check:
```bash
curl -s http://hq-ai:11434/api/ps | python3 -c "import sys,json; print(len(json.load(sys.stdin)['models']))"
```

## Key Lessons

1. **8B models produce confident stubs, not real code.** They'll claim "done"
   with 11-line Flask files and no actual logic. Verify file sizes and run tests.
2. **33B models can code but need patience.** First token may take 30-60s on
   spillover models. The think-hard-output-once pattern means this is fine.
3. **Text parsers are essential for local models.** Many produce function calls
   in text rather than structured tool_calls. Build regex + fuzzy matching.
4. **OpenCode's compatibility layer is the bottleneck, not the models.**
   The raw Ollama API works; OpenCode's @ai-sdk/openai-compatible doesn't.
5. **System prompt MUST be action-first, not reason-first.** Telling a model
   "Output your reasoning first, then use tools" causes analysis paralysis on
   complex tasks — nemotron3:33b burned 15 turns (30 min) with zero files
   written. Use "Use tools IMMEDIATELY. Do not plan or reason. Just do it."
   and "NEVER spend a turn just thinking. Every turn must include a tool call."
6. **Cap token generation with `num_predict`.** Without a cap, models ramble
   indefinitely per turn. Set `num_predict: 1024` in the Ollama options — at
   10 tok/s this gives ~100s per turn, which is plenty for a tool call + brief
   explanation. Combine with the action-first prompt for best results.
7. **Nemotron3:33b is a tool-capable overthinker.** It produces clean JSON
   `tool_calls` (unlike laguna's text format) and executes simple tasks
   correctly (hello.py in 1 turn). But on complex greenfield tasks, it falls
   into exploration loops — searching, planning, reading nonexistent files —
   without ever calling `write_file`. Aggressive action-first prompting and
   a low `num_predict` cap are essential for this model.

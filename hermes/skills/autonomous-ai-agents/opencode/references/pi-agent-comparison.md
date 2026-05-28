# Pi Agent vs OpenCode — Architecture Comparison

## Quick Summary

| | Pi Agent | OpenCode |
|---|---|---|
| **System prompt** | ~200 tokens | Much larger (tools + LSP + permissions) |
| **Tools shipped** | 4 (minimal) | 12+ (batteries included) |
| **Sub-agents** | Build via extensions | Built-in Plan/Build agents |
| **Extension model** | In-process TypeScript, 25+ hooks | Out-of-process plugins |
| **Resource use** | Very low RAM/token overhead | Higher (full IDE experience) |
| **Local model compat** | Raw API calls, minimal compat layer | **Broken for >16B models** (ai-sdk layer) |
| **Customization** | Replace UI, intercept any event, modify per-turn | Add tools, hook tool execution, config via JSON |
| **Philosophy** | "Chassis + engine — build what you need" | "Production car — configure what you need" |

## Key Distinction

- **OpenCode** is a Claude Code alternative: polished, feature-complete, works out of the box. But its `@ai-sdk/openai-compatible` layer silently fails with large local models (nemotron3:33b, laguna-xs.2).
- **Pi Agent** is a programmable coding agent runtime. Its in-process TypeScript extensions can intercept/modify any lifecycle event (tool calls, context injection, input gating, system prompts per-turn). You build sub-agents, planning modes, and custom workflows as extensions — nothing is hardcoded.

## For SovereignAI

Pi's architecture fits better for local-first, model-agnostic coding:
- **Minimal prompt overhead** → more context for actual code
- **Extension hooks** → build exactly the sub-agent isolation pattern you want
- **No compat layer** → raw API calls work with any model
- **Tree-structured sessions** → branch/fork/explore without losing state

But OpenCode's built-in sub-agents and Plan mode mean less work upfront —
if you can use smaller models (<8B) that survive the compat layer.

## Resources

- **Official docs:** https://pi.dev/docs/latest/extensions
- **Community extensions:** https://github.com/qualisero/awesome-pi-agent (990★)
- **Official examples:** https://github.com/earendil-works/pi/blob/main/packages/coding-agent/examples/extensions
- **Key SovereignAI extensions:** `pi-ssh-remote` (redirect ops to remote host), `agent-stuff` (sub-agent spawning), `pi-hooks` (LSP + permissions)

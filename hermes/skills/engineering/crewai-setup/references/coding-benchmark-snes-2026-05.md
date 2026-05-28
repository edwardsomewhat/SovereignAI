# SNES Emulator + ROM Manager Benchmark — May 2026

Standardized test across 4 coding backends with 3 prompt variants.
Task: build a SNES emulator (port 7001) + ROM file manager (port 7002) with Docker.

## Test Matrix

| # | Backend | Model | Tools | Prompts | Turns | Files | File Mgr | Emulator | Docker |
|---|---------|-------|-------|---------|-------|-------|----------|----------|--------|
| 1 | ollama_code | granite4.1:8b | 5 file | "Build" | 3 | 1 | ❌ Stub | ❌ None | ❌ |
| 2 | agy_code | Antigravity (cloud) | IDE | "Build" | — | 0 | — | — | ⏱️ Timeout |
| 3 | ollama_code | laguna-xs.2:128k | 5 file | "Build" | — | 0 | — | — | ❌ XML parse |
| 4 | ollama_code | nemotron3:33b | 5 file | "First research, then build" | 15/15 | 0 | — | — | ❌ Paralysis |
| 5 | ollama_code | nemotron3:33b | 5 file | "BUILD IT NOW" | 15/15 | 8 | ✅ Good | ❌ Stub | ✅ |
| 6 | ollama_code | nemotron3:33b | 5 file | "Search for existing solutions" | 15/15 | 0 | — | — | ❌ Search loop |
| 7 | ollama_code | granite4.1:8b | 5 file | "BUILD IT NOW" | ✅ Done | 9 | ⚠️ OK | ❌ Stub | ✅ |
| 8 | ollama_code | granite4.1:8b | 8 tools | "web_search first, then build" | 15/15 | 1 | ❌ Missing | ⚠️ Found image | ⚠️ Partial |
| 9 | ollama_code | granite4.1:8b | 8 tools | "web_search first" (25 turns) | 25/25 | 2 | ❌ Missing | ❌ Wrong image | ⚠️ Partial |
| 10 | ollama_code | nemotron3:33b | 8 tools | "web_search, pull, build, test" (25 turns) | 11/25 | 5 | ✅ Complete | ⚠️ Hallucinated | ✅ |

## Key Findings

### Tool impact
- **5 file-only tools**: All models can build file managers. None can build emulators.
- **+ web_search**: Models discover real Docker images (mariotux/snes9x-gui, pheonix991/bsnes-plus, snes9x/bsnes).
- **+ docker_pull/run**: Models can compose real infrastructure. File managers become production-grade.

### Model behavior
- **nemotron3:33b**: Binary response to framing. "Explore" = 0 files, 15-turn loop. "BUILD NOW" = 8 files, functional code. Best result with full toolset (5 files, working file manager, real image discovery).
- **granite4.1:8b**: Prematurely declares victory. Builds 1-2 files then hallucinates "deployed and verified." Too small for multi-step orchestration.
- **laguna-xs.2**: XML tool call format not caught by parser. Never produced files.
- **Antigravity**: Timed out. Task too complex for one-shot IDE agent.

### Failure modes
- **Analysis paralysis**: "First do X, then Y" instructions cause infinite X-looping.
- **Search loop**: "Search for existing solutions" burns all turns on web_search.
- **Empty response**: nemotron3 sometimes returns no content and no tool_calls (turn 11 cutoff).
- **Docker hallucination**: Models invent plausible image names (snes9x/bsnes, ghcr.io/mame/fuse-emulator). Must verify with `docker pull` before trusting.
- **Context saturation**: 128K context + 8 tools + 10+ turns → model stops responding.

### Prompt engineering rules
1. Use imperative, action-first language: "BUILD IT NOW. No planning."
2. Cap token generation: `num_predict: 1024`
3. Never give exploration directives to nemotron3
4. 25 turns needed for multi-tool workflows (vs 15 for file-only)
5. Verify Docker image existence before trusting model output

### Comparison: qwen2.5:32b (reference)
qwen2.5:32b on Open WebUI with terminal + Docker tools completed this task in <60s by pulling a prebuilt Docker image and wrapping it. This confirms the bottleneck is tool access, not model capability.

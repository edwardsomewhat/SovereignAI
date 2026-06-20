# SovereignAI

### A sovereign self-hosted AI infrastructure stack. No cloud dependency. No subscriptions. No telemetry.

> *"The best definition of freedom is the absence of reliance."*

SovereignAI is the blueprint for a fully local AI ecosystem — a distributed fleet of Tailscale-connected nodes running LLMs, image/video generation, CAD manufacturing, web services, automation, and quality control. Everything runs on your own hardware. Everything stays on your own network. The API layer is an optional quality fallback, never a dependency.

This repo is the living source of truth: agent configs, the full CrewAI multi-agent system, 154+ skills, and the Shinobi coding swarm protocol.

---

## The Vision

**$4,500–$7,500 per household unit.** One-time sale as a systems integrator. Never recurring.

SovereignAI doesn't compete in the subscription AI market — it destroys the playing field. Every cycle of compute run locally is a cycle denied to centralized server farms. We're building a world where AI belongs to the user, not the vendor.

---

## Architecture

### The Fleet (8 nodes, Tailscale mesh)

| Node | Role | Hardware | Key Services |
|------|------|----------|-------------|
| **sovereign** | Brain / Orchestrator | — | Hermes Agent, Crew Supervisor |
| **conchai** | GPU Workhorse | RTX 3090 24GB | ComfyUI (images, video), SearXNG, Firecrawl, Kiwix |
| **hq-ai** | LLM Server | Quadro P5000 16GB, 16GB RAM | Ollama (16 models), ComfyUI (fallback), Qwen TTS |
| **Fat-Eds-Eyes** | Edge Vision | Jetson Orin | Coral TPU (<15ms), Florence 2 (captions/detection/OCR), Ollama edge |
| **charlotte** | Automation | — | N8N workflows |
| **csweb** | Web + DB | — | Syndicate CMS, PostgreSQL, Open WebUI |
| **cs** | Combustion Syndicate | — | Core infrastructure |
| **omega** | Sandbox | 4GB RAM | Docker test deployments via Hawser |

### Operations Philosophy

**GPU Routing — the right chip for the right job:**

| GPU | Node | What runs there | Why |
|-----|------|----------------|-----|
| RTX 3090 24GB | conchai | ComfyUI (images + video) | Only card with enough VRAM for Flux (16.1GB), Wan (14.3GB), and HunyuanVideo (16.7GB). Near-idle most of the time — spun up on demand. |
| Quadro P5000 16GB | hq-ai | Ollama LLMs (11 models), ComfyUI fallback, Qwen TTS | Primary inference server. Runs gpt-oss:20b as the main agent model. Smaller models (≤16GB) live here. |
| Jetson Orin | Fat-Eds-Eyes | Coral TPU + Florence 2 | Edge vision <15ms classification + deep Florence 2 analysis. No heavy inference. |

**Model selection philosophy:**
- **Small models for small tasks.** Not every request needs a 20B parameter model. Hermes3:8b handles quick queries; deepseek-ocr:3b extracts text; ministral-3:14b runs the Scout.
- **Find existing solutions, then integrate/wrap.** Never build from scratch what the open-source ecosystem already solved. Models ≤33B compose Docker, Flask CRUD, and wrap tools reliably. They cannot build complex systems (emulators, compilers) from nothing — so don't ask them to.
- **API as optional quality layer.** OpenRouter free tier (gemma-4-31b-it) is the fallback for image review if local qwen3-vl:8b is unavailable. Everything else runs local. No hard dependency on external services.
- **Nick handles model selection. Hermes handles infra ops.** Clear separation.

**The Conch:** Conchai is dual-boot (TheConch for Windows, Conchai for Linux). The 3090 follows whichever OS is running — "Lord of the Flies conch" — whoever holds it, holds the floor.

**Spec-driven development:** Nick prefers building from specs. The agent plans, the agent executes. "Risk it" — build now, refine later. Dense multi-point communication, every point acknowledged.

### Design Principles (from the Sovereign Codex)

- **Autopoiesis** — the system writes, builds, and deploys its own tools. It is a forge, not a hammer.
- **The Polymorphic Engine** — HQ changes its digital shape based on the immediate necessity. Universal applicability.
- **The Builder Protocol** — the Watchdog provisions infrastructure. "If it isn't in the Registry, it doesn't exist."
- **Swappable Brain Doctrine** — the Intelligence Node is disposable. The Core is persistent. Swap the engine without losing the driver.

---

## CrewAI Multi-Agent System

12 specialized agents coordinated by a hierarchical Supervisor:

| Agent | Role | Tools |
|-------|------|-------|
| **Supervisor** | Orchestrates all tasks | — |
| **Infra** | Fleet operator | SSH, Docker, health checks |
| **Coders (Pi Ninja)** | Coding swarm | Shinobi, Antigravity, Ollama Code |
| **Art Studio** | Visual creative | ComfyUI (Flux, Wan, HunyuanVideo) |
| **Fab Studio** | CAD manufacturing | Florence 2 → OpenSCAD → STL |
| **Vision** | Image analysis | Coral TPU, Florence 2 |
| **QA** | Quality gate | DeepSeek V4 Flash |
| **Web Dev** | Full-stack web | FastAPI, React, PostgreSQL |
| **DB Manager** | Data persistence | PostgreSQL, SQLite, ChromaDB |
| **Cloudflare** | DNS + edge | Tunnels, Workers, R2 |
| **Payments** | Billing | Stripe, crypto gateways |
| **N8N Manager** | Automation | N8N workflows |

14 task definitions covering infrastructure audits, code implementation (full Shinobi swarm: scout→coder→builder→reviewer→QA), creative generation, fabrication, DNS, payments, and quality gating.

---

## Creative Department (Art + Fab)

### Art Studio
Generates images, video, and audio via ComfyUI on Conchai's RTX 3090:

**Image:** Flux Dev fp8, JuggernautXL, SDXL, photon_v1, Qwen Image Edit, Flux Fill  
**Video:** Wan 2.1/2.2 (T2V + I2V), HunyuanVideo 1.5, Kandinsky5 Lite  
**Copy:** gpt-oss:20b on hq-ai (taglines, ad copy, scripts)  
**Review:** qwen3-vl:8b on hq-ai (~30s reviews), fallback to gemma-4-31b-it via OpenRouter free tier  
**TTS:** Qwen TTS with Nick voice clone on hq-ai

Pipeline: Creative Director → routes to Image/Video/Copy Studio → Review Agent → deliver. Fully wired and operational (May 2026).

### Fab Studio
Engineering CAD for physical fabrication — NOT diffusion 3D:

Pipeline: Creality Ferret 3D scanner (OBJ) → Florence 2 analysis (Jetson Orin) → OpenSCAD parametric CAD → STL/STEP → Fusion 360 cleanup → 3D print.

Use cases: arcade cabinets, TV boxes, e-scooter body panels, Hermes physical shell.

---

## Pi Ninja — Coding Swarm Protocol

The `coders` agent deploys zero-footprint coding swarms via the Shinobi protocol:

```
scout → coder → builder → reviewer → QA → vanish
```

Each mission: explore the codebase, implement changes, build, review, test, then vanish — leaving only a rich intel packet behind. Fallback: Antigravity CLI (cloud) and Ollama Code (local hq-ai models) for quick single-file tasks.

Full Shinobi source: [`edwardsomewhat/PiNinja`](https://github.com/edwardsomewhat/PiNinja) (git submodule in `shinobi/`)

---

## Agent Skills

154 skills across 22 categories — the agent's procedural memory:

| Category | Skills | Highlights |
|----------|--------|-----------|
| Creative | 29 | ComfyUI, Image Studio, Video Studio, Copy Studio, Review Agent, Creative Director, Fab Studio, TouchDesigner, pixel art, p5.js, ASCII art/video, infographics, songwriting |
| DevOps | 11 | Network Scout, Tailscale SSH/MCP, node bootstrap, Kanban workers, webhooks, TTS deployment |
| Engineering | 13 | CrewAI setup, QC suite (agent/rubric/process/handoff), TDD, diagnose, prototype, zoom-out |
| MLOps | 20 | llama.cpp, vLLM, Axolotl, Unsloth, TRL, DSPy, Florence 2, SAM, AudioCraft, RAG |
| Productivity | 12 | Google Workspace, Notion, Airtable, PowerPoint, Linear, maps, handoff, caveman mode |
| Software Engineering | 14 | Book rule sets (Clean Code/Architecture, DDD, Refactoring, Pragmatic Programmer, etc.) |
| Web Search | 3 | SearXNG, Firecrawl, Kiwix (offline Wikipedia) |
| GitHub | 5 | Auth, PR workflow, code review, issues, repo management |
| Other | 47 | Gaming, media, email, research, red-teaming, smart home, social media, browser automation |

---

## RAG Knowledge Base

ChromaDB at `~/.hermes/rag_db/` — one collection:

- **sovereign_rag** (72,916 chunks, 503MB): Full project knowledge — Sovereign Codex, Genesis Logs, architecture specs, network maps, email configs, Pi Coding Agent docs (26 pages), IDE histories from Antigravity/sage/conchAI/DevCSwebs

Query via `sovereign_rag.py query "..."` — gives the agent instant recall of the project's design intent and architecture. Rebuilt June 2026 after ChromaDB Rust binding corruption; stable on chromadb 1.4.1.

---

## Memory Infrastructure

### Mnemosyne (BEAM Architecture)

Deployed June 2026 as the primary agent memory backbone:

- **v3.10.0** — MIT-licensed, single SQLite file, zero external APIs
- **28 MCP tools** — `mnemosyne_remember`, `mnemosyne_recall`, `mnemosyne_triple_add`, graph traversal, scratchpad, canonical facts, etc.
- **Recall latency:** 2.67ms p50 (100% precision@K on benchmarks)
- **Vector search:** fastembed bge-small-en-v1.5 (no GPU required)
- **Dual-write active** with Honcho through June 21, 2026 — cutover to Mnemosyne-primary after 48hr validation

Honcho remains as semantic memory backup. ChromaDB handles RAG (knowledge retrieval). Mnemosyne handles episodic/working memory for agent conversations.

---

## Training Pipeline

Session mining pipeline captures Hermes conversation transcripts → summarizes via local LLM → grades A/B/C/D → curates best examples for fine-tuning. Cron-driven every 4 hours on sovereign.

Script: `scripts/training_pipeline.py`

---

## Repo Structure

```
├── hermes/
│   ├── config.yaml              # Hermes Agent configuration
│   ├── SOUL.md                  # Agent persona / personality
│   └── skills/                  # 154 skills across 22 categories
├── hermes-crew/                 # CrewAI multi-agent system
│   └── src/hermes_crew/
│       ├── config/agents.yaml   # 12 agent definitions
│       ├── config/tasks.yaml    # 14 task definitions
│       ├── crew.py              # Crew assembly (hierarchical)
│       └── tools/               # Shinobi, Antigravity, Ollama Code, infra tools
├── shinobi/                     # Pi Ninja coding swarm (git submodule)
├── scripts/
│   ├── sync-to-repo.sh          # Auto-syncs ~/.hermes/ → repo
│   ├── training_pipeline.py     # Session mining for fine-tuning data
│   └── sovereign-sync.sh
├── systemd/                     # Service definitions
└── setup.sh                     # Bootstrap script for fresh nodes
```

---

## Quick Start

```bash
git clone https://github.com/edwardsomewhat/SovereignAI.git --recurse-submodules
cd SovereignAI
./setup.sh
```

Requires: Linux (Ubuntu 24.04+), Hermes Agent, Tailscale, Python 3.12+.

---

## Progress Log

| Date | Milestone |
|------|-----------|
| Jan 2026 | Sovereign Codex v2 ratified. Genesis architecture locked. |
| Mar 2026 | 8-node Tailscale mesh operational. Ollama + ComfyUI serving. |
| Apr 2026 | CrewAI multi-agent system deployed. 11 agents, hierarchical orchestration. |
| May 2026 | Creative Department wired end-to-end (Director → Studio → Review). Shinobi v0.1.0 shipped. QA evaluation framework deployed. |
| May 2026 | Art Studio + Fab Studio added as first-class crew agents. PiNinja added as submodule. RAG re-indexed. |
| Jun 2026 | hq-ai OOM fixed (64GB→16GB RAM, host overcommit resolved). Ollama stable at 16 models. |
| Jun 2026 | Mnemosyne v3.10.0 deployed — BEAM memory architecture (28 MCP tools, dual-write with Honcho, 2.67ms recall). |
| Jun 2026 | ChromaDB RAG rebuilt — 72,916 chunks recovered from corrupted SQLite, fresh collection, stable on 1.4.1. |
| Jun 2026 | General Research track deployed (parallel pipeline, overnight cron, T1/T2 briefs). Agent Protocol directory created. |
| **Next** | Mnemosyne cutover (June 21), Fab Studio end-to-end automation, Scout initial inventory scans, RAG full validation |

---

## Author

**Nick Schweska** — Primary Architect, Combustion Syndicate.

Built for sovereignty. No rent. No reliance.

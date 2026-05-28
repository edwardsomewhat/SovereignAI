---
name: sovereign-rag
description: "Query the Sovereign RAG database — retrieves relevant context from the Sovereign Codex, architecture docs, network maps, email configs, AND Pi Coding Agent documentation. Use when user asks about SovereignAI architecture, Pi (pi.dev) coding agent, extensions, skills, providers, Custom models, SDQ, RPC mode, session format, or themes."
---

# Sovereign RAG

Query the ChromaDB RAG database at `~/.hermes/rag_db/` which contains all SovereignAI documents.

## Query

```bash
/home/fated/.hermes/hermes-agent/venv/bin/python /home/fated/sovereign_rag.py query "USER_QUESTION"
```

Replace USER_QUESTION with the user's actual question. The output shows the top 5 most relevant document chunks with source filenames and distance scores.

## Re-index

If new documents are added to /home/fated/ (taildropped or created), re-run:

```bash
/home/fated/.hermes/hermes-agent/venv/bin/python /home/fated/sovereign_rag.py
```

## Documents indexed

**Sovereign Codex collection** (sovereign_codex):
- THE SOVEREIGN CODEX v2.txt (11 chunks)
- Project Genesis Log The Sovereign U.md (3 chunks)
- Project Genesis Log v2.md (3 chunks)
- Project Scoping Sovereign Unit AI.txt (2 chunks)
- The Sovereign Unit Master Architect v1.md (2 chunks)
- sovereign diagram.md (2 chunks)
- --- Combustion Syndicate Network --.md (2 chunks)
- Combustion Syndicate Network.txt (2 chunks)
- purly.txt (1 chunk)
- purely mail stuff.txt (6 chunks)

**Pi Documentation collection** (sovereign_docs) — from pi.dev/docs:
- 25 pages covering: quickstart, usage, providers, settings, keybindings, sessions, compaction, extensions, skills, prompt templates, themes, packages, custom models, custom providers, SDK, RPC mode, JSON event stream, TUI components, session format, Windows, Termux, tmux, terminal setup, shell aliases, development (53 chunks)

Re-index Pi docs when they update:
```bash
/home/fated/.hermes/hermes-agent/venv/bin/python /home/fated/.hermes/pi-docs/index_pi_docs.py
```

## Network Discovery (RAG + Tailscale)

When the user asks about the overall architecture or distributed network, the RAG gives you the documented design — but the live network may have evolved. Cross-reference RAG results with live Tailscale state for a complete picture:

1. Query the RAG for architecture docs: `query "architecture nodes network topology"`
2. Query for Codex principles: `query "Sovereign Codex principles Builder Protocol"`
3. Call `tailscale_status` (Tailscale MCP) for the live node list, IPs, and online/offline state
4. Cross-reference: RAG tells you the design intent (e.g., "The Watchdog is an Orange Pi"), Tailscale tells you what's actually running (e.g., "Fat-Eds-Eyes" is the nano node at 100.81.229.44)

Documents that are especially useful for network topology:
- `Combustion Syndicate Network.txt` — node hostnames, Tailscale IPs, user accounts
- `The Sovereign Unit Master Architect v1.md` — VM/container roles and hardware specs
- `Project Genesis Log v2.md` — the Registry component and Builder Protocol

## Adding New Documentation Sources

See [references/docs-scraping-pattern.md](references/docs-scraping-pattern.md) for the full workflow: map → scrape → chunk → index → verify.

Quick re-index for Pi docs:
```bash
/home/fated/.hermes/hermes-agent/venv/bin/python /home/fated/.hermes/pi-docs/index_pi_docs.py
```

## Pitfalls

- RAG queries print `Loading weights` progress bars and `HF_TOKEN` warnings to stderr. These are harmless noise from the embedding model loader — ignore them.
- Results include distance scores; lower = better match. Scores above ~0.55 may be tangentially relevant rather than directly on-point.
- The RAG is a snapshot of documents as they were at last index. New taildropped files won't appear until `re-index` is run.
- Short queries work better than long compound questions — the embedding model does best with focused topical queries. For complex questions, run 2-3 targeted queries instead of one mega-query.

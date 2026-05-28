---
name: sovereign-rag
description: "Query the Sovereign RAG database — retrieves relevant context from the Sovereign Codex, architecture docs, network maps, and email configs. Use when user asks about SovereignAI architecture, the Watchdog, Registry, Builder Protocol, network nodes, or email accounts."
---

# Sovereign RAG

Query the ChromaDB RAG database at `~/.hermes/rag_db/` which contains all SovereignAI documents.

## Architecture

- **Database:** ChromaDB (PersistentClient, SQLite-backed)
- **Embeddings:** `all-MiniLM-L6-v2` via sentence-transformers (small, fast, local — no API calls)
- **Collection:** `sovereign_codex`
- **Chunking:** 1500-char sliding windows with 200-char overlap, broken at paragraph boundaries
- **Each node has its own independent database** — conchai and sovereign maintain separate indexes from the same source documents

## Setup (first run)

```bash
# Install dependencies (in Hermes venv)
/home/fated/.hermes/hermes-agent/venv/bin/pip3 install chromadb sentence-transformers

# Index all SovereignAI documents
/home/fated/.hermes/hermes-agent/venv/bin/python /home/fated/sovereign_rag.py
```

The script automatically chunks documents and stores embeddings. Documents are read from the home directory — scp or taildrop new .md/.txt files there before re-indexing.

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

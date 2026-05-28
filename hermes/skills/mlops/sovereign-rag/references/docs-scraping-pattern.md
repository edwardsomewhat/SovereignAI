# Scraping & Indexing Documentation Sites into ChromaDB

Pattern used for pi.dev/docs — repeatable for any documentation site.

## 1. Map the documentation tree

Browse the docs index page to get the full page list:

```bash
# Use web_extract on the main docs page to get the ToC
# Identify all linked pages and their URLs
```

For pi.dev, the main page at `https://pi.dev/docs/latest` had 25 linked sub-pages.
Use `web_extract` in batches of 5 URLs (the max per call).

## 2. Scrape all pages

Batch-scrape via web_extract. Each batch returns markdown content:

```
Batch 1: quickstart, usage, providers, settings, keybindings
Batch 2: sessions, compaction, extensions, skills, prompt-templates
Batch 3: themes, packages, models, custom-provider, sdk
Batch 4: rpc, json, tui, session-format, windows
Batch 5: termux, tmux, terminal-setup, shell-aliases, development
```

Pages come back as LLM-summarized markdown. For small pages (<5000 chars), full content is preserved.

## 3. Save as markdown files

Write each page to a docs directory with numbered prefixes for ordering:

```
~/.hermes/pi-docs/
├── 00-index.md
├── 01-quickstart.md
├── 02-usage.md
├── ...
└── 25-development.md
```

Use `execute_code` to batch-write files (avoids dozens of individual `write_file` calls).

## 4. Create the indexing script

Template at `~/.hermes/pi-docs/index_pi_docs.py`. Key elements:

```python
import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path

DOCS_DIR = Path.home() / ".hermes" / "pi-docs"
DB_DIR = Path.home() / ".hermes" / "rag_db"

# Setup
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"  # small, fast, local
)
client = chromadb.PersistentClient(path=str(DB_DIR))
collection = client.get_or_create_collection("collection_name", embedding_function=embedding_fn)

# For each file: read, chunk, add to collection
# Chunk size: 1500 chars, overlap: 200 chars
# Delete existing chunks for a file before re-adding (idempotent re-index)
# Metadata: source, title, type, chunk number
```

**Important:** Use `SentenceTransformerEmbeddingFunction` with `all-MiniLM-L6-v2` — it's local, fast, and produces good embeddings for documentation search.

## 5. Run indexing

```bash
~/.hermes/hermes-agent/venv/bin/python ~/.hermes/pi-docs/index_pi_docs.py 2>&1
```

The `Loading weights` and `HF_TOKEN` warnings to stderr are harmless.

## 6. Verify with test queries

```python
collection.query(query_texts=["how do pi skills work"], n_results=3)
```

Check that the top result (lowest distance score) is from the expected page.
Scores below ~0.50 are good matches; above ~0.65 are tangential.

## 7. Update the query script

If using `sovereign_rag.py` pattern, update the `query()` function to search the new collection alongside existing ones. The updated query function now searches both `sovereign_codex` and `sovereign_docs` and merges results sorted by distance.

## Pitfalls

- `web_extract` summarizes large pages (>5000 chars). For detailed technical pages, prefer `browser_navigate` + `browser_snapshot(full=true)` for full content.
- ChromaDB collections use the same embedding function for writes and reads — if you change the embedding model, you must re-index.
- Each web_extract call is a separate API call. Budget ~25-30 calls for a full docs site.
- The `chunk_text` function should try to break at paragraph boundaries, not mid-sentence. Overlap ensures no information is lost at chunk boundaries.

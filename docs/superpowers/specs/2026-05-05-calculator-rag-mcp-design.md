# Calculator RAG — MCP Server Design

**Date:** 2026-05-05
**Status:** Approved

## Goal

Give Claude Code direct access to a local RAG database of vintage calculator manuals. Claude Code calls a tool to retrieve relevant chunks from Qdrant, then reasons over them to answer questions — no Anthropic API key required.

---

## Architecture

```
Claude Code
     │  MCP (stdio)
     ▼
calculator-mcp (Python, local subprocess)
     │                    │
  HTTP                 HTTP
     ▼                    ▼
Ollama :11434        Qdrant :6333
(embed query)        (vector search)
     │
nomic-embed-text model
```

Claude Code spawns the MCP server as a local subprocess over stdin/stdout. When the user asks about calculators, Claude Code calls `search_calculators`, which embeds the query via Ollama and fetches the top 5 matching chunks from Qdrant. The chunks (with source filenames and scores) are returned to Claude Code, which uses them to answer.

---

## Components

| File | Purpose |
|------|---------|
| `.env` | `PDF_DIR` updated to `/home/jjureta/Books/Manuals/Calculators` |
| `mcp-server/server.py` | MCP server — embeds queries, searches Qdrant, returns chunks |
| `mcp-server/requirements.txt` | Python deps: `mcp`, `qdrant-client`, `requests` |
| `.claude/settings.json` | Registers the MCP server with Claude Code |

`ingestor/query.py` is left unchanged — it remains a standalone CLI option if an Anthropic API key becomes available later.

---

## MCP Tool

**Name:** `search_calculators`

**Input:**
```json
{ "question": "How do I write a FOR loop on the HP-41C?" }
```

**Output:** list of up to 5 objects:
```json
[
  { "source": "HP-41C_Manual.pdf", "text": "...", "score": 0.91 },
  ...
]
```

---

## Data Flow — Per Query

1. User asks Claude Code a question about a calculator
2. Claude Code calls `search_calculators(question)`
3. MCP server POSTs question text to `http://localhost:11434/api/embeddings` (Ollama, `nomic-embed-text`)
4. MCP server queries Qdrant collection `calculator_manuals` with the embedding vector, `limit=5`
5. Returns chunks with `source`, `text`, `score` fields
6. Claude Code reads the chunks and answers the user, citing sources

---

## Setup Sequence (One-Time)

1. Update `PDF_DIR` in `.env` to `/home/jjureta/Books/Manuals/Calculators`
2. `docker compose up -d` — starts Qdrant, Ollama, pulls `nomic-embed-text`, runs ingestor
3. Wait for ingestor container to complete (PDFs indexed into Qdrant)
4. `pip install -r mcp-server/requirements.txt`
5. Register MCP server in `.claude/settings.json`

The ingestor only needs to run once (or again when new PDFs are added). Qdrant persists to a named Docker volume and survives restarts.

---

## Error Handling

- If Ollama is unreachable: return an error message explaining the Docker stack is not running
- If Qdrant is unreachable: same
- If the collection is empty (not yet ingested): return a clear message
- No retries — fast fail so Claude Code can report the issue to the user

---

## Out of Scope

- Web UI / Open WebUI integration (separate concern)
- Anthropic API / `query.py` changes
- GPU acceleration (can be enabled later in `docker-compose.yml`)
- Re-ingestion automation / file watching

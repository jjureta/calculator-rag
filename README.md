# Calculator Manual RAG Stack

Local RAG pipeline for vintage programmable calculator manuals.
Stack: Qdrant · Ollama (nomic-embed-text) · Claude Code MCP server

## How it works

1. **Ingestor** reads PDFs from your manuals folder, chunks them, embeds via Ollama, and stores vectors in Qdrant.
2. **MCP server** exposes a `search_calculators` tool to Claude Code. When you ask a question, Claude Code calls the tool, retrieves the top matching chunks from Qdrant, and answers using its own intelligence — no Anthropic API key required.

## Prerequisites

- Ollama running as a service with `nomic-embed-text` pulled:
  ```bash
  ollama pull nomic-embed-text
  ```
- Docker (for Qdrant + ingestor)

## Directory layout

```
.
├── docker-compose.yml      ← Qdrant + ingestor only
├── .env                    ← set PDF_DIR here
├── ingestor/
│   ├── ingest.py           ← PDF → chunks → Qdrant
│   └── query.py            ← CLI query tool (requires Anthropic API key)
└── mcp-server/
    ├── server.py           ← FastMCP server for Claude Code
    ├── requirements.txt
    └── tests/
        └── test_server.py
```

## Setup

```bash
# 1. Copy and edit the env file
cp .env.example .env
# Set PDF_DIR to your manuals folder, e.g.:
# PDF_DIR=/home/yourname/Books/Manuals/Calculators

# 2. Install MCP server dependencies
pip install -r mcp-server/requirements.txt

# 3. Start Qdrant and run the ingestor
docker compose up -d
docker compose logs -f ingestor
```

The ingestor scans subdirectories recursively. Only PDFs with selectable text (not scanned images) will be indexed.

## Re-ingesting after adding new PDFs

```bash
docker compose up ingestor
```

## Claude Code integration

The MCP server is registered in `.claude/settings.json`. Restart Claude Code in this project directory to pick it up. Verify with `/mcp` — `calculator-rag` should appear as connected.

Then just ask naturally:
> "How do I write a FOR loop on the HP-41C?"

## Qdrant dashboard

Browse indexed vectors at: http://localhost:6333/dashboard

## Upgrading to RTX 3090

When your Zotac RTX 3090 arrives, update the Ollama systemd service to target the new GPU (NVIDIA Container Toolkit is already installed). No other changes needed.

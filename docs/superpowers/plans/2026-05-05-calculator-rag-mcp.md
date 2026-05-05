# Calculator RAG MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local MCP server that lets Claude Code search vintage calculator manuals stored in Qdrant via semantic search.

**Architecture:** A Python FastMCP server exposes one tool (`search_calculators`) that embeds the query via Ollama (`nomic-embed-text`) and returns the top 5 matching chunks from Qdrant. Claude Code calls this tool and reasons over the results using its own intelligence — no Anthropic API key required.

**Tech Stack:** Python 3.11, `mcp[cli]`, `qdrant-client`, `requests`, `pytest`, Docker Compose (Qdrant + Ollama)

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `.env` | Modify | Correct `PDF_DIR` path |
| `mcp-server/requirements.txt` | Create | Python dependencies |
| `mcp-server/server.py` | Create | MCP server — embed + search + tool handler |
| `mcp-server/tests/test_server.py` | Create | Unit tests with mocked Ollama/Qdrant |
| `.claude/settings.json` | Create | Register MCP server with Claude Code |

---

## Task 1: Update PDF_DIR in .env

**Files:**
- Modify: `.env:11`

- [ ] **Step 1: Update the PDF_DIR value**

Open `.env` and change line 5 from:
```
PDF_DIR=/home/josip/calculators/pdfs
```
to:
```
PDF_DIR=/home/jjureta/Books/Manuals/Calculators
```

- [ ] **Step 2: Verify**

```bash
grep PDF_DIR .env
```
Expected output:
```
PDF_DIR=/home/jjureta/Books/Manuals/Calculators
```

- [ ] **Step 3: Commit**

```bash
git add .env
git commit -m "config: set correct PDF_DIR for calculator manuals"
```

---

## Task 2: Create requirements.txt and install dependencies

**Files:**
- Create: `mcp-server/requirements.txt`

- [ ] **Step 1: Create the file**

Create `mcp-server/requirements.txt` with this exact content:
```
mcp[cli]>=1.0.0
qdrant-client>=1.7.0
requests>=2.31.0
pytest>=7.4.0
```

- [ ] **Step 2: Install**

```bash
pip install -r mcp-server/requirements.txt
```

Expected: packages install without errors. Note the exact versions installed — if `mcp[cli]` fails, try `mcp` (the `[cli]` extra adds the `mcp` CLI tool; the library works either way).

- [ ] **Step 3: Commit**

```bash
git add mcp-server/requirements.txt
git commit -m "chore: add mcp-server requirements"
```

---

## Task 3: Write failing tests for embed()

**Files:**
- Create: `mcp-server/tests/__init__.py` (empty)
- Create: `mcp-server/tests/test_server.py`

- [ ] **Step 1: Create the test directory and empty __init__.py**

```bash
mkdir -p mcp-server/tests
touch mcp-server/tests/__init__.py
```

- [ ] **Step 2: Write the failing tests for embed()**

Create `mcp-server/tests/test_server.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import server


def test_embed_returns_vector():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"embedding": [0.1, 0.2, 0.3]}
    with patch("server.requests.post", return_value=mock_resp):
        result = server.embed("test query")
    assert result == [0.1, 0.2, 0.3]


def test_embed_raises_on_http_error():
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = Exception("HTTP 500")
    with patch("server.requests.post", return_value=mock_resp):
        with pytest.raises(Exception, match="HTTP 500"):
            server.embed("test query")
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
cd mcp-server && python -m pytest tests/test_server.py::test_embed_returns_vector tests/test_server.py::test_embed_raises_on_http_error -v
```

Expected: `ModuleNotFoundError: No module named 'server'` or `ImportError` — the file doesn't exist yet.

---

## Task 4: Implement embed() — make embed tests pass

**Files:**
- Create: `mcp-server/server.py`

- [ ] **Step 1: Create server.py with embed() only**

Create `mcp-server/server.py`:

```python
import os
import requests
from qdrant_client import QdrantClient
from mcp.server.fastmcp import FastMCP

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
COLLECTION = os.getenv("COLLECTION", "calculator_manuals")
EMBED_MODEL = "nomic-embed-text"
TOP_K = 5

mcp = FastMCP("calculator-rag")


def embed(text: str) -> list[float]:
    resp = requests.post(
        f"{OLLAMA_HOST}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def search(question: str) -> list[dict]:
    raise NotImplementedError


@mcp.tool()
def search_calculators(question: str) -> str:
    """Search vintage calculator manuals and return relevant excerpts."""
    raise NotImplementedError


if __name__ == "__main__":
    mcp.run()
```

- [ ] **Step 2: Run embed tests**

```bash
cd mcp-server && python -m pytest tests/test_server.py::test_embed_returns_vector tests/test_server.py::test_embed_raises_on_http_error -v
```

Expected: both PASS.

- [ ] **Step 3: Commit**

```bash
git add mcp-server/server.py mcp-server/tests/__init__.py mcp-server/tests/test_server.py
git commit -m "feat: add embed() with tests"
```

---

## Task 5: Write failing tests for search()

**Files:**
- Modify: `mcp-server/tests/test_server.py`

- [ ] **Step 1: Add search() tests to the test file**

Append to `mcp-server/tests/test_server.py`:

```python
def test_search_returns_chunks():
    mock_point = MagicMock()
    mock_point.payload = {"source": "HP-41C.pdf", "text": "some manual text"}
    mock_point.score = 0.95

    mock_qc = MagicMock()
    mock_qc.search.return_value = [mock_point]

    with patch("server.QdrantClient", return_value=mock_qc), \
         patch("server.embed", return_value=[0.1, 0.2, 0.3]):
        result = server.search("how to program HP-41C")

    assert len(result) == 1
    assert result[0]["source"] == "HP-41C.pdf"
    assert result[0]["text"] == "some manual text"
    assert result[0]["score"] == 0.95


def test_search_returns_empty_list_when_no_results():
    mock_qc = MagicMock()
    mock_qc.search.return_value = []

    with patch("server.QdrantClient", return_value=mock_qc), \
         patch("server.embed", return_value=[0.1, 0.2, 0.3]):
        result = server.search("obscure question")

    assert result == []
```

- [ ] **Step 2: Run new tests to confirm they fail**

```bash
cd mcp-server && python -m pytest tests/test_server.py::test_search_returns_chunks tests/test_server.py::test_search_returns_empty_list_when_no_results -v
```

Expected: both FAIL with `NotImplementedError`.

---

## Task 6: Implement search() — make search tests pass

**Files:**
- Modify: `mcp-server/server.py`

- [ ] **Step 1: Replace the NotImplementedError stub in search()**

In `mcp-server/server.py`, replace:
```python
def search(question: str) -> list[dict]:
    raise NotImplementedError
```
with:
```python
def search(question: str) -> list[dict]:
    qc = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    vector = embed(question)
    results = qc.search(
        collection_name=COLLECTION,
        query_vector=vector,
        limit=TOP_K,
    )
    return [
        {"source": r.payload["source"], "text": r.payload["text"], "score": r.score}
        for r in results
    ]
```

- [ ] **Step 2: Run search tests**

```bash
cd mcp-server && python -m pytest tests/test_server.py::test_search_returns_chunks tests/test_server.py::test_search_returns_empty_list_when_no_results -v
```

Expected: both PASS.

- [ ] **Step 3: Commit**

```bash
git add mcp-server/server.py mcp-server/tests/test_server.py
git commit -m "feat: add search() with tests"
```

---

## Task 7: Write failing tests for search_calculators()

**Files:**
- Modify: `mcp-server/tests/test_server.py`

- [ ] **Step 1: Add tool handler tests**

Append to `mcp-server/tests/test_server.py`:

```python
def test_search_calculators_no_results():
    with patch("server.search", return_value=[]):
        result = server.search_calculators("unknown question")
    assert "No relevant content" in result


def test_search_calculators_formats_chunks():
    chunks = [
        {"source": "HP-41C.pdf", "text": "FOR loop syntax is GTO", "score": 0.91},
        {"source": "HP-41C.pdf", "text": "examples of loops", "score": 0.80},
    ]
    with patch("server.search", return_value=chunks):
        result = server.search_calculators("FOR loop")
    assert "HP-41C.pdf" in result
    assert "FOR loop syntax is GTO" in result
    assert "---" in result
    assert "0.910" in result


def test_search_calculators_handles_exception():
    with patch("server.search", side_effect=Exception("Qdrant unreachable")):
        result = server.search_calculators("any question")
    assert "Error" in result
    assert "Qdrant unreachable" in result
```

- [ ] **Step 2: Run new tests to confirm they fail**

```bash
cd mcp-server && python -m pytest tests/test_server.py::test_search_calculators_no_results tests/test_server.py::test_search_calculators_formats_chunks tests/test_server.py::test_search_calculators_handles_exception -v
```

Expected: all FAIL with `NotImplementedError`.

---

## Task 8: Implement search_calculators() — make all tests pass

**Files:**
- Modify: `mcp-server/server.py`

- [ ] **Step 1: Replace the NotImplementedError stub in search_calculators()**

In `mcp-server/server.py`, replace:
```python
@mcp.tool()
def search_calculators(question: str) -> str:
    """Search vintage calculator manuals and return relevant excerpts."""
    raise NotImplementedError
```
with:
```python
@mcp.tool()
def search_calculators(question: str) -> str:
    """Search vintage calculator manuals and return relevant excerpts."""
    try:
        chunks = search(question)
    except Exception as e:
        return f"Error: {e}"

    if not chunks:
        return "No relevant content found in the calculator manuals."

    return "\n\n---\n\n".join(
        f"Source: {c['source']} (score: {c['score']:.3f})\n{c['text']}"
        for c in chunks
    )
```

- [ ] **Step 2: Run the full test suite**

```bash
cd mcp-server && python -m pytest tests/ -v
```

Expected: all 9 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add mcp-server/server.py mcp-server/tests/test_server.py
git commit -m "feat: implement search_calculators MCP tool with tests"
```

---

## Task 9: Register MCP server with Claude Code

**Files:**
- Create: `.claude/settings.json`

- [ ] **Step 1: Create the .claude directory and settings file**

```bash
mkdir -p .claude
```

Create `.claude/settings.json`:

```json
{
  "mcpServers": {
    "calculator-rag": {
      "command": "python",
      "args": ["/home/jjureta/Projects/calculator-rag/mcp-server/server.py"],
      "env": {
        "QDRANT_HOST": "localhost",
        "QDRANT_PORT": "6333",
        "OLLAMA_HOST": "http://localhost:11434",
        "COLLECTION": "calculator_manuals"
      }
    }
  }
}
```

- [ ] **Step 2: Verify JSON is valid**

```bash
python3 -c "import json; json.load(open('.claude/settings.json')); print('valid')"
```

Expected: `valid`

- [ ] **Step 3: Commit**

```bash
git add .claude/settings.json
git commit -m "config: register calculator-rag MCP server with Claude Code"
```

---

## Task 10: Start Docker stack and ingest PDFs

**Files:** none

- [ ] **Step 1: Verify PDF directory exists and has files**

```bash
ls /home/jjureta/Books/Manuals/Calculators | head -20
```

Expected: a list of PDF files. If empty, stop — ingestor will do nothing.

- [ ] **Step 2: Start the stack**

```bash
docker compose up -d
```

Expected: containers start. Ollama, Qdrant, and the ingestor pull/start.

- [ ] **Step 3: Watch the ingestor complete**

```bash
docker compose logs -f ingestor
```

Wait until you see output ending in something like `Ingested N documents` or the container exits. Press Ctrl+C when done.

- [ ] **Step 4: Verify data is in Qdrant**

```bash
curl -s http://localhost:6333/collections/calculator_manuals | python3 -m json.tool
```

Expected: JSON showing `"status": "green"` and `"vectors_count"` > 0.

---

## Task 11: End-to-end smoke test

- [ ] **Step 1: Restart Claude Code**

Close and reopen Claude Code in this project directory. This causes it to pick up the new MCP server from `.claude/settings.json`.

- [ ] **Step 2: Verify MCP server is registered**

In the Claude Code session, run:
```
/mcp
```

Expected: `calculator-rag` appears in the list with status connected.

- [ ] **Step 3: Ask a calculator question**

In Claude Code, ask:
> "How do I write a program on the HP-41C?"

Expected: Claude Code calls `search_calculators`, retrieves chunks from Qdrant, and answers citing specific PDF sources.

- [ ] **Step 4: Ask a question with no answer**

> "What is the price of the HP-41C?"

Expected: Claude Code reports no relevant content was found (or gives a general answer noting the manuals don't cover pricing).

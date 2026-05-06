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
    qc = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    vector = embed(question)
    results = qc.query_points(
        collection_name=COLLECTION,
        query=vector,
        limit=TOP_K,
    ).points
    return [
        {"source": r.payload["source"], "text": r.payload["text"], "score": r.score}
        for r in results
    ]


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


def _filter_stdin_empty_lines() -> None:
    # Claude Code sends bare '\n' keepalives over stdio; the MCP library
    # can't parse them as JSON and aborts the connection. Filter them out
    # at the raw stream level before FastMCP reads stdin.
    import io
    import sys

    class _FilteredRaw(io.RawIOBase):
        def __init__(self, raw: io.RawIOBase) -> None:
            self._raw = raw
            self._pending = b""

        def readable(self) -> bool:
            return True

        def readinto(self, b: bytearray) -> int:
            while not self._pending:
                line = self._raw.readline()
                if not line:
                    return 0
                if line.strip():
                    self._pending = line
            n = min(len(self._pending), len(b))
            b[:n] = self._pending[:n]
            self._pending = self._pending[n:]
            return n

    filtered = io.BufferedReader(_FilteredRaw(sys.stdin.buffer.raw))
    sys.stdin = io.TextIOWrapper(filtered, encoding="utf-8")


if __name__ == "__main__":
    _filter_stdin_empty_lines()
    mcp.run()

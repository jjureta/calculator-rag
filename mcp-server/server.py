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
    results = qc.search(
        collection_name=COLLECTION,
        query_vector=vector,
        limit=TOP_K,
    )
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


if __name__ == "__main__":
    mcp.run()

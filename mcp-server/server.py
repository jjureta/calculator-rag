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

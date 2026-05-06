"""
query.py — ask questions about your calculator manuals.
Uses Qdrant for retrieval and Claude API as the LLM brain.

Usage:
  ANTHROPIC_API_KEY=sk-... python query.py "How do I write a FOR loop on the HP-41C?"

Or drop into interactive mode:
  ANTHROPIC_API_KEY=sk-... python query.py
"""

import os
import sys
import requests
import anthropic
from qdrant_client import QdrantClient

# ── Config ───────────────────────────────────────────────────────────
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
COLLECTION  = os.getenv("COLLECTION", "calculator_manuals")
EMBED_MODEL = "nomic-embed-text"
TOP_K       = 5

qc              = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
anthropic_client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY


# ── Helpers ──────────────────────────────────────────────────────────

def embed(text: str) -> list[float]:
    resp = requests.post(
        f"{OLLAMA_HOST}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def retrieve(question: str, top_k: int = TOP_K) -> list[dict]:
    vector = embed(question)
    results = qc.search(
        collection_name=COLLECTION,
        query_vector=vector,
        limit=top_k,
    )
    return [{"source": r.payload["source"], "text": r.payload["text"]} for r in results]


def ask(question: str) -> str:
    chunks = retrieve(question)
    if not chunks:
        return "No relevant content found in the manuals."

    context = "\n\n---\n\n".join(
        f"[{c['source']}]\n{c['text']}" for c in chunks
    )

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": (
                    "You are an expert on vintage programmable calculators. "
                    "Answer the question using ONLY the provided manual excerpts. "
                    "Always cite which manual your answer comes from. "
                    "If the answer is not in the excerpts, say so.\n\n"
                    f"MANUAL EXCERPTS:\n{context}\n\n"
                    f"QUESTION: {question}"
                ),
            }
        ],
    )
    return response.content[0].text


# ── Entry point ──────────────────────────────────────────────────────

def main():
    if len(sys.argv) > 1:
        # Single question from CLI arg
        print(ask(" ".join(sys.argv[1:])))
    else:
        # Interactive REPL
        print("Calculator Manual RAG — type 'quit' to exit.\n")
        while True:
            try:
                q = input("Question: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if q.lower() in {"quit", "exit", "q"}:
                break
            if q:
                print(f"\n{ask(q)}\n")


if __name__ == "__main__":
    main()

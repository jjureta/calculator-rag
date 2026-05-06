"""
ingest.py — chunk PDFs, embed via Ollama, store in Qdrant.
Run automatically by the 'ingestor' Docker service.
Re-running is safe: existing collections are recreated.
"""

import hashlib
import json
import os
import uuid
from pathlib import Path

import pdfplumber
import requests
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# ── Config from environment ──────────────────────────────────────────
QDRANT_HOST  = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT  = int(os.getenv("QDRANT_PORT", 6333))
OLLAMA_HOST  = os.getenv("OLLAMA_HOST", "http://localhost:11434")
PDF_DIR      = Path(os.getenv("PDF_DIR", "./pdfs"))
COLLECTION   = os.getenv("COLLECTION", "calculator_manuals")
CHUNK_SIZE   = int(os.getenv("CHUNK_SIZE", 500))
EMBED_MODEL  = "nomic-embed-text"
VECTOR_DIM   = 768  # nomic-embed-text output dimension
MANIFEST_PATH = Path(os.getenv("MANIFEST_PATH", "/app/ingested.json"))

# ── Helpers ──────────────────────────────────────────────────────────

def embed(text: str) -> list[float]:
    resp = requests.post(
        f"{OLLAMA_HOST}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def chunk_text(text: str, size: int = CHUNK_SIZE) -> list[str]:
    """Split text into overlapping chunks (10 % overlap)."""
    overlap = size // 10
    chunks, i = [], 0
    while i < len(text):
        chunks.append(text[i : i + size])
        i += size - overlap
    return chunks


def extract_text(pdf_path: Path) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        pages = [p.extract_text() or "" for p in pdf.pages]
    return "\n".join(pages)


def load_manifest() -> dict[str, str]:
    if not MANIFEST_PATH.exists():
        return {}
    try:
        return json.loads(MANIFEST_PATH.read_text())
    except json.JSONDecodeError:
        print(f"Warning: corrupt manifest at {MANIFEST_PATH}, starting fresh.")
        return {}


def save_manifest(manifest: dict[str, str]) -> None:
    tmp = MANIFEST_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(manifest, indent=2))
    tmp.replace(MANIFEST_PATH)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ── Main ─────────────────────────────────────────────────────────────

def main():
    qc = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    # Recreate collection (wipe + re-index on every run)
    qc.recreate_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
    )
    print(f"Collection '{COLLECTION}' ready.")

    pdfs = sorted(PDF_DIR.rglob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {PDF_DIR}. Mount your manuals and re-run.")
        return

    points: list[PointStruct] = []
    for pdf_path in pdfs:
        print(f"  → {pdf_path.name}", end=" ", flush=True)
        text = extract_text(pdf_path)
        chunks = [c for c in chunk_text(text) if len(c.strip()) >= 50]
        for chunk in chunks:
            vector = embed(chunk)
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={"text": chunk, "source": pdf_path.name},
                )
            )
        print(f"({len(chunks)} chunks)")

    # Upsert in batches of 256
    batch_size = 256
    for i in range(0, len(points), batch_size):
        qc.upsert(collection_name=COLLECTION, points=points[i : i + batch_size])

    print(f"\nDone. {len(points)} chunks indexed from {len(pdfs)} manuals.")


if __name__ == "__main__":
    main()

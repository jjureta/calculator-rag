# Incremental Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-process only new or changed PDFs on each ingestor run, skipping unchanged files and cleaning up Qdrant points for removed files.

**Architecture:** A SHA-256 manifest (`ingested.json`) is written alongside the ingestor scripts at `/app/ingested.json`, which maps to `./ingestor/ingested.json` on the host via the existing volume mount. On each run, `main()` diffs the manifest against disk: skips unchanged files, deletes Qdrant points for changed/removed files, then embeds and upserts only what is new or updated.

**Tech Stack:** Python stdlib (`hashlib`, `json`), qdrant-client `FilterSelector`/`Filter`/`FieldCondition`/`MatchValue`, pytest with `monkeypatch` and `unittest.mock.patch`.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `ingestor/requirements.txt` | Pin ingestor deps for reproducible installs |
| Create | `ingestor/conftest.py` | Add `ingestor/` to sys.path so `import ingest` works in tests |
| Create | `ingestor/tests/__init__.py` | Mark tests directory as package |
| Create | `ingestor/tests/test_ingest.py` | All unit tests |
| Modify | `ingestor/ingest.py` | Add manifest helpers + incremental `main()` |
| Modify | `docker-compose.yml` | Use `requirements.txt` instead of inline pip args |

---

### Task 1: Add requirements.txt and test scaffolding

**Files:**
- Create: `ingestor/requirements.txt`
- Create: `ingestor/conftest.py`
- Create: `ingestor/tests/__init__.py`
- Modify: `docker-compose.yml`

- [ ] **Step 1: Create `ingestor/requirements.txt`**

```
pdfplumber
qdrant-client>=1.7.0
requests>=2.31.0
pytest>=7.4.0
```

- [ ] **Step 2: Create `ingestor/conftest.py`**

This file makes `import ingest` work from any test file without needing a package install.

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
```

- [ ] **Step 3: Create `ingestor/tests/__init__.py`** (empty file)

```python
```

- [ ] **Step 4: Update the `ingestor` command in `docker-compose.yml`**

Replace:
```yaml
    command: >
      sh -c "
        pip install --quiet pdfplumber qdrant-client requests &&
        python ingest.py
      "
```

With:
```yaml
    command: >
      sh -c "
        pip install --quiet -r requirements.txt &&
        python ingest.py
      "
```

- [ ] **Step 5: Verify test runner works**

```bash
cd /path/to/calculator-rag/ingestor
pip install -r requirements.txt
pytest tests/ -v
```

Expected output: `no tests ran` (no test file yet — that's correct at this stage).

- [ ] **Step 6: Commit**

```bash
git add ingestor/requirements.txt ingestor/conftest.py ingestor/tests/__init__.py docker-compose.yml
git commit -m "chore: add ingestor requirements.txt and test scaffolding"
```

---

### Task 2: Add manifest helpers with TDD

**Files:**
- Create: `ingestor/tests/test_ingest.py`
- Modify: `ingestor/ingest.py`

- [ ] **Step 1: Write failing tests for `load_manifest`, `save_manifest`, `file_sha256`**

Create `ingestor/tests/test_ingest.py`:

```python
import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import ingest


def test_load_manifest_returns_empty_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(ingest, "MANIFEST_PATH", tmp_path / "ingested.json")
    assert ingest.load_manifest() == {}


def test_load_manifest_reads_existing_file(tmp_path, monkeypatch):
    manifest_file = tmp_path / "ingested.json"
    manifest_file.write_text(json.dumps({"foo.pdf": "abc123"}))
    monkeypatch.setattr(ingest, "MANIFEST_PATH", manifest_file)
    assert ingest.load_manifest() == {"foo.pdf": "abc123"}


def test_save_manifest_writes_json(tmp_path, monkeypatch):
    manifest_file = tmp_path / "ingested.json"
    monkeypatch.setattr(ingest, "MANIFEST_PATH", manifest_file)
    ingest.save_manifest({"bar.pdf": "def456"})
    assert json.loads(manifest_file.read_text()) == {"bar.pdf": "def456"}


def test_file_sha256_is_deterministic(tmp_path):
    f = tmp_path / "test.bin"
    f.write_bytes(b"hello world")
    assert ingest.file_sha256(f) == ingest.file_sha256(f)
    assert ingest.file_sha256(f) == hashlib.sha256(b"hello world").hexdigest()


def test_file_sha256_differs_for_different_content(tmp_path):
    a, b = tmp_path / "a.bin", tmp_path / "b.bin"
    a.write_bytes(b"content A")
    b.write_bytes(b"content B")
    assert ingest.file_sha256(a) != ingest.file_sha256(b)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd ingestor && pytest tests/test_ingest.py -v
```

Expected: `AttributeError: module 'ingest' has no attribute 'load_manifest'`

- [ ] **Step 3: Add imports and helpers to `ingestor/ingest.py`**

Add to the existing import block at the top:
```python
import hashlib
import json
```

After the config block (after the `CHUNK_SIZE` line), add:
```python
MANIFEST_PATH = Path(os.getenv("MANIFEST_PATH", "/app/ingested.json"))
```

After the `extract_text()` function, add:
```python
def load_manifest() -> dict[str, str]:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text())
    return {}


def save_manifest(manifest: dict[str, str]) -> None:
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd ingestor && pytest tests/test_ingest.py -v
```

Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add ingestor/ingest.py ingestor/tests/test_ingest.py
git commit -m "feat: add manifest load/save and file_sha256 helpers"
```

---

### Task 3: Add `delete_source_points` helper with TDD

**Files:**
- Modify: `ingestor/tests/test_ingest.py` (append one test)
- Modify: `ingestor/ingest.py`

- [ ] **Step 1: Append a failing test to `ingestor/tests/test_ingest.py`**

```python
def test_delete_source_points_calls_qdrant_delete():
    from qdrant_client.models import FilterSelector, Filter, FieldCondition, MatchValue
    qc = MagicMock()
    ingest.delete_source_points(qc, "my_col", "foo.pdf")
    qc.delete.assert_called_once()
    kwargs = qc.delete.call_args.kwargs
    assert kwargs["collection_name"] == "my_col"
    selector = kwargs["points_selector"]
    assert isinstance(selector, FilterSelector)
    assert selector.filter.must[0].key == "source"
    assert selector.filter.must[0].match.value == "foo.pdf"
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd ingestor && pytest tests/test_ingest.py::test_delete_source_points_calls_qdrant_delete -v
```

Expected: `AttributeError: module 'ingest' has no attribute 'delete_source_points'`

- [ ] **Step 3: Update the qdrant_client import in `ingestor/ingest.py`**

Replace:
```python
from qdrant_client.models import Distance, VectorParams, PointStruct
```

With:
```python
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue, FilterSelector,
)
```

Then add `delete_source_points` after `file_sha256`:

```python
def delete_source_points(qc: QdrantClient, collection: str, source: str) -> None:
    qc.delete(
        collection_name=collection,
        points_selector=FilterSelector(
            filter=Filter(
                must=[FieldCondition(key="source", match=MatchValue(value=source))]
            )
        ),
    )
```

- [ ] **Step 4: Run all tests to confirm they pass**

```bash
cd ingestor && pytest tests/test_ingest.py -v
```

Expected: 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add ingestor/ingest.py ingestor/tests/test_ingest.py
git commit -m "feat: add delete_source_points for removing stale Qdrant vectors by filename"
```

---

### Task 4: Refactor `main()` for incremental ingestion with TDD

**Files:**
- Modify: `ingestor/tests/test_ingest.py` (append four tests)
- Modify: `ingestor/ingest.py` (replace `main()`)

- [ ] **Step 1: Append four failing tests to `ingestor/tests/test_ingest.py`**

```python
def _make_pdf(tmp_path: Path, name: str, content: bytes = b"data") -> Path:
    p = tmp_path / name
    p.write_bytes(content)
    return p


def test_main_skips_unchanged_pdf(tmp_path, monkeypatch):
    _make_pdf(tmp_path, "calc.pdf", b"unchanged")
    sha = hashlib.sha256(b"unchanged").hexdigest()
    manifest_file = tmp_path / "ingested.json"
    manifest_file.write_text(json.dumps({"calc.pdf": sha}))
    monkeypatch.setattr(ingest, "PDF_DIR", tmp_path)
    monkeypatch.setattr(ingest, "MANIFEST_PATH", manifest_file)
    monkeypatch.setattr(ingest, "COLLECTION", "test_col")

    qc = MagicMock()
    qc.collection_exists.return_value = True
    with patch("ingest.QdrantClient", return_value=qc), \
         patch("ingest.embed") as mock_embed:
        ingest.main()

    mock_embed.assert_not_called()
    qc.upsert.assert_not_called()


def test_main_ingests_new_pdf(tmp_path, monkeypatch):
    _make_pdf(tmp_path, "new.pdf", b"new content")
    manifest_file = tmp_path / "ingested.json"
    manifest_file.write_text("{}")
    monkeypatch.setattr(ingest, "PDF_DIR", tmp_path)
    monkeypatch.setattr(ingest, "MANIFEST_PATH", manifest_file)
    monkeypatch.setattr(ingest, "COLLECTION", "test_col")

    qc = MagicMock()
    qc.collection_exists.return_value = True
    with patch("ingest.QdrantClient", return_value=qc), \
         patch("ingest.embed", return_value=[0.1] * 768), \
         patch("ingest.extract_text", return_value="word " * 120):
        ingest.main()

    qc.upsert.assert_called()
    saved = json.loads(manifest_file.read_text())
    assert "new.pdf" in saved


def test_main_reprocesses_changed_pdf(tmp_path, monkeypatch):
    _make_pdf(tmp_path, "changed.pdf", b"new bytes")
    manifest_file = tmp_path / "ingested.json"
    manifest_file.write_text(json.dumps({"changed.pdf": "old_stale_hash"}))
    monkeypatch.setattr(ingest, "PDF_DIR", tmp_path)
    monkeypatch.setattr(ingest, "MANIFEST_PATH", manifest_file)
    monkeypatch.setattr(ingest, "COLLECTION", "test_col")

    qc = MagicMock()
    qc.collection_exists.return_value = True
    with patch("ingest.QdrantClient", return_value=qc), \
         patch("ingest.embed", return_value=[0.1] * 768), \
         patch("ingest.extract_text", return_value="word " * 120):
        ingest.main()

    qc.delete.assert_called()
    qc.upsert.assert_called()
    saved = json.loads(manifest_file.read_text())
    assert saved["changed.pdf"] != "old_stale_hash"


def test_main_removes_deleted_pdf_from_index(tmp_path, monkeypatch):
    manifest_file = tmp_path / "ingested.json"
    manifest_file.write_text(json.dumps({"gone.pdf": "some_hash"}))
    monkeypatch.setattr(ingest, "PDF_DIR", tmp_path)
    monkeypatch.setattr(ingest, "MANIFEST_PATH", manifest_file)
    monkeypatch.setattr(ingest, "COLLECTION", "test_col")

    qc = MagicMock()
    qc.collection_exists.return_value = True
    with patch("ingest.QdrantClient", return_value=qc), \
         patch("ingest.embed") as mock_embed:
        ingest.main()

    qc.delete.assert_called()
    mock_embed.assert_not_called()
    saved = json.loads(manifest_file.read_text())
    assert "gone.pdf" not in saved
```

- [ ] **Step 2: Run the new tests to confirm they fail**

```bash
cd ingestor && pytest tests/test_ingest.py -k "test_main" -v
```

Expected: 4 tests FAIL (current `main()` calls `recreate_collection` and processes all files unconditionally).

- [ ] **Step 3: Replace `main()` in `ingestor/ingest.py`**

Replace the entire `main()` function (lines 56–92) with:

```python
def main():
    qc = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    if not qc.collection_exists(COLLECTION):
        qc.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
        )
    print(f"Collection '{COLLECTION}' ready.")

    manifest = load_manifest()
    pdfs = {p.name: p for p in sorted(PDF_DIR.rglob("*.pdf"))}

    for name in list(manifest):
        if name not in pdfs:
            print(f"  - {name} removed — deleting from index.")
            delete_source_points(qc, COLLECTION, name)
            del manifest[name]

    if not pdfs:
        print(f"No PDFs found in {PDF_DIR}. Mount your manuals and re-run.")
        save_manifest(manifest)
        return

    points: list[PointStruct] = []
    for name, pdf_path in pdfs.items():
        current_hash = file_sha256(pdf_path)
        if manifest.get(name) == current_hash:
            print(f"  = {name} unchanged — skipping.")
            continue

        if name in manifest:
            print(f"  ~ {name} changed — re-indexing.", end=" ", flush=True)
            delete_source_points(qc, COLLECTION, name)
        else:
            print(f"  + {name} new — indexing.", end=" ", flush=True)

        text = extract_text(pdf_path)
        chunks = [c for c in chunk_text(text) if len(c.strip()) >= 50]
        for chunk in chunks:
            vector = embed(chunk)
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={"text": chunk, "source": name},
                )
            )
        manifest[name] = current_hash
        print(f"({len(chunks)} chunks)")

    batch_size = 256
    for i in range(0, len(points), batch_size):
        qc.upsert(collection_name=COLLECTION, points=points[i : i + batch_size])

    save_manifest(manifest)
    print(f"\nDone. {len(points)} new chunks indexed.")
```

- [ ] **Step 4: Run all tests to confirm they pass**

```bash
cd ingestor && pytest tests/test_ingest.py -v
```

Expected: 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add ingestor/ingest.py ingestor/tests/test_ingest.py
git commit -m "feat: incremental ingestion — skip unchanged PDFs, delete removed ones"
```

---

## Self-Review

**Spec coverage:**
- Skip unchanged files → `test_main_skips_unchanged_pdf` ✓
- Ingest new files → `test_main_ingests_new_pdf` ✓
- Re-ingest changed files → `test_main_reprocesses_changed_pdf` ✓
- Remove deleted files from Qdrant → `test_main_removes_deleted_pdf_from_index` ✓
- Manifest persists across runs → `save_manifest(manifest)` called in all code paths ✓

**Placeholder scan:** No TBD, no "add validation", no "similar to Task N" — all steps contain complete code.

**Type consistency:**
- `load_manifest() -> dict[str, str]` — used as `manifest.get(name)`, `del manifest[name]`, and `manifest[name] = current_hash` ✓
- `save_manifest(manifest: dict[str, str])` — called with the same `manifest` dict throughout `main()` ✓
- `file_sha256(path: Path) -> str` — compared against `manifest.get(name)` (str or None) ✓
- `delete_source_points(qc, COLLECTION, name)` — `name` is `str` from `pdfs` dict keys ✓
- `FilterSelector`/`Filter`/`FieldCondition`/`MatchValue` imported in Task 3 and used in `delete_source_points` ✓

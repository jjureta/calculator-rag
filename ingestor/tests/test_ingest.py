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
    assert ingest.file_sha256(f) == hashlib.sha256(b"hello world").hexdigest()


def test_file_sha256_differs_for_different_content(tmp_path):
    a, b = tmp_path / "a.bin", tmp_path / "b.bin"
    a.write_bytes(b"content A")
    b.write_bytes(b"content B")
    assert ingest.file_sha256(a) != ingest.file_sha256(b)


def test_load_manifest_returns_empty_on_corrupt_file(tmp_path, monkeypatch):
    manifest_file = tmp_path / "ingested.json"
    manifest_file.write_text("not valid json{{{")
    monkeypatch.setattr(ingest, "MANIFEST_PATH", manifest_file)
    assert ingest.load_manifest() == {}


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

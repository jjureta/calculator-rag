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

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

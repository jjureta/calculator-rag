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

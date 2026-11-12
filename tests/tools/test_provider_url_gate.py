"""Contract tests for request_json URL scheme gate (T-0401)."""

from unittest.mock import Mock

import pytest

from tools.provider_jobs import request_json


def test_rejects_file_scheme():
    with pytest.raises(ValueError, match=r"file"):
        request_json("GET", "file:///etc/passwd")


def test_rejects_ftp_scheme():
    with pytest.raises(ValueError, match=r"ftp"):
        request_json("GET", "ftp://example.com/file")


def test_rejects_data_scheme():
    with pytest.raises(ValueError, match=r"data"):
        request_json("GET", "data:application/json,{}")


def test_rejects_url_without_host():
    with pytest.raises(ValueError):
        request_json("GET", "http:///path")


def test_allows_https_without_real_network(monkeypatch):
    response = Mock()
    response.json = Mock(return_value={"ok": True})
    response.raise_for_status = Mock()
    request = Mock(return_value=response)
    monkeypatch.setattr("tools.provider_jobs.requests.request", request)

    assert request_json("GET", "https://example.com") == {"ok": True}
    request.assert_called_once()
    assert request.call_args.args[1] == "https://example.com"


def test_allows_local_http_without_real_network(monkeypatch):
    response = Mock()
    response.json = Mock(return_value={"status": "ready"})
    response.raise_for_status = Mock()
    request = Mock(return_value=response)
    monkeypatch.setattr("tools.provider_jobs.requests.request", request)

    assert request_json("GET", "http://127.0.0.1:8188") == {"status": "ready"}
    request.assert_called_once()
    assert request.call_args.args[1] == "http://127.0.0.1:8188"

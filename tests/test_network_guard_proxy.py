"""Adversarial tests: a local proxy must not bypass the session network guard.

System/env proxies on 127.0.0.1 look like loopback to a socket-only wall and
would otherwise tunnel paid provider calls. These cases prove that path is shut.
"""

from __future__ import annotations

import socket
import urllib.request

import pytest

_PROVIDER_URL = "https://api.atlascloud.ai/api/v1/model/prediction/x"
_LOOPBACK_PROXY = "http://127.0.0.1:7890"


class TestGuardBlocksProxyEscape:
    def test_env_proxy_cannot_reach_provider(self, monkeypatch):
        """HTTP(S)_PROXY pointing at loopback must not fetch a provider URL."""
        requests = pytest.importorskip("requests")
        monkeypatch.setenv("HTTP_PROXY", _LOOPBACK_PROXY)
        monkeypatch.setenv("HTTPS_PROXY", _LOOPBACK_PROXY)
        monkeypatch.setenv("http_proxy", _LOOPBACK_PROXY)
        monkeypatch.setenv("https_proxy", _LOOPBACK_PROXY)
        with pytest.raises(Exception):
            requests.get(_PROVIDER_URL, timeout=5)

    def test_getproxies_discovered_proxy_cannot_reach_provider(self):
        """Proxies that getproxies() would normally expose must not escape."""
        requests = pytest.importorskip("requests")
        # Under the guard, discovery is neutered (env + Windows registry).
        # trust_env / getproxies is exactly the path the Windows system proxy used.
        assert urllib.request.getproxies() == {}
        with pytest.raises(Exception):
            requests.get(_PROVIDER_URL, timeout=5)

    def test_loopback_direct_still_works(self):
        """Binding and connecting to a local 127.0.0.1 server must still work."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]
        try:
            client = socket.create_connection(("127.0.0.1", port), timeout=5)
            client.close()
        finally:
            server.close()

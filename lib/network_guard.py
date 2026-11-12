"""Socket-layer network guard for the test suite.

Blocks outbound (non-loopback) connections so provider tools cannot spend
money during tests. Also neuters proxy discovery: a local system/env proxy
on 127.0.0.1 would otherwise be treated as loopback and tunnel out freely.
"""

from __future__ import annotations

import os
import socket
import urllib.request
from typing import Callable

_ALLOW_ENV_FLAG = "OPENMONTAGE_ALLOW_NETWORK"

_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0", ""}

_PROXY_ENV_KEYS = (
    "http_proxy",
    "https_proxy",
    "ftp_proxy",
    "all_proxy",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "FTP_PROXY",
    "ALL_PROXY",
    "no_proxy",
    "NO_PROXY",
)

_real_connect = socket.socket.connect
_real_connect_ex = socket.socket.connect_ex
_real_create_connection = socket.create_connection

_real_getproxies = urllib.request.getproxies
_real_getproxies_environment = urllib.request.getproxies_environment
_real_getproxies_registry = getattr(urllib.request, "getproxies_registry", None)


class NetworkCallInTestError(RuntimeError):
    """Raised when a test tries to open a non-loopback connection."""


def network_allowed() -> bool:
    return os.environ.get(_ALLOW_ENV_FLAG, "").strip().lower() in {"1", "true", "yes"}


def is_loopback(address) -> bool:
    """True for loopback TCP/UDP targets and for AF_UNIX socket paths."""
    if isinstance(address, (str, bytes)):
        return True  # AF_UNIX / abstract socket — local by definition
    if not isinstance(address, (tuple, list)) or not address:
        return True  # unrecognised shape; let the real call decide
    host = address[0]
    if isinstance(host, bytes):
        host = host.decode("utf-8", "replace")
    if not isinstance(host, str):
        return False
    host = host.strip("[]").lower()
    if host in _LOOPBACK_HOSTS:
        return True
    return host.startswith("127.")


def blocked_error(address) -> NetworkCallInTestError:
    return NetworkCallInTestError(
        f"Blocked a network connection to {address!r} during a test.\n"
        f"\n"
        f"Tests must not call real endpoints — provider APIs bill per request.\n"
        f"Mock the transport instead (see tests/tools/test_atlas_video.py for the\n"
        f"fake-`requests` pattern), or mark the test @pytest.mark.live_api and run\n"
        f"it deliberately with {_ALLOW_ENV_FLAG}=1."
    )


def _empty_proxies() -> dict:
    return {}


def _patch_requests_getproxies(empty: Callable[[], dict]) -> Callable[[], None] | None:
    """requests.utils may hold a direct reference to getproxies — keep it in sync."""
    try:
        import requests.utils as requests_utils
    except ImportError:
        return None
    real = getattr(requests_utils, "getproxies", None)
    requests_utils.getproxies = empty

    def restore() -> None:
        if real is not None:
            requests_utils.getproxies = real

    return restore


def install_network_guard() -> Callable[[], None]:
    """Install socket blocks + proxy-discovery neutering. Returns a restore callback."""

    def guarded_connect(self, address, *args, **kwargs):
        if not is_loopback(address):
            raise blocked_error(address)
        return _real_connect(self, address, *args, **kwargs)

    def guarded_connect_ex(self, address, *args, **kwargs):
        if not is_loopback(address):
            raise blocked_error(address)
        return _real_connect_ex(self, address, *args, **kwargs)

    def guarded_create_connection(address, *args, **kwargs):
        if not is_loopback(address):
            raise blocked_error(address)
        return _real_create_connection(address, *args, **kwargs)

    socket.socket.connect = guarded_connect
    socket.socket.connect_ex = guarded_connect_ex
    socket.create_connection = guarded_create_connection

    # Neuter proxy discovery. requests imports getproxies by name; that original
    # function resolves getproxies_environment / getproxies_registry via module
    # globals, so patching those closes both env and Windows-registry proxies.
    urllib.request.getproxies_environment = _empty_proxies
    if _real_getproxies_registry is not None:
        urllib.request.getproxies_registry = _empty_proxies
    urllib.request.getproxies = _empty_proxies
    restore_requests = _patch_requests_getproxies(_empty_proxies)

    saved_proxy_env = {
        key: os.environ[key] for key in _PROXY_ENV_KEYS if key in os.environ
    }
    for key in saved_proxy_env:
        del os.environ[key]

    def restore() -> None:
        socket.socket.connect = _real_connect
        socket.socket.connect_ex = _real_connect_ex
        socket.create_connection = _real_create_connection
        urllib.request.getproxies = _real_getproxies
        urllib.request.getproxies_environment = _real_getproxies_environment
        if _real_getproxies_registry is not None:
            urllib.request.getproxies_registry = _real_getproxies_registry
        if restore_requests is not None:
            restore_requests()
        for key in list(os.environ):
            if key in _PROXY_ENV_KEYS or key.lower().endswith("_proxy"):
                # Drop keys tests may have set while the guard was active.
                if key not in saved_proxy_env:
                    del os.environ[key]
        for key, value in saved_proxy_env.items():
            os.environ[key] = value

    return restore

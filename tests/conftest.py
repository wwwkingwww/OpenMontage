"""Session-wide test safety net.

**No test may open a network connection.** Provider tools bill per call, so a
test that reaches a real endpoint costs the developer money — silently, and
every time CI runs. This blocks outbound sockets for the whole test session.

The guard is at the socket layer on purpose. Patching `requests` only covers
tools that use `requests`; the fleet also talks to vendor SDKs (google-cloud,
openai, boto3), `httpx`, and raw `urllib`. Everything bottoms out in
`socket.connect`, so that is where the wall goes.

Loopback is still allowed — local servers, ffmpeg RPC, and Backlot fixtures need it.
Proxy discovery (env + OS/`getproxies`) is neutered so a local system proxy
cannot tunnel outbound through 127.0.0.1 and bypass the wall.

To write a test that genuinely hits a live API:

    @pytest.mark.live_api
    def test_real_call():
        ...

Marked tests are **skipped by default** and only run with the env flag set:

    OPENMONTAGE_ALLOW_NETWORK=1 pytest -m live_api

Limitation: this guards the pytest process. A test that shells out to a
subprocess (node, ffmpeg, npx) is outside its reach — don't call paid APIs
from a subprocess in tests.
"""

from __future__ import annotations

import pytest

from lib.network_guard import (
    NetworkCallInTestError,
    install_network_guard,
    network_allowed,
)

# Re-export for any test that imported these from conftest historically.
_ALLOW_ENV_FLAG = "OPENMONTAGE_ALLOW_NETWORK"
__all__ = ["NetworkCallInTestError", "_ALLOW_ENV_FLAG"]


@pytest.fixture(scope="session", autouse=True)
def _block_network():
    """Refuse non-loopback sockets (and proxy escapes) for the entire session."""
    if network_allowed():
        yield
        return

    restore = install_network_guard()
    try:
        yield
    finally:
        restore()


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "live_api: test performs a real, billable API call. Skipped unless "
        f"{_ALLOW_ENV_FLAG}=1 is set.",
    )


def pytest_collection_modifyitems(config, items):
    """Skip live_api tests unless the operator explicitly opted in."""
    if network_allowed():
        return
    skip = pytest.mark.skip(
        reason=f"live API test — costs money; set {_ALLOW_ENV_FLAG}=1 to run"
    )
    for item in items:
        if "live_api" in item.keywords:
            item.add_marker(skip)

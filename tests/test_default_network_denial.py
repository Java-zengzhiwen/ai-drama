import pytest

from tests.network_guard import guarded_connect


def test_default_network_guard_allows_loopback_and_denies_external_hosts():
    calls = []

    def original(_socket, address):
        calls.append(address)
        return "connected"

    assert guarded_connect(original, object(), ("127.0.0.1", 8000)) == "connected"
    assert guarded_connect(original, object(), ("::1", 8000)) == "connected"
    assert guarded_connect(original, object(), ("localhost", 8000)) == "connected"
    with pytest.raises(RuntimeError, match="UNEXPECTED_REAL_NETWORK"):
        guarded_connect(original, object(), ("apihub.agnes-ai.com", 443))

    assert calls == [("127.0.0.1", 8000), ("::1", 8000), ("localhost", 8000)]

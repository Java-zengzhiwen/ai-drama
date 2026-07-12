import pytest

from tests.network_guard import (
    guarded_connect,
    guarded_connect_ex,
    guarded_resolve,
    guarded_reverse_resolve,
    guarded_sendmsg,
    guarded_sendto,
)


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


@pytest.mark.parametrize(
    ("guard", "args"),
    [
        (guarded_connect_ex, (object(), ("example.com", 443))),
        (guarded_sendto, (object(), b"payload", ("8.8.8.8", 53))),
        (guarded_sendmsg, (object(), [b"payload"], [], 0, ("8.8.8.8", 53))),
        (guarded_resolve, ("example.com",)),
        (guarded_reverse_resolve, ("8.8.8.8",)),
        (guarded_reverse_resolve, (("8.8.8.8", 53),)),
    ],
)
def test_default_network_guard_denies_other_network_entry_points(guard, args):
    with pytest.raises(RuntimeError, match="UNEXPECTED_REAL_NETWORK"):
        guard(lambda *_args, **_kwargs: None, *args)

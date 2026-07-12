import socket

import pytest

from tests.network_guard import guarded_connect, guarded_connect_ex, guarded_resolve, guarded_sendto


@pytest.fixture(autouse=True)
def deny_unexpected_real_network(monkeypatch):
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_sendto = socket.socket.sendto

    def connect(sock, address):
        return guarded_connect(original_connect, sock, address)

    def connect_ex(sock, address):
        return guarded_connect_ex(original_connect_ex, sock, address)

    def sendto(sock, data, *args):
        return guarded_sendto(original_sendto, sock, data, *args)

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket.socket, "connect_ex", connect_ex)
    monkeypatch.setattr(socket.socket, "sendto", sendto)
    for name in ("getaddrinfo", "gethostbyname", "gethostbyname_ex"):
        original = getattr(socket, name)
        monkeypatch.setattr(
            socket,
            name,
            lambda host, *args, _original=original, **kwargs: guarded_resolve(
                _original, host, *args, **kwargs
            ),
        )

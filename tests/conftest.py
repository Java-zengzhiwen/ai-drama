import socket

import pytest

from tests.network_guard import guarded_connect


@pytest.fixture(autouse=True)
def deny_unexpected_real_network(monkeypatch):
    original = socket.socket.connect

    def connect(sock, address):
        return guarded_connect(original, sock, address)

    monkeypatch.setattr(socket.socket, "connect", connect)

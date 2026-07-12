import ipaddress


def guarded_connect(original, sock, address):
    if isinstance(address, str):
        return original(sock, address)
    host = address[0]
    if host == "localhost":
        return original(sock, address)
    try:
        if ipaddress.ip_address(host).is_loopback:
            return original(sock, address)
    except ValueError:
        pass
    raise RuntimeError("UNEXPECTED_REAL_NETWORK: %s" % host)

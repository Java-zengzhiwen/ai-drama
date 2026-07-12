import ipaddress


def is_loopback_host(host):
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def deny_unless_loopback(host):
    if not is_loopback_host(host):
        raise RuntimeError("UNEXPECTED_REAL_NETWORK: %s" % host)


def guarded_connect(original, sock, address):
    if isinstance(address, str):
        return original(sock, address)
    host = address[0]
    deny_unless_loopback(host)
    return original(sock, address)


def guarded_connect_ex(original, sock, address):
    return guarded_connect(original, sock, address)


def guarded_sendto(original, sock, data, *args):
    address = args[-1]
    if isinstance(address, tuple):
        deny_unless_loopback(address[0])
    return original(sock, data, *args)


def guarded_resolve(original, host, *args, **kwargs):
    deny_unless_loopback(host)
    return original(host, *args, **kwargs)

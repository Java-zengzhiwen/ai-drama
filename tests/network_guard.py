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


def guarded_sendmsg(original, sock, buffers, *args):
    address = args[-1] if args and isinstance(args[-1], tuple) else None
    if address is None:
        raise RuntimeError("UNEXPECTED_REAL_NETWORK: connected-datagram")
    deny_unless_loopback(address[0])
    return original(sock, buffers, *args)


def guarded_resolve(original, host, *args, **kwargs):
    deny_unless_loopback(host)
    return original(host, *args, **kwargs)


def guarded_reverse_resolve(original, address, *args, **kwargs):
    host = address[0] if isinstance(address, tuple) else address
    deny_unless_loopback(host)
    return original(address, *args, **kwargs)

import ipaddress
import re


PROJECT_MANAGEMENT_PATH = re.compile(
    r"^/api/projects/[^/]+/(?:model-bindings|model-resolution(?:/|$))"
)


def is_management_path(path):
    return (
        path.startswith("/api/suppliers")
        or path.startswith("/api/models")
        or path.startswith("/api/model-tests")
        or path == "/api/settings/agnes"
        or bool(PROJECT_MANAGEMENT_PATH.match(path))
    )


def is_local_management_request(request, trusted_proxy_cidrs=""):
    peer = _ip(request.client.host if request.client else "")
    if peer is None:
        return False
    if peer.is_loopback:
        return True
    trusted = _networks(trusted_proxy_cidrs)
    if not trusted or not _in_networks(peer, trusted):
        return False
    forwarded = request.headers.get("x-forwarded-for", "")
    chain = [_ip(item.strip()) for item in forwarded.split(",") if item.strip()]
    if not chain or any(item is None for item in chain):
        return False
    if any(not _in_networks(proxy, trusted) for proxy in chain[1:]):
        return False
    return chain[0].is_loopback


def _ip(value):
    try:
        return ipaddress.ip_address(value)
    except ValueError:
        return None


def _networks(value):
    networks = []
    for item in value.split(","):
        item = item.strip()
        if item:
            try:
                networks.append(ipaddress.ip_network(item, strict=False))
            except ValueError:
                continue
    return networks


def _in_networks(address, networks):
    return any(address.version == network.version and address in network for network in networks)

import net from "node:net";


function codedError(code) {
  return Object.assign(new Error(code), { code });
}

export function isPublicAddress(address) {
  if (net.isIP(address) === 4) {
    const octets = address.split(".").map(Number);
    const [a, b] = octets;
    return !(
      a === 0 || a === 10 || a === 127 || a >= 224
      || (a === 100 && b >= 64 && b <= 127)
      || (a === 169 && b === 254)
      || (a === 172 && b >= 16 && b <= 31)
      || (a === 192 && b === 168)
      || (a === 198 && (b === 18 || b === 19))
    );
  }
  if (net.isIP(address) === 6) {
    const value = address.toLowerCase().split("%")[0];
    if (value.startsWith("::ffff:")) return isPublicAddress(value.slice(7));
    return !(
      value === "::" || value === "::1" || value.startsWith("fc")
      || value.startsWith("fd") || /^fe[89ab]/.test(value)
      || value.startsWith("ff")
    );
  }
  return false;
}

export function assertPeerAddress(remoteAddress, allowedAddresses) {
  if (!isPublicAddress(remoteAddress) || !allowedAddresses.has(remoteAddress)) {
    throw codedError("HTTP_PEER_ADDRESS_MISMATCH");
  }
}

export function assertNotRedirect(statusCode) {
  const status = Number(statusCode);
  if (status >= 300 && status < 400) throw codedError("HTTP_REDIRECT_FORBIDDEN");
}

import dns from "node:dns";
import dgram from "node:dgram";
import net from "node:net";


function isLoopback(host) {
  return host === "localhost" || host === "::1" || /^127(?:\.|$)/.test(host || "");
}


function assertLoopback(host) {
  if (!isLoopback(host)) throw new Error(`UNEXPECTED_REAL_NETWORK: ${host}`);
}


const originalConnect = net.Socket.prototype.connect;
net.Socket.prototype.connect = function guardedConnect(...args) {
  const options = typeof args[0] === "object" ? args[0] : {};
  const host = options.host || (typeof args[1] === "string" ? args[1] : "localhost");
  if (!options.path) assertLoopback(host);
  return originalConnect.apply(this, args);
};

for (const name of ["lookup", "resolve", "resolve4", "resolve6"]) {
  const original = dns[name];
  dns[name] = function guardedDns(host, ...args) {
    assertLoopback(host);
    return original.call(this, host, ...args);
  };
}

for (const name of ["lookup", "resolve", "resolve4", "resolve6"]) {
  const original = dns.promises[name];
  dns.promises[name] = function guardedDnsPromise(host, ...args) {
    assertLoopback(host);
    return original.call(this, host, ...args);
  };
}

const originalSend = dgram.Socket.prototype.send;
dgram.Socket.prototype.send = function guardedSend(...args) {
  const address = [...args].reverse().find(value => typeof value === "string");
  assertLoopback(address || "localhost");
  return originalSend.apply(this, args);
};

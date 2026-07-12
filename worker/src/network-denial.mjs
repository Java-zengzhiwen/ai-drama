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

const resolverMethods = [
  "resolve", "resolve4", "resolve6", "resolveAny", "resolveCaa", "resolveCname",
  "resolveMx", "resolveNaptr", "resolveNs", "resolvePtr", "resolveSoa", "resolveSrv",
  "resolveTxt", "reverse",
];
const dnsMethods = ["lookup", "lookupService", ...resolverMethods];
for (const api of [dns, dns.promises]) {
  for (const name of dnsMethods) {
    const original = api[name];
    if (!original) continue;
    api[name] = function guardedDns(host, ...args) {
      assertLoopback(host);
      return original.call(this, host, ...args);
    };
  }
}

for (const Resolver of [dns.Resolver, dns.promises.Resolver]) {
  for (const name of resolverMethods) {
    const original = Resolver.prototype[name];
    if (!original) continue;
    Resolver.prototype[name] = function guardedResolver(host, ...args) {
      assertLoopback(host);
      return original.call(this, host, ...args);
    };
  }
}

const originalSend = dgram.Socket.prototype.send;
const originalDatagramConnect = dgram.Socket.prototype.connect;
const loopbackDatagrams = new WeakSet();
dgram.Socket.prototype.connect = function guardedDatagramConnect(port, address, ...args) {
  const host = typeof address === "string" ? address : "localhost";
  assertLoopback(host);
  loopbackDatagrams.add(this);
  return originalDatagramConnect.call(this, port, address, ...args);
};
dgram.Socket.prototype.send = function guardedSend(...args) {
  const address = [...args].reverse().find(value => typeof value === "string");
  if (address) assertLoopback(address);
  else if (!loopbackDatagrams.has(this)) assertLoopback("connected-datagram");
  return originalSend.apply(this, args);
};

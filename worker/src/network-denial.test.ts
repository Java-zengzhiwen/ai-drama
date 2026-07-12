import assert from "node:assert/strict";
import dns from "node:dns";
import dgram from "node:dgram";
import net from "node:net";
import test from "node:test";


test("default test guard denies external DNS, TCP, and UDP", () => {
  assert.throws(() => dns.lookup("example.com", () => {}), /UNEXPECTED_REAL_NETWORK/);
  assert.throws(() => dns.promises.lookup("example.com"), /UNEXPECTED_REAL_NETWORK/);
  assert.throws(() => new net.Socket().connect({ host: "example.com", port: 443 }), /UNEXPECTED_REAL_NETWORK/);
  const socket = dgram.createSocket("udp4");
  assert.throws(() => socket.send(Buffer.from("x"), 53, "8.8.8.8"), /UNEXPECTED_REAL_NETWORK/);
  socket.close();
});

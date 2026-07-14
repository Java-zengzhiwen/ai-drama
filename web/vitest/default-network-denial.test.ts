import net from "node:net";
import { describe, expect, test } from "vitest";

describe("default Node transport denial", () => {
  test("throws before a non-loopback socket can connect", () => {
    const socket = new net.Socket();
    expect(() => socket.connect(443, "external.invalid")).toThrow(/UNEXPECTED_REAL_NETWORK/);
    socket.destroy();
  });
});

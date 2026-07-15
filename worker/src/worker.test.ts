import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createPinnedLookup } from "./pinned-lookup.mjs";


function invoke(compiledCode, mode = "execution", payload = {}) {
  const result = spawnSync(process.execPath, [
    "--import", fileURLToPath(new URL("./network-denial.mjs", import.meta.url)),
    fileURLToPath(new URL("./worker.ts", import.meta.url)),
  ], {
    input: JSON.stringify({
      workerProtocolVersion: "1",
      helperApiVersion: "ai-drama-helper-v1",
      workerRuntimeVersion: process.version,
      compiledCode,
      operation: "textRequest",
      payload,
      mode,
      timeoutMs: 1000,
      maxOutputBytes: 1024 * 1024,
    }),
    encoding: "utf8",
    env: { PATH: process.env.PATH, LANG: "C.UTF-8", TZ: "UTC" },
  });
  return JSON.parse(result.stdout);
}


test("pinned lookup returns all resolved addresses when Node requests all", async () => {
  const records = [
    { address: "203.0.113.10", family: 4 },
    { address: "2001:db8::10", family: 6 },
  ];
  const lookup = createPinnedLookup(records);

  const result = await new Promise((resolve, reject) => {
    lookup("api.example.test", { all: true }, (error, addresses) => {
      if (error) reject(error);
      else resolve(addresses);
    });
  });

  assert.deepEqual(result, records);
});


test("pinned lookup returns one address for the legacy callback contract", async () => {
  const lookup = createPinnedLookup([{ address: "203.0.113.10", family: 4 }]);

  const result = await new Promise((resolve, reject) => {
    lookup("api.example.test", {}, (error, address, family) => {
      if (error) reject(error);
      else resolve({ address, family });
    });
  });

  assert.deepEqual(result, { address: "203.0.113.10", family: 4 });
});


test("supplier context cannot read process", () => {
  const response = invoke("module.exports.textRequest = () => typeof process;");
  assert.equal(response.ok, true);
  assert.equal(response.value, "undefined");
});


test("validation helper denies network", () => {
  const response = invoke(
    "module.exports.textRequest = async (_payload, helpers) => helpers.http.request({});",
    "validation",
  );
  assert.equal(response.ok, false);
  assert.equal(response.error.code, "NETWORK_DISABLED_DURING_VALIDATION");
});

test("execution helper rejects destinations outside selected config", () => {
  const response = invoke(
    "module.exports.textRequest = async (_payload, helpers) => helpers.http.request({url:'https://blocked.invalid/v1'});",
    "execution",
    {config: {base_url: "https://allowed.invalid/v1"}},
  );
  assert.equal(response.ok, false);
  assert.equal(response.error.code, "HTTP_DESTINATION_NOT_ALLOWED");
});

for (const url of [
  "https://127.0.0.1/resource",
  "https://169.254.169.254/latest/meta-data",
  "https://[::1]/resource",
  "https://[fd00::1]/resource",
]) {
  test(`execution helper rejects non-public destination ${url}`, () => {
    const response = invoke(
      `module.exports.textRequest = async (_payload, helpers) => helpers.http.request({url:${JSON.stringify(url)}});`,
      "execution",
      {config: {base_url: url}},
    );
    assert.equal(response.ok, false);
    assert.equal(response.error.code, "HTTP_DESTINATION_NOT_ALLOWED");
  });
}

test("worker test transport denies external DNS even for configured origin", () => {
  const response = invoke(
    "module.exports.textRequest = async (_payload, helpers) => helpers.http.request({url:'https://example.invalid/v1'});",
    "execution",
    {config: {base_url: "https://example.invalid/v1"}},
  );
  assert.equal(response.ok, false);
  assert.match(response.error.code, /SUPPLIER_EXECUTION_FAILED|UNEXPECTED_REAL_NETWORK/);
});

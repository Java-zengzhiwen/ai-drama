import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { readFileSync, rmSync } from "node:fs";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createPinnedLookup } from "./pinned-lookup.mjs";
import { buildMultipartBody, decodeBase64 } from "./media-helpers.mjs";


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


test("bounded base64 decoder rejects malformed and oversized media", () => {
  assert.deepEqual(decodeBase64("ZmFrZS1wbmc=", 32), Buffer.from("fake-png"));
  assert.throws(() => decodeBase64("%%%", 32), error => error.code === "PROVIDER_RESPONSE_MALFORMED");
  assert.throws(() => decodeBase64("ZmFrZS1wbmc=", 4), error => error.code === "SUPPLIER_WORKER_OUTPUT_TOO_LARGE");
});


test("multipart builder accepts only fixed safe scalar fields", () => {
  const body = buildMultipartBody({
    fields: { model: "gpt-image-2", prompt: "make it blue" },
    files: [{ fieldName: "image[]", filename: "image-1.png", mediaType: "image/png", data: Buffer.from("png") }],
  }, "ai-drama-test-boundary", 1024);
  const text = body.toString("utf8");
  assert.match(text, /name="model"/);
  assert.match(text, /name="image\[\]"; filename="image-1.png"/);
  assert.throws(
    () => buildMultipartBody({ fields: { authorization: "secret" }, files: [] }, "boundary", 1024),
    error => error.code === "SUPPLIER_MULTIPART_INVALID",
  );
});


test("supplier can decode base64 only through bounded media helper", () => {
  const response = invoke(`
    module.exports.textRequest = async (_payload, helpers) =>
      helpers.media.decodeBase64("ZmFrZS1wbmc=", "image/png");
  `);
  assert.equal(response.ok, true);
  assert.equal(response.value.media_type, "image/png");
  assert.equal(response.value.size, 8);
  assert.equal(readFileSync(response.value.local_file, "utf8"), "fake-png");
  rmSync(new URL(`file://${response.value.local_file}`).pathname);
  rmSync(new URL(`file://${response.value.local_file}`).pathname.replace(/\/[^/]+$/, ""), { recursive: true, force: true });
});


test("supplier VM still cannot access host media globals", () => {
  const response = invoke(`
    module.exports.textRequest = () => ({
      buffer: typeof Buffer,
      fs: typeof fs,
      process: typeof process,
      require: typeof require
    });
  `);
  assert.deepEqual(response.value, {
    buffer: "undefined",
    fs: "undefined",
    process: "undefined",
    require: "undefined",
  });
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

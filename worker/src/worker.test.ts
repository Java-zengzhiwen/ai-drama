import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { readFileSync, rmSync } from "node:fs";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createPinnedLookup } from "./pinned-lookup.mjs";
import { assertNotRedirect, assertPeerAddress } from "./network-policy.mjs";
import {
  assertInputBudget,
  authorizeDeclaredInputReference,
  authorizeProviderResultDownload,
  buildMultipartBody,
  collectProviderResultUrls,
  decodeBase64,
  decodeDeclaredImageReference,
  providerHttpErrorCode,
} from "./media-helpers.mjs";


function invoke(compiledCode, mode = "execution", payload = {}, helperApiVersion = "ai-drama-helper-v2") {
  const result = spawnSync(process.execPath, [
    "--import", fileURLToPath(new URL("./network-denial.mjs", import.meta.url)),
    fileURLToPath(new URL("./worker.ts", import.meta.url)),
  ], {
    input: JSON.stringify({
      workerProtocolVersion: "1",
      helperApiVersion,
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


test("network policy rejects redirects and peer-IP mismatches", () => {
  assert.throws(() => assertNotRedirect(302), error => error.code === "HTTP_REDIRECT_FORBIDDEN");
  assert.doesNotThrow(() => assertNotRedirect(200));
  assert.doesNotThrow(() => assertPeerAddress("8.8.8.8", new Set(["8.8.8.8"])));
  assert.throws(
    () => assertPeerAddress("8.8.4.4", new Set(["8.8.8.8"])),
    error => error.code === "HTTP_PEER_ADDRESS_MISMATCH",
  );
  assert.throws(
    () => assertPeerAddress("127.0.0.1", new Set(["127.0.0.1"])),
    error => error.code === "HTTP_PEER_ADDRESS_MISMATCH",
  );
});


test("bounded base64 decoder rejects malformed and oversized media", () => {
  const png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9WlS8AAAAASUVORK5CYII=";
  assert.equal(decodeBase64(png, "image/png", 128).subarray(0, 8).toString("hex"), "89504e470d0a1a0a");
  assert.throws(() => decodeBase64("%%%", "image/png", 32), error => error.code === "PROVIDER_RESPONSE_MALFORMED");
  assert.throws(() => decodeBase64("ZmFrZS1wbmc=", "image/png", 32), error => error.code === "PROVIDER_RESPONSE_MALFORMED");
  assert.throws(() => decodeBase64(png, "image/png", 4), error => error.code === "SUPPLIER_WORKER_OUTPUT_TOO_LARGE");
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


test("declared data image is decoded without exposing Buffer to supplier code", () => {
  const decoded = decodeDeclaredImageReference(
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9WlS8AAAAASUVORK5CYII=",
    128,
  );
  assert.equal(decoded.mediaType, "image/png");
  assert.equal(decoded.buffer.subarray(0, 8).toString("hex"), "89504e470d0a1a0a");
  assert.throws(
    () => decodeDeclaredImageReference("data:text/plain;base64,ZmFrZQ==", 32),
    error => error.code === "SUPPLIER_INPUT_MEDIA_INVALID",
  );
});


test("provider result URL collection returns only named media result fields", () => {
  assert.deepEqual(
    collectProviderResultUrls({
      data: [{ url: "https://cdn.example.test/result.png?sig=x" }],
      homepage: "https://untrusted.example.test/",
      ignored: "http://bad.test",
    }),
    ["https://cdn.example.test/result.png?sig=x"],
  );
});


test("provider result download is one-shot GET bytes without request metadata", () => {
  const raw = "https://cdn.example.test/result.png?sig=x";
  const allowed = new Set([raw]);
  assert.equal(
    authorizeProviderResultDownload({ method: "GET", url: raw, responseType: "bytes" }, allowed),
    true,
  );
  assert.equal(allowed.size, 0);
  assert.throws(
    () => authorizeProviderResultDownload({ method: "GET", url: raw, responseType: "bytes" }, allowed),
    error => error.code === "HTTP_DESTINATION_NOT_ALLOWED",
  );
  assert.throws(
    () => authorizeProviderResultDownload({ method: "POST", url: raw, responseType: "bytes", headers: { Authorization: "x" } }, new Set([raw])),
    error => error.code === "HTTP_DESTINATION_NOT_ALLOWED",
  );
});


test("declared input authorization requires an exact original reference", () => {
  const raw = "https://assets.example.test/input.png?sig=x";
  const declared = new Set([raw]);
  assert.equal(authorizeDeclaredInputReference(raw, declared), raw);
  assert.throws(
    () => authorizeDeclaredInputReference("https://assets.example.test/input.png?sig=y", declared),
    error => error.code === "HTTP_DESTINATION_NOT_ALLOWED",
  );
});


test("multipart input budget rejects aggregate bytes before body concatenation", () => {
  assert.equal(assertInputBudget(10, 5, 16), 15);
  assert.throws(
    () => assertInputBudget(10, 7, 16),
    error => error.code === "SUPPLIER_WORKER_OUTPUT_TOO_LARGE",
  );
});


test("provider HTTP status maps to stable sanitized categories", () => {
  assert.equal(providerHttpErrorCode(400), "PROVIDER_REQUEST_REJECTED");
  assert.equal(providerHttpErrorCode(401), "PROVIDER_AUTHENTICATION_ERROR");
  assert.equal(providerHttpErrorCode(404), "PROVIDER_ROUTE_OR_MODEL_NOT_FOUND");
  assert.equal(providerHttpErrorCode(429), "PROVIDER_RATE_LIMITED");
  assert.equal(providerHttpErrorCode(502), "PROVIDER_UPSTREAM_ERROR");
});


test("supplier can decode base64 only through bounded media helper", () => {
  const response = invoke(`
    module.exports.textRequest = async (_payload, helpers) =>
      helpers.media.decodeBase64("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9WlS8AAAAASUVORK5CYII=", "image/png");
  `);
  assert.equal(response.ok, true);
  assert.equal(response.value.media_type, "image/png");
  assert.equal(response.value.size, 68);
  assert.equal(readFileSync(response.value.local_file).subarray(0, 8).toString("hex"), "89504e470d0a1a0a");
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


test("legacy helper v1 cannot use v2 media or multipart contracts", () => {
  const media = invoke(
    "module.exports.textRequest = async (_payload, helpers) => helpers.media.decodeBase64('x','image/png');",
    "execution",
    {},
    "ai-drama-helper-v1",
  );
  const multipart = invoke(
    "module.exports.textRequest = async (payload, helpers) => helpers.http.request({method:'POST',url:payload.config.base_url,multipart:{fields:{model:'x'},files:[{url:payload.request.input_images[0]}]}});",
    "execution",
    {config:{base_url:"https://example.invalid/v1"},request:{input_images:["data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9WlS8AAAAASUVORK5CYII="]}},
    "ai-drama-helper-v1",
  );
  assert.equal(media.ok, false);
  assert.equal(multipart.error.code, "SUPPLIER_RUNTIME_UNAVAILABLE");
});


test("v2 multipart resolves a declared data image before denied test transport", () => {
  const code = `module.exports.textRequest = async (payload, helpers) => helpers.http.request({
    method:'POST', url:payload.config.base_url, headers:{},
    multipart:{fields:{model:'gpt-image-2',prompt:'edit'},files:[{fieldName:'image[]',url:payload.request.input_images[0]}]}
  });`;
  const image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9WlS8AAAAASUVORK5CYII=";
  const accepted = invoke(code, "execution", {config:{base_url:"https://example.invalid/v1"},request:{input_images:[image]}});
  const rejected = invoke(code, "execution", {config:{base_url:"https://example.invalid/v1"},request:{input_images:[]}});
  assert.match(accepted.error.code, /SUPPLIER_EXECUTION_FAILED|UNEXPECTED_REAL_NETWORK/);
  assert.equal(rejected.error.code, "HTTP_DESTINATION_NOT_ALLOWED");
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

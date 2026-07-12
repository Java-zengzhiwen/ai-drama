import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import test from "node:test";
import { fileURLToPath } from "node:url";


function invoke(compiledCode, mode = "execution") {
  const result = spawnSync(process.execPath, [fileURLToPath(new URL("./worker.ts", import.meta.url))], {
    input: JSON.stringify({
      workerProtocolVersion: "1",
      helperApiVersion: "ai-drama-helper-v1",
      workerRuntimeVersion: process.version,
      compiledCode,
      operation: "textRequest",
      payload: {},
      mode,
      timeoutMs: 1000,
      maxOutputBytes: 1024 * 1024,
    }),
    encoding: "utf8",
    env: { PATH: process.env.PATH, LANG: "C.UTF-8", TZ: "UTC" },
  });
  return JSON.parse(result.stdout);
}


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

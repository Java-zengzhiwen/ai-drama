import vm from "node:vm";


function respond(payload) {
  const output = JSON.stringify(payload);
  const limit = Number(request?.maxOutputBytes || 4 * 1024 * 1024);
  if (Buffer.byteLength(output, "utf8") > limit) {
    process.stdout.write(JSON.stringify({
      ok: false,
      error: {
        code: "SUPPLIER_WORKER_OUTPUT_TOO_LARGE",
        message: "supplier worker output too large",
      },
    }));
    return;
  }
  process.stdout.write(output);
}


let request;
try {
  const input = await new Promise((resolve, reject) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", chunk => data += chunk);
    process.stdin.on("end", () => resolve(data));
    process.stdin.on("error", reject);
  });
  request = JSON.parse(input);
} catch {
  process.stdout.write(JSON.stringify({
    ok: false,
    error: { code: "SUPPLIER_WORKER_PROTOCOL_ERROR", message: "invalid worker request" },
  }));
  process.exit(0);
}

if (request.workerProtocolVersion !== "1") {
  respond({
    ok: false,
    error: { code: "SUPPLIER_WORKER_PROTOCOL_ERROR", message: "unsupported worker protocol" },
  });
  process.exit(0);
}
if (
  request.helperApiVersion !== "ai-drama-helper-v1"
  || request.workerRuntimeVersion !== process.version
) {
  respond({
    ok: false,
    error: {
      code: "SUPPLIER_RUNTIME_UNAVAILABLE",
      message: "supplier runtime fingerprint is unavailable",
    },
  });
  process.exit(0);
}

const networkError = request.mode === "validation"
  ? "NETWORK_DISABLED_DURING_VALIDATION"
  : "NETWORK_HELPER_UNAVAILABLE";
const context = vm.createContext(
  {
    payloadJson: JSON.stringify(request.payload),
    operationName: String(request.operation),
    networkErrorCode: networkError,
  },
  { codeGeneration: { strings: false, wasm: false } },
);

try {
  new vm.Script(`
    globalThis.module = { exports: {} };
    globalThis.exports = globalThis.module.exports;
    globalThis.payload = JSON.parse(payloadJson);
    globalThis.operation = operationName;
    const denyNetwork = async () => {
      const error = new Error(networkErrorCode);
      error.code = networkErrorCode;
      throw error;
    };
    globalThis.helpers = Object.freeze({
      http: Object.freeze({ request: denyNetwork }),
      log: Object.freeze({ info: () => undefined, warning: () => undefined }),
    });
  `, { filename: "supplier-bootstrap.cjs" }).runInContext(
    context,
    { timeout: request.timeoutMs },
  );
  new vm.Script(request.compiledCode, { filename: "supplier.cjs" }).runInContext(
    context,
    { timeout: request.timeoutMs },
  );
  new vm.Script(
    "globalThis.__supplierResult = Promise.resolve(module.exports[operation](payload, helpers));",
    { filename: "supplier-invoke.cjs" },
  ).runInContext(context, { timeout: request.timeoutMs });
  const value = await context.__supplierResult;
  respond({
    ok: true,
    workerProtocolVersion: "1",
    helperApiVersion: request.helperApiVersion,
    workerRuntimeVersion: process.version,
    value,
  });
} catch (error) {
  respond({
    ok: false,
    error: {
      code: error?.code || "SUPPLIER_EXECUTION_FAILED",
      message: error?.code || "supplier operation failed",
    },
  });
}
